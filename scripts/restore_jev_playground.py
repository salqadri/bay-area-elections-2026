"""Restore a committed review bundle into local playground history, without API calls.

Existing runs are never overwritten. Existing local thresholds take precedence;
use a fresh --work-dir to reproduce the committed review settings exactly.
"""
import argparse
import json
from pathlib import Path

from ballotpedia_endorsements import digest, dump
from grade_gaza import validate_questions, validate_response
from score_grade import validate_mapping

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUNDLE = ROOT / 'research/gaza-grading/playground-review-2026-10-30/manifest.json'


def load_review(bundle=DEFAULT_BUNDLE, root=ROOT):
    root = Path(root).resolve()
    manifest = json.loads(Path(bundle).read_text())
    if manifest.get('format') != 'jev-playground-review/v1':
        raise ValueError('Unsupported playground review bundle')
    mapping = validate_mapping(manifest['score_grade_mapping'])

    def source(path):
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError('Review source is outside the repository')
        return resolved

    preferred = json.loads(source(manifest['preferred_criteria_path']).read_text())
    validate_questions(preferred['questions'])
    if digest(dump(preferred['questions']).encode()) != manifest['preferred_questions_sha256']:
        raise ValueError('Preferred review prompt hash mismatch')
    runs, ids = [], set()
    for entry in manifest['runs']:
        raw = source(entry['path']).read_bytes()
        if digest(raw) != entry['sha256']:
            raise ValueError('Review run hash mismatch: ' + entry['path'])
        run = json.loads(raw)
        run_id = run['id']
        if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in run_id):
            raise ValueError('Invalid review run ID')
        if run_id in ids or run_id != entry['run_id'] or run.get('format') != 'jev-playground-run/v1':
            raise ValueError('Duplicate or mismatched review run')
        ids.add(run_id)
        validate_questions(run['questions'])
        if (run['status'] != 'complete' or run['errors'] or
                run['completed'] != len(run['rows']) or len(run['rows']) != entry['candidates']):
            raise ValueError('Review run must contain complete successful evaluations')
        row_ids = set()
        for row in run['rows']:
            request = row['request']
            identity = digest(dump([row['position_id'], row['candidate'], row['roster']]).encode())[:24]
            if row['id'] != identity or row['id'] in row_ids or row['status'] != 'complete':
                raise ValueError('Invalid or duplicate review candidacy')
            row_ids.add(row['id'])
            if (request['questions'] != run['questions'] or
                    digest(dump(request).encode()) != row['request_sha256']):
                raise ValueError('Review request hash or questions mismatch')
            validate_response(request['questions'], row['response'])
        runs.append((run_id, raw))
    return manifest, mapping, runs


def restore(bundle=DEFAULT_BUNDLE, work=ROOT / '.research/jev-playground-pr22'):
    manifest, mapping, runs = load_review(bundle)
    work = Path(work)
    # Validate every destination before writing any file.
    pending, existing = [], []
    for run_id, raw in runs:
        target = work / 'runs' / run_id / 'run.json'
        if target.exists():
            if target.read_bytes() != raw:
                raise ValueError('Refusing to overwrite a different local run: ' + run_id)
            existing.append(run_id)
        else:
            pending.append((target, raw))
    mapping_path = work / 'score-grade-mapping.json'
    if mapping_path.exists():
        validate_mapping(json.loads(mapping_path.read_text()))
    for target, raw in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    mapping_status = 'preserved_existing'
    if not mapping_path.exists():
        work.mkdir(parents=True, exist_ok=True)
        mapping_path.write_text(json.dumps(mapping, indent=2) + '\n')
        mapping_status = 'restored_from_bundle'
    return {'restored_runs': len(pending), 'already_present_runs': len(existing),
            'thresholds': mapping_status, 'preferred_criteria_path': manifest['preferred_criteria_path'],
            'work_dir': str(work)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument('--work-dir', type=Path, default=ROOT / '.research/jev-playground-pr22')
    args = parser.parse_args()
    print(json.dumps(restore(args.bundle, args.work_dir), indent=2))
