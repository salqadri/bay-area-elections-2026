"""Read-only audit of dated public evidence across published Git history.

This finds missing IDs; absence is a research lead, never authority to restore a
quarantined claim. It does not apply Jev's legislative or funding input cutoffs.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
DATASET = '2026-11-03_Bay_Area_Elections.json'
ROSTERS = ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates')


def evidence(data):
    for position in data.get('positions', []):
        for roster in ROSTERS:
            for candidate in position.get(roster) or []:
                for item in candidate.get('gaza_evidence', []):
                    yield (position['id'], candidate['name'], item['id']), item


def audit(start, end, ref='HEAD', dataset=None):
    date.fromisoformat(start); date.fromisoformat(end)
    if start > end:
        raise ValueError('Start must not follow end')
    git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT)
    current = json.loads((ROOT / DATASET).read_text()) if dataset is None else dataset
    current_items = dict(evidence(current))
    commits = git('log', '--first-parent', '--format=%H', ref, '--', DATASET).decode().splitlines()
    historical = {}
    for revision in commits:
        data = json.loads(git('show', revision + ':' + DATASET))
        for key, item in evidence(data):
            if start <= (item.get('date') or '') <= end and key not in historical:
                historical[key] = {'position_id': key[0], 'candidate': key[1],
                                   'record': item, 'newest_seen_commit': revision}
    return {'format': 'historical-gaza-preservation-audit/v1', 'ref': ref,
            'ref_sha': git('rev-parse', ref).decode().strip(), 'start': start, 'end': end,
            'commits_checked': len(commits), 'historical_records': len(historical),
            'retained_ids': len(set(historical) & set(current_items)),
            'missing_records': [row for key, row in historical.items() if key not in current_items],
            'limitation': 'Missing IDs need review for duplicates, identity, attribution and dates; this audit never restores evidence or bypasses quarantine. Month-only records retain their stated precision.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', default='2023-10-07'); parser.add_argument('--end', default='2023-12-31')
    parser.add_argument('--ref', default='HEAD'); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.start, args.end, args.ref)
    path=args.output.resolve()
    if path.exists() or path in {(ROOT / DATASET).resolve(), (ROOT / 'elections.schema.json').resolve()}:
        raise SystemExit('Use a new audit output; maintained inputs and old audits must be preserved')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'commits_checked': result['commits_checked'], 'historical_records': result['historical_records'],
                      'missing_records': len(result['missing_records']), 'output': str(path)}))
