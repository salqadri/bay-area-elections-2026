"""Refresh both federal money layers (receipts + independent expenditures) and publish.

Deterministic maintenance pass for the two FEC-derived layers:

 1. Independent expenditures — refetch official Schedule E candidate aggregates for every FEC-linked
    printed or provisional federal candidate (``fec_independent_expenditures.py run --force``), re-aggregate and
    attach with a fresh ``checked_on`` date.
 2. Campaign receipts — read each candidate's aggregate cycle totals.
    Update ``receipts``/``through`` only when the reported
    coverage start still equals the stored ``from`` (so multi-cycle exceptions like
    Scott Wiener's 2023-start summary are never silently relabelled) and the new
    coverage end is later than the stored one. Missing totals stay null; a total is
    never inferred from anything else.

Then: bump ``finance.checked_on``/``ie_finance.checked_on`` (the full federal scope
was refreshed, which is exactly what those dates certify), advance
``election.publication_version``, rebuild both pages, run the complete offline
release gate, and only on a fully green gate commit + push to main. A failing gate
aborts with no dataset publication and exit code 1.

The FEC key comes from FEC_API_KEY or --fec-key-file. Git uses configured
credentials, or GITHUB_TOKEN/GH_TOKEN/--github-token-file through an HTTP header
in the child environment, never a credential-bearing URL or command argument.
Neither credential is written into the repository or error output. Intended for a
scheduled run through Election Day (November 3, 2026); after that it exits as a
no-op unless --force-window is passed.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from fec_independent_expenditures import checked_date, now_utc

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "2026-11-03_Bay_Area_Elections.json"
COLLECTOR = ROOT / "scripts/fec_independent_expenditures.py"
REMOTE = "https://github.com/salqadri/bay-area-elections-2026.git"


def redact(text, secrets=()):
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[redacted]')
    return re.sub(r'(https?://)[^/\s@]+@', r'\1[redacted]@', text)


def sh(*cmd, check=True, env=None, secrets=()):
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    if check and result.returncode != 0:
        # Redact before truncation so a token crossing the output boundary cannot
        # leak a suffix that no longer matches the complete secret.
        command = redact(' '.join(map(str, cmd)), secrets)
        stdout = redact(result.stdout, secrets)[-2000:]
        stderr = redact(result.stderr, secrets)[-2000:]
        raise SystemExit(f'command failed: {command}\n{stdout}\n{stderr}')
    return result


def read_secret(names, filename, required=False):
    for name in names:
        if os.environ.get(name, '').strip():
            return os.environ[name].strip()
    try:
        value = Path(filename).read_text(encoding='utf-8').strip() if filename else ''
    except OSError:
        value = ''
    if not value and required:
        raise SystemExit('Provide ' + names[0] + ' or a readable credential file.')
    return value


def push_main(token=''):
    env = None
    secrets = ()
    if token:
        encoded = base64.b64encode(('x-access-token:' + token).encode()).decode()
        env = os.environ.copy()
        index = int(env.get('GIT_CONFIG_COUNT', '0'))
        env['GIT_CONFIG_COUNT'] = str(index + 1)
        env[f'GIT_CONFIG_KEY_{index}'] = 'http.https://github.com/.extraheader'
        env[f'GIT_CONFIG_VALUE_{index}'] = 'AUTHORIZATION: basic ' + encoded
        secrets = (token, encoded)
    sh('git', 'push', REMOTE, 'HEAD:main', env=env, secrets=secrets)


def fec_get_json(url):
    """GET with FEC rate-limit backoff; 429 and transient 5xx retry, key never surfaces."""
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(min(20 * (attempt + 1), 90))
                continue
            raise RuntimeError(f"FEC API request failed: HTTP {error.code}") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt < 5:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError("FEC API request failed: network error") from None


def fec_totals(key, candidate_id):
    """Candidate-level cycle totals — aggregates across all authorized committees,
    the same source shape as the original ingestion (committee-level totals would
    undercount multi-committee candidates like John McBride)."""
    url = ("https://api.open.fec.gov/v1/candidate/" + candidate_id + "/totals/?"
           + urllib.parse.urlencode({"cycle": 2026, "api_key": key}))
    results = fec_get_json(url).get("results") or []
    return results[0] if results else None


def fec_committees(key, candidate_id):
    url = ('https://api.open.fec.gov/v1/candidate/' + candidate_id + '/committees/?'
           + urllib.parse.urlencode({'cycle': 2026, 'api_key': key, 'per_page': 100}))
    results = fec_get_json(url).get('results') or []
    return sorted({r['committee_id'] for r in results
                   if r.get('designation') in {'P', 'A'} and r.get('committee_id')})


def update_receipts(fec, totals, checked_on, committee_ids=None):
    """Validate one full summary before mutating; unknown is distinct from zero."""
    receipts = (totals or {}).get('receipts')
    if receipts is None:
        return 'skipped', 'no published total'
    start = str(totals.get('coverage_start_date') or '')[:10]
    end = str(totals.get('coverage_end_date') or '')[:10]
    try:
        valid_period = date.fromisoformat(start) <= date.fromisoformat(end) <= date.fromisoformat(checked_on)
    except ValueError:
        valid_period = False
    if not valid_period:
        return 'skipped', 'missing or invalid coverage period'
    if fec.get('from') and start != fec['from']:
        return 'skipped', 'coverage start differs from the stored period; exception preserved'
    if fec.get('through') and end < fec['through']:
        return 'skipped', 'older coverage end; existing snapshot preserved'
    if not fec.get('from') and int(start[:4]) < 2025:
        return 'skipped', 'new multi-cycle coverage requires a reviewed explanatory note'
    amount = Decimal(str(receipts)).quantize(Decimal('0.01'))
    if not amount.is_finite() or amount < 0:
        raise ValueError('Invalid FEC receipt amount')
    if fec.get('receipts') is not None and Decimal(str(fec['receipts'])) > amount:
        # A decrease over the IDENTICAL coverage window is an FEC amendment of a
        # previously published total (e.g. Shah H4AZ01194 -$7,000 on 2026-10-22).
        # Any other lower reading stays blocked: it historically meant fetching
        # committee-level instead of candidate-level totals.
        if not (fec.get('from') == start and fec.get('through') == end):
            raise ValueError('New receipts below the stored total; investigate before publishing')
    committees = committee_ids or totals.get('committee_ids') or fec.get('committee_ids')
    if not committees or any(not re.fullmatch(r'C[0-9]{8}', cid) for cid in committees):
        return 'skipped', 'authorized committee IDs unavailable; existing snapshot preserved'
    if fec.get('receipts') == float(amount) and fec.get('through') == end:
        return 'unchanged', ''
    was_unknown = fec.get('receipts') is None
    fec.update(receipts=float(amount), **{'from': start, 'through': end, 'committee_ids': sorted(set(committees))})
    if was_unknown:
        # The old shared note says no summary total was available. Do not retain
        # that claim after the candidate has a fully dated published summary.
        fec.pop('note_id', None)
    return 'updated', f'${amount:,} through {end}'


def next_version(current):
    today = checked_date(now_utc())
    if current and current.startswith(today + "."):
        return f"{today}.{int(current.rsplit('.', 1)[1]) + 1}"
    return today + ".1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-window", action="store_true",
                        help="run even after the November 4, 2026 window closes")
    parser.add_argument("--skip-push", action="store_true",
                        help="refresh and validate locally without publishing")
    parser.add_argument('--fec-key-file', default='/root/.cfg/fec_key')
    parser.add_argument('--github-token-file', default='/root/.cfg/gh_token')
    args = parser.parse_args()

    if date.fromisoformat(checked_date(now_utc())) > date(2026, 11, 4) and not args.force_window:
        print("Refresh window closed after the November 3 election; no-op. "
              "Remove or pause this scheduled job.")
        return

    if not args.skip_push:
        if sh('git', 'branch', '--show-current').stdout.strip() != 'main':
            raise SystemExit('Automated publication requires the main branch; use --skip-push for local review.')
        if sh('git', 'status', '--porcelain').stdout.strip():
            raise SystemExit('Automated publication requires a clean checkout; review existing changes first.')
    key = read_secret(('FEC_API_KEY',), args.fec_key_file, required=True)
    today = checked_date(now_utc())
    report = {"date": today}

    # 1) Independent expenditures: refetch everything, re-aggregate, attach.
    fec_env = {**os.environ, 'FEC_API_KEY': key}
    sh(sys.executable, str(COLLECTOR), "run", "--force", env=fec_env, secrets=(key,))
    before = json.loads(DATASET.read_text(encoding="utf-8"))
    sh(sys.executable, str(COLLECTOR), "attach", "--checked-on", today)

    # 2) Candidate aggregate receipts with the coverage-start guard.
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    updated, skipped = [], []
    for position in data["positions"]:
        if position.get("government_level") != "Federal":
            continue
        # Provisional filings (nationwide Senate compilations) carry FEC records too.
        for candidate in (position.get("candidates") or []) + (position.get("filed_candidates_not_confirmed_on_ballot") or []):
            fec = candidate.get("fec") or {}
            if not isinstance(fec, dict) or not fec.get("id"):
                continue
            totals = fec_totals(key, fec["id"])
            label = candidate["name"]
            committees = None
            if (totals or {}).get('receipts') is not None and not (fec.get('committee_ids') or totals.get('committee_ids')):
                committees = fec_committees(key, fec['id'])
            status, reason = update_receipts(fec, totals, today, committees)
            if status == 'updated':
                updated.append(label + ': ' + reason)
            elif status == 'skipped':
                skipped.append(label + ': ' + reason)

    data["finance"]["checked_on"] = today
    version = next_version(before["election"].get("publication_version"))
    data["election"]["publication_version"] = version
    DATASET.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    report.update(receipts_updated=updated, receipts_skipped=skipped,
                  publication_version=version)

    # 3) Rebuild and run the full offline gate; publish only when green.
    sh(sys.executable, "scripts/build_site.py")
    gate = sh(sys.executable, "scripts/check_release.py", check=False)
    if gate.returncode != 0:
        report["gate"] = "FAILED — dataset NOT published"
        print(json.dumps(report, indent=2))
        print(gate.stdout[-3000:])
        raise SystemExit(1)
    report["gate"] = "Complete offline release gate passed"

    if args.skip_push:
        report["published"] = False
        print(json.dumps(report, indent=2))
        return

    token = read_secret(('GITHUB_TOKEN', 'GH_TOKEN'), args.github_token_file)
    sh("git", "add", DATASET.name, "index.html", "ballot.html")
    message = (f"FEC money refresh {today}: receipts + independent expenditures\n\n"
               f"Receipts updated: {len(updated)}; skipped with reason: {len(skipped)}.\n"
               f"IE layer refetched for all FEC-linked federal candidates. "
               f"Publication {version}. Full offline release gate green before push.")
    commit = sh("git", "commit", "-m", message, check=False)
    if "nothing to commit" in commit.stdout + commit.stderr:
        report["published"] = False
        report["note"] = "no changes since last refresh"
        print(json.dumps(report, indent=2))
        return
    if commit.returncode:
        raise SystemExit(redact('Commit failed: ' + commit.stdout + commit.stderr, (token, key)))
    sh("git", "fetch", "origin", "--quiet")
    ahead_behind = sh("git", "rev-list", "--left-right", "--count", "HEAD...origin/main").stdout.split()
    if ahead_behind != ["1", "0"]:
        report["published"] = False
        raise SystemExit(f"unexpected divergence from origin/main ({ahead_behind}); aborting push")
    push_main(token)
    report["published"] = True
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
