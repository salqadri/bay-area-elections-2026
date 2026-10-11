"""Triage campaign-site endorsement proposals with the TypeSafe Jev decision model.

Reads quote_verified proposals from the campaign scan ledger, asks Jev
(/v1/systemone choice questions) per site whether each entry is a genuine
endorsement of that campaign's candidate or page noise (staff list, donor
wall, ballot measure, candidate endorsing others...). Emits a decisions JSON
for `campaign_endorsements.py apply-review`; it never touches the dataset.

The API key comes from the TYPESAFE_API_KEY environment variable and is never
written to disk or logs. Standard library only; resumable via its own ledger
table so an interrupted run can continue. Review policy: accept only when Jev
picks `endorsement` with probability >= --threshold AND the mechanical quote
gate passed; everything else stays undecided for human review.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from campaign_endorsements import DEFAULT_DB, DATASET  # noqa: E402
from endorsement_extract import candidates_from_data  # noqa: E402

API = 'https://api.typesafe.ai/v1/systemone'
MODEL = os.environ.get('JEV_MODEL', 'jev-latest')
CHUNK = 20          # entries per API call (calibrated: per-question entry text keeps batch accuracy)
QPS_SLEEP = 0.35    # gentle pacing; Jev retries 429/5xx with backoff anyway


def post(state, questions, key):
    body = json.dumps({'model': MODEL, 'state': state, 'questions': questions}).encode()
    for attempt in range(6):
        try:
            req = urllib.request.Request(API, data=body, headers={
                'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(2 ** attempt); continue
            raise RuntimeError(f'jev HTTP {e.code}: {e.read()[:200]!r}') from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 5:
                time.sleep(2 ** attempt); continue
            raise RuntimeError(f'jev network: {e}') from e


def ensure_state_table(db):
    db.execute('''CREATE TABLE IF NOT EXISTS jev_triage(
        proposal_id TEXT PRIMARY KEY, site_key TEXT, choice TEXT, p_endorse REAL,
        reviewed_at TEXT)''')
    db.commit()


def build_state(campaign_url, candidate_lines):
    return '\n'.join([f'Campaign website: {campaign_url}',
                      "This is the campaign's OWN website for: " + '; '.join(candidate_lines),
                      'The page displays several entries in what appears to be an endorsement/supporter section. '
                      'Each question below is about ONE entry quoted inside it; judge only that entry.'])


def q_instructions(e):
    return (f'This page entry — "{e["endorser"]}" (kind {e.get("kind","unspecified")}) '
            f'quote from the page: "{e["quote"]}" — is it an endorsement of this candidate?')


CRITERIA = {'endorsement': 'An organization, official, or named person is presented as endorsing/supporting this candidate',
            'not_endorsement': 'Staff/volunteer roster, donor list, ballot measure, this candidate endorsing others, navigation or generic text'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--threshold', type=float, default=0.75)
    ap.add_argument('--limit-sites', type=int, default=0)
    ap.add_argument('--out', default=str(ROOT / '.research/endorsements/review/campaign-jev-decisions.json'))
    args = ap.parse_args()
    key = os.environ.get('TYPESAFE_API_KEY')
    if not key:
        raise SystemExit('TYPESAFE_API_KEY environment variable is required')

    db = sqlite3.connect(DEFAULT_DB); db.row_factory = sqlite3.Row
    ensure_state_table(db)
    rows = candidates_from_data(json.loads(DATASET.read_text()))
    todo_sites = [r['site_key'] for r in db.execute(
        '''SELECT DISTINCT p.site_key FROM proposals p
           WHERE p.gate='quote_verified' AND p.proposal_id NOT IN (SELECT proposal_id FROM jev_triage)
           ORDER BY p.site_key''')]
    if args.limit_sites:
        todo_sites = todo_sites[:args.limit_sites]

    calls = accepted = 0
    for site_key in todo_sites:
        task = db.execute('SELECT * FROM tasks WHERE site_key=?', (site_key,)).fetchone()
        cand_lines = [f"{rows[i]['name']} ({rows[i].get('office','?')})" for i in json.loads(task['candidacy_ids']) if i in rows]
        props = [dict(p) for p in db.execute(
            "SELECT proposal_id, record_json FROM proposals WHERE site_key=? AND gate='quote_verified' "
            'AND proposal_id NOT IN (SELECT proposal_id FROM jev_triage)', (site_key,))]
        if not props:
            continue
        entries = [(f'q{n}', p['proposal_id'], json.loads(p['record_json'])) for n, p in enumerate(props)]
        for start in range(0, len(entries), CHUNK):
            chunk = entries[start:start + CHUNK]
            questions = {qid: {'type': 'choice', 'instructions': q_instructions(rec),
                               'criteria': CRITERIA} for qid, _, rec in chunk}
            resp = post(build_state(task['campaign_url'], cand_lines), questions, key)
            calls += 1
            for qid, pid, rec in chunk:
                a = (resp.get('answers') or {}).get(qid) or {}
                probs = a.get('probabilities') or {}
                p_end = float(probs.get('endorsement', 0.0))
                db.execute('INSERT OR REPLACE INTO jev_triage VALUES(?,?,?,?,?)',
                           (pid, site_key, a.get('choice'), round(p_end, 3), time.strftime('%Y-%m-%dT%H:%M:%S%z')))
            db.commit()
        time.sleep(QPS_SLEEP)

    # emit decisions for apply-review from the full triage ledger
    accepted_rows = db.execute(
        "SELECT proposal_id FROM jev_triage WHERE choice='endorsement' AND p_endorse>=?", (args.threshold,))
    ids = [r['proposal_id'] for r in accepted_rows]
    decisions = [{'proposal_id': pid, 'action': 'accept',
                  'reason': f'Mechanical quote gate + Jev {MODEL} endorsement classification (p>={args.threshold})',
                  'reviewed_by': 'jev-1.13 via campaign scan'} for pid in ids]
    Path(args.out).write_text(json.dumps(decisions, indent=1) + '\n')
    held = db.execute("SELECT COUNT(*) c FROM jev_triage WHERE NOT (choice='endorsement' AND p_endorse>=?)",
                      (args.threshold,)).fetchone()['c']
    print(json.dumps({'api_calls': calls, 'accepted_written': len(decisions), 'held_for_review': held,
                      'out': args.out}, indent=1))


if __name__ == '__main__':
    main()
