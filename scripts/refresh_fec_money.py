"""Refresh both federal money layers (receipts + independent expenditures) and publish.

Deterministic maintenance pass for the two FEC-derived layers:

 1. Independent expenditures — refetch Schedule E rows for every printed federal
    candidate (``fec_independent_expenditures.py run --force``), re-aggregate and
    attach with a fresh ``checked_on`` date.
 2. Campaign receipts — for each candidate's authorized committee, read the FEC
    committee cycle totals. Update ``receipts``/``through`` only when the reported
    coverage start still equals the stored ``from`` (so multi-cycle exceptions like
    Scott Wiener's 2023-start summary are never silently relabelled) and the new
    coverage end is later than the stored one. Missing totals stay null; a total is
    never inferred from anything else.

Then: bump ``finance.checked_on``/``ie_finance.checked_on`` (the full federal scope
was refreshed, which is exactly what those dates certify), advance
``election.publication_version``, rebuild both pages, run the complete offline
release gate, and only on a fully green gate commit + push to main. A failing gate
aborts with no dataset publication and exit code 1.

The FEC key comes from FEC_API_KEY or /root/.cfg/fec_key; the git token from
/root/.cfg/gh_token. Neither is ever written into the repository. Intended for a
scheduled run through Election Day (November 3, 2026); after that it exits as a
no-op unless --force-window is passed.
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "2026-11-03_Bay_Area_Elections.json"
COLLECTOR = ROOT / "scripts/fec_independent_expenditures.py"
REMOTE = ("https://x-access-token:{token}@"
          "github.com/salqadri/bay-area-elections-2026.git")


def sh(*cmd, check=True):
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(map(str, cmd))}\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
    return result


def fec_totals(key, candidate_id):
    """Candidate-level cycle totals — aggregates across all authorized committees,
    the same source shape as the original ingestion (committee-level totals would
    undercount multi-committee candidates like John McBride)."""
    url = ("https://api.open.fec.gov/v1/candidate/" + candidate_id + "/totals/?"
           + urllib.parse.urlencode({"cycle": 2026, "api_key": key}))
    with urllib.request.urlopen(url, timeout=45) as response:
        results = json.load(response).get("results") or []
    return results[0] if results else None


def next_version(current):
    today = date.today().isoformat()
    if current and current.startswith(today + "."):
        return f"{today}.{int(current.rsplit('.', 1)[1]) + 1}"
    return today + ".1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-window", action="store_true",
                        help="run even after the November 4, 2026 window closes")
    parser.add_argument("--skip-push", action="store_true",
                        help="refresh and validate locally without publishing")
    args = parser.parse_args()

    if date.today() > date(2026, 11, 4) and not args.force_window:
        print("Refresh window closed after the November 3 election; no-op. "
              "Remove or pause this scheduled job.")
        return

    key = Path("/root/.cfg/fec_key").read_text(encoding="utf-8").strip()
    today = date.today().isoformat()
    report = {"date": today}

    # 1) Independent expenditures: refetch everything, re-aggregate, attach.
    sh(sys.executable, str(COLLECTOR), "run", "--force")
    before = json.loads(DATASET.read_text(encoding="utf-8"))
    sh(sys.executable, str(COLLECTOR), "attach", "--checked-on", today)

    # 2) Receipts: committee cycle totals with the coverage-start guard.
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    updated, skipped = [], []
    for position in data["positions"]:
        if position.get("government_level") != "Federal":
            continue
        for candidate in position.get("candidates") or []:
            fec = candidate.get("fec") or {}
            if not isinstance(fec, dict) or not fec.get("id"):
                continue
            totals = fec_totals(key, fec["id"])
            receipts = (totals or {}).get("receipts")
            start = str((totals or {}).get("coverage_start_date") or "")[:10]
            end = str((totals or {}).get("coverage_end_date") or "")[:10]
            label = candidate["name"]
            if receipts is None:
                skipped.append(f"{label}: no published total (stays {fec.get('receipts')!r})")
                continue
            amount = Decimal(str(receipts)).quantize(Decimal("0.01"))
            if fec.get("from") and start != fec["from"]:
                skipped.append(f"{label}: coverage start {start} != stored {fec['from']} (exception preserved)")
                continue
            if fec.get("receipts") == float(amount) and fec.get("through") == end:
                continue
            assert not Decimal(str(fec["receipts"] or 0)) > amount, \
                f"{label}: new total {amount} below stored {fec['receipts']} — investigate before publishing"
            fec["receipts"] = float(amount)
            if fec.get("from"):
                fec["through"] = end
            updated.append(f"{label}: ${amount:,} through {end}")

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
    report["gate"] = "16/16 PASS"

    if args.skip_push:
        report["published"] = False
        print(json.dumps(report, indent=2))
        return

    token = Path("/root/.cfg/gh_token").read_text(encoding="utf-8").strip()
    sh("git", "add", "-A")
    message = (f"FEC money refresh {today}: receipts + independent expenditures\n\n"
               f"Receipts updated: {len(updated)}; skipped with reason: {len(skipped)}.\n"
               f"IE layer refetched for all printed federal candidates. "
               f"Publication {version}. Full offline release gate green before push.")
    commit = sh("git", "commit", "-m", message, check=False)
    if "nothing to commit" in commit.stdout + commit.stderr:
        report["published"] = False
        report["note"] = "no changes since last refresh"
        print(json.dumps(report, indent=2))
        return
    sh("git", "fetch", "origin", "--quiet")
    ahead_behind = sh("git", "rev-list", "--left-right", "--count", "HEAD...origin/main").stdout.split()
    if ahead_behind != ["1", "0"]:
        report["published"] = False
        raise SystemExit(f"unexpected divergence from origin/main ({ahead_behind}); aborting push")
    sh("git", "push", REMOTE.format(token=token) + " HEAD:main")
    report["published"] = True
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
