#!/usr/bin/env python3
"""Register the Fresno grading batch as a targeted run in the playground review
bundle (aisha-current-scope / scott-final precedent), then re-pin the manifest
entries. The run file is a jev-playground-run/v1 with the exact fresh v11 rows
from done-ids.json; restore() revalidates every row hash before use.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys_path = str(ROOT / "scripts")
import sys
sys.path.insert(0, sys_path)
from grade_gaza import dump, digest, validate_questions  # noqa: E402

DONE = ROOT / ".research/jev-playground-fresno/done-ids.json"
BOOT = ROOT / ".research/jev-playground-fresno/bootstrap-fresno.json"
V11 = ROOT / "research/gaza-grading/criteria-pro-palestine-v11.json"
RUN_DIR = ROOT / "research/gaza-grading/fresno-county-2026-11-03"
RUN_FILE = RUN_DIR / "run.json"
MANIFEST = ROOT / "research/gaza-grading/playground-review-2026-10-30/manifest.json"


def main():
    if RUN_FILE.exists():
        raise SystemExit('preserve the existing run file')
    fresh = json.load(open(DONE))
    boot = json.load(open(BOOT))
    v11 = json.load(open(V11))['questions']
    validate_questions(v11)
    rows = []
    for tid in sorted(fresh):
        row = fresh[tid]
        request = row['request']
        if request['questions'] != v11:
            raise SystemExit('fresh row questions drift: ' + row['candidate'])
        if digest(dump(request).encode()) != row['request_sha256']:
            raise SystemExit('fresh row hash drift: ' + row['candidate'])
        rows.append({'id': row['id'], 'position_id': row['position_id'],
                     'candidate': row['candidate'], 'party': row.get('party'),
                     'roster': row['roster'], 'request': request,
                     'request_sha256': row['request_sha256'], 'response': row['response'],
                     'status': 'complete', 'finished_at': row.get('finished_at')})
    run_id = '20261103T201500Z-fresno222'
    run = {'format': 'jev-playground-run/v1', 'id': run_id,
           'created_at': '2026-11-03T20:15:00Z', 'model': 'jev-latest',
           'questions': v11, 'scope': 'all',
           'dataset_sha256': boot['latest']['dataset_sha256'],
           'state_version': boot['latest']['state_version'],
           'races': boot['latest']['races'], 'rows': rows, 'status': 'complete',
           'revision': len(rows), 'completed': len(rows), 'errors': 0}
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    RUN_FILE.write_text(json.dumps(run, ensure_ascii=False, indent=1) + '\n')
    raw = RUN_FILE.read_bytes()
    if json.loads(raw)['completed'] != len(rows):
        raise SystemExit('run file invalid')
    manifest = json.loads(MANIFEST.read_text())
    if any(e['path'].endswith('fresno-county-2026-11-03/run.json') for e in manifest['runs']):
        raise SystemExit('manifest already registers the Fresno run')
    manifest['runs'].append({
        'path': 'research/gaza-grading/fresno-county-2026-11-03/run.json',
        'run_id': run_id,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'candidates': len(rows)})
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n')
    print('registered run', run_id, 'rows', len(rows), flush=True)


if __name__ == '__main__':
    main()
