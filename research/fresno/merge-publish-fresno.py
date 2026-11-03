#!/usr/bin/env python3
"""Merge the Fresno bootstrap into a complete published archive (2026-11-03.2).

Carries jev-2026-11-03-final rows byte-identical (with their v10/v11 variant
bindings), registers v11 as a question variant, binds every new Fresno row to
the v11 questions hash, then runs publish_jev_grades freeze+attach exactly like
the playground publisher would.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from grade_gaza import dump, digest  # noqa: E402

FINAL = ROOT / "research/gaza-grading/published-2026-11-03-final.json"
BOOT = ROOT / ".research/jev-playground-fresno/bootstrap-fresno.json"
V11 = ROOT / "research/gaza-grading/criteria-pro-palestine-v11.json"
OUT = ROOT / "research/gaza-grading/published-2026-11-03-fresno.json"


def main():
    if OUT.exists():
        raise SystemExit('preserve the existing archive; use a new path')
    final = json.load(open(FINAL))
    boot = json.load(open(BOOT))
    latest = boot['latest']
    dataset_path = ROOT / "2026-11-03_Bay_Area_Elections.json"
    registry = json.load(open(dataset_path))['pro_palestine_grading'].get('previous_explanations')
    v11 = json.load(open(V11))
    v11_sha = digest(dump(v11['questions']).encode())
    # every new row must use the exact v11 questions
    have = {row['id'] for row in final['rows']}
    for row in latest['rows']:
        if row['id'] in have:
            continue
        if row['request']['questions'] != v11['questions']:
            raise SystemExit('new row not using exact v11 questions: ' + row['candidate'])
    archive = {
        'format': 'published-jev-grades/v1',
        'id': 'jev-2026-11-03-fresno',
        'published_on': '2026-11-03',
        'selection': 'latest successful saved evaluation per candidacy',
        'score_grade_mapping': final['score_grade_mapping'],
        'evidence_threshold': final['evidence_threshold'],
        'preferred_criteria_path': 'research/gaza-grading/criteria-pro-palestine-v11.json',
        'preferred_criteria': v11,
        'question_variants': list(final['question_variants']) + (
            [] if any(v['questions_sha256'] == v11_sha for v in final['question_variants'])
            else [{'criteria_path': 'research/gaza-grading/criteria-pro-palestine-v11.json',
                   'questions_sha256': v11_sha, 'criteria': v11}]),
        'candidate_question_variants': dict(final['candidate_question_variants']),
        'rows': latest['rows'],
    }
    for row in latest['rows']:
        if row['id'] not in have:
            archive['candidate_question_variants'][row['id']] = v11_sha
    if {row['id'] for row in archive['rows']} != set(archive['candidate_question_variants']):
        raise SystemExit('variant bindings must cover every row exactly')
    OUT.write_text(json.dumps(archive, ensure_ascii=False, indent=1) + '\n')
    print('archive written', OUT, 'rows', len(archive['rows']), flush=True)
    # freeze() validates before writing; run the publisher attach on the fresh archive
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'publish_jev_grades.py'),
         '--archive', str(OUT), '--published-on', '2026-11-03'],
        cwd=ROOT, text=True, capture_output=True)
    print(result.stdout, result.stderr)
    if result.returncode:
        raise SystemExit('attach failed')
    # A new score archive drops the earlier-assessment registry; re-attach it with
    # its current-publication pointer advanced to this archive, then re-pin the
    # registry hash (the pointer lives inside the archive bytes).
    if registry:
        earlier = ROOT / registry['archive_path']
        a = json.loads(earlier.read_text())
        a['current_publication_id'] = archive['id']
        earlier.write_text(json.dumps(a, ensure_ascii=False, indent=2) + '\n')
        import hashlib
        registry['archive_sha256'] = hashlib.sha256(earlier.read_bytes()).hexdigest()
        data = json.load(open(dataset_path))
        data['pro_palestine_grading']['previous_explanations'] = registry
        dataset_path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
        print('earlier-summaries pointer advanced and registry re-pinned', flush=True)


if __name__ == '__main__':
    main()
