#!/usr/bin/env python3
"""Fresno County grading run (2026-11-03): evaluate the candidacies that joined
the dataset with Fresno County coverage, then merge them with the 1,296 exact
saved answers from jev-2026-11-03-final into one complete archive.

Every existing row keeps its exact saved request/response/variant assignment;
only the 222 new Fresno candidacies make provider calls, using the preferred
criteria v11. Rerunning resumes: completed candidate results are cached under
the work dir and reused without new calls.
"""
import json
import sys
import time
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from serve_jev_playground import RunManager, snapshot, STATE_VERSION  # noqa: E402
from grade_gaza import DATASET, dump, digest, now  # noqa: E402

WORK = ROOT / '.research/jev-playground-fresno'
FINAL = ROOT / 'research/gaza-grading/published-2026-11-03-final.json'
CRITERIA = ROOT / 'research/gaza-grading/criteria-pro-palestine-v11.json'
OUT = WORK / 'bootstrap-fresno.json'
ROSTERS = ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--jev-key-file', type=Path)
    cli.add_argument('--work-dir', type=Path, default=WORK)
    cli.add_argument('--plan-only', action='store_true', help='Inspect target count; no credentials or model calls')
    args = cli.parse_args()
    work = args.work_dir
    final = json.load(open(FINAL))
    have = {row['id'] for row in final['rows']}
    questions = json.load(open(CRITERIA))['questions']
    questions_sha = digest(dump(questions).encode())
    data = json.load(open(DATASET))
    current = snapshot(data)
    if current['state_version'] != STATE_VERSION:
        raise SystemExit('state version drift: ' + current['state_version'])
    by_id = {c['id']: c for c in current['candidates']}
    targets = [c['id'] for c in current['candidates'] if c['id'] not in have]
    stale = have - set(by_id)
    if stale:
        raise SystemExit(f'archived rows no longer in snapshot: {sorted(stale)[:5]}')
    print('targets', len(targets), 'carry-forward', len(have), flush=True)

    if args.plan_only:
        return
    key = args.jev_key_file.read_text().strip() if args.jev_key_file else os.environ.get('TYPESAFE_API_KEY','').strip()
    if not key:raise SystemExit('Provide --jev-key-file or TYPESAFE_API_KEY')

    manager = RunManager(work=work, key=key, workers=3)
    fresh = {}
    done_file = work / 'done-ids.json'
    if done_file.exists():
        for tid, row in json.load(open(done_file)).items():
            if tid not in targets:
                raise SystemExit('Cache contains a candidacy outside this import')
            expected = {'model':'jev-latest','state':by_id[tid]['state'],'questions':questions}
            if row.get('status') != 'complete' or row.get('request') != expected or row.get('request_sha256') != digest(dump(expected).encode()):
                raise SystemExit('Cached input changed; choose a new work directory instead of reusing old answers')
            fresh[tid] = row
        print('resumed', len(fresh), 'cached results', flush=True)
    for i, tid in enumerate(targets):
        if tid in fresh:
            continue
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
            raise SystemExit(f'Jev failed for {by_id[tid]["candidate"]}: {row.get("error")}')
        fresh[tid] = row
        done_file.write_text(json.dumps(fresh))
        print(f'[{i+1}/{len(targets)}]', by_id[tid]['candidate'],
              row['response']['answers']['pro_palestine_score']['score'], flush=True)

    # merged archive-shaped rows: carry-forward rows byte-identical, new rows fresh
    KEEP = ('id', 'position_id', 'candidate', 'party', 'roster',
            'status', 'request', 'request_sha256', 'response', 'finished_at', 'evaluation')
    rows = []
    for row8 in final['rows']:
        rows.append({k: row8[k] for k in KEEP if k in row8})
    for tid in targets:
        row = fresh[tid]
        rows.append({k: row[k] for k in KEEP if k in row} | {
            'status': 'complete',
            'evaluation': {'dataset_sha256': current['dataset_sha256'],
                           'state_version': STATE_VERSION,
                           'model': 'jev-latest',
                           'run_id': 'fresno-2026-11-03'}})
    latest = {'format': 'jev-playground-run/v1', 'id': 'latest', 'scope': 'latest',
              'created_at': now(), 'model': 'jev-latest',
              'questions': questions, 'status': 'complete',
              'dataset_sha256': current['dataset_sha256'], 'state_version': STATE_VERSION,
              'races': current['races'], 'rows': rows, 'revision': len(rows),
              'completed': len(rows), 'errors': 0}
    boot = {'snapshot': current, 'baseline': latest, 'latest': latest,
            'questions': questions,
            'score_grade_mapping': final['score_grade_mapping'],
            'default_score_grade_mapping': final['score_grade_mapping'],
            'key_configured': True, 'history': []}
    out = work/'bootstrap-fresno.json'
    out.write_text(json.dumps(boot))
    print('merged bootstrap saved', out, 'rows', len(rows), flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
