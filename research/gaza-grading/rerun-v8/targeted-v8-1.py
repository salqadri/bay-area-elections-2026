#!/usr/bin/env python3
"""v8.1 targeted rerun (owner directive 2026-10-30): SB403/caste context demoted to
an explicitly LOW-WEIGHT channel (max ±0.2, never moves a grade band alone).

Reruns ONLY the 19 candidacies whose grading state actually changed under
STATE v20 (`caste_legislation_context` split out of the education channel), then
merges them with the 1,277 byte-identical answers from jev-2026-10-30-v8 and
writes a bootstrap-equivalent snapshot for publish_jev_grades. All 1,296 rows in
the output carry the CURRENT v20 state, so the publication stays consistent.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from serve_jev_playground import RunManager, snapshot, STATE_VERSION  # noqa: E402
from grade_gaza import DATASET, dump, digest  # noqa: E402

KEY = Path('/root/.cfg/typesafe_key').read_text().strip()
WORK = ROOT / '.research/jev-playground-v8'
V8 = ROOT / 'research/gaza-grading/published-2026-10-30-v8.json'
CRITERIA = ROOT / 'research/gaza-grading/criteria-pro-palestine-v8.json'
OUT = WORK / 'bootstrap-v8-1.json'
TARGETS = ROOT / '.research/v8-1-rerun-ids.json'


def main():
    v8 = json.load(open(V8))
    targets = set(json.load(open(TARGETS)))
    data = json.load(open(DATASET))
    current = snapshot(data)
    if current['state_version'] != STATE_VERSION:
        raise SystemExit('state version drift: ' + current['state_version'])
    by_id = {c['id']: c for c in current['candidates']}
    questions = json.load(open(CRITERIA))['questions']

    manager = RunManager(work=WORK, key=KEY, workers=3)
    fresh = {}
    for tid in sorted(targets):
        while manager.active:
            time.sleep(5)
        run = manager.start(questions, candidate_id=tid)
        while True:
            cur = manager.get(run['id'])
            if cur['status'] not in {'running', 'cancelling'}:
                break
            time.sleep(3)
        row = cur['rows'][0]
        if cur['status'] != 'complete' or row['status'] != 'complete':
            raise SystemExit(f'Jev rerun failed for {by_id[tid]["candidate"]}: {row.get("error")}')
        fresh[tid] = row
        print('rerode', by_id[tid]['candidate'],
              row['response']['answers']['pro_palestine_score']['score'], flush=True)

    # merged archive-shaped run: every row current-state, answers = fresh or v8
    rows = []
    for row8 in v8['rows']:
        base = {k: row8.get(k) for k in ('id', 'position_id', 'candidate', 'party', 'roster',
                                         'response', 'finished_at')}
        state = by_id[row8['id']]['state'] | {'candidate_roster': row8['roster']}
        if row8['id'] in fresh:
            row = fresh[row8['id']]
            state = row['request']['state']
            response = row['response']
            finished = row.get('finished_at')
        else:
            response = row8['response']
            finished = row8.get('finished_at')
        request = {'model': 'jev-latest', 'state': state, 'questions': questions}
        rows.append({**base, 'request': request,
                     'request_sha256': digest(dump(request).encode()), 'status': 'complete',
                     'response': response, 'finished_at': finished,
                     'evaluation': {'created_at': row8['evaluation']['created_at'],
                                    'dataset_sha256': current['dataset_sha256'],
                                    'state_version': STATE_VERSION,
                                    'model': 'jev-latest',
                                    'run_id': 'v8-1-merge',
                                    'finished_at': finished,
                                    'request_sha256_frozen': row8['request_sha256']}})
    boot = {
        'snapshot': current,
        'baseline': {'format': 'jev-playground-run/v1', 'id': 'v8-1-merge', 'created_at': v8['published_on'],
                     'model': 'jev-latest', 'questions': questions, 'status': 'complete',
                     'dataset_sha256': current['dataset_sha256'], 'state_version': STATE_VERSION,
                     'races': current['races'], 'rows': rows, 'revision': len(rows),
                     'completed': len(rows), 'errors': 0},
        'latest': None,
        'questions': questions,
        'score_grade_mapping': v8['score_grade_mapping'],
        'default_score_grade_mapping': v8['score_grade_mapping'],
        'key_configured': True,
        'history': [],
    }
    # latest must mirror baseline for publish freeze
    latest = dict(boot['baseline'])
    latest.update({'id': 'latest', 'scope': 'latest'})
    boot['latest'] = latest
    OUT.write_text(json.dumps(boot))
    print('merged bootstrap saved', OUT, 'rows', len(rows), flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
