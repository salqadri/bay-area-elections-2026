"""Attach Hermes evidence summaries to every published Jev grade.

No provider calls here: the generator ran offline against the frozen archive;
this command validates each cached summary against its exact archived request,
freezes them into an immutable explanations archive and attaches a compact
per-candidate projection plus a top-level registry binding. Summaries explain
the saved score; they never regrade or replace raw provider answers.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re

from ballotpedia_endorsements import digest, dump
from publish_jev_grades import ROOT, DATASET
from score_grade import row_grade

QUEUE = 'research/gaza-grading/explanation-queue-2026-10-27-vfp.json'
NA_NOTE_MODEL = 'guide-editorial'
NA_NOTE_TEMPLATE = ("We could not find enough in {name}'s public record — statements, votes, sponsored bills, "
                    "endorsements or outside spending — on Palestine, Gaza or Israel to judge where {name} "
                    "stands on Palestinian justice. This race is marked N/A; we do not infer any stance "
                    "from silence.")
EXPLANATION_FIELD = 'pro_palestine_explanation'
SUMMARY_WORDS = (20, 130)


def validate_summary(result, row, grade, publication_id):
    errors = []
    if result.get('candidate_id') != row['id'] or result.get('request_sha256') != row['request_sha256']:
        errors.append('identity/request binding mismatch')
    if result.get('publication_id') != publication_id:
        errors.append('wrong publication id')
    summary = result.get('summary')
    if not isinstance(summary, str) or not summary.strip():
        errors.append('missing summary')
    else:
        words = len(summary.split())
        if not SUMMARY_WORDS[0] <= words <= SUMMARY_WORDS[1]:
            errors.append('summary outside %d-%d words' % SUMMARY_WORDS)
        import re as _re
        if _re.search(r'^\s*#', summary, _re.M) or '**' in summary or '\n' in summary.strip():
            errors.append('markdown or multiline text (inline hashtags inside quotes are fine)')
        if grade == 'N/A' and not re.search(r'insufficient|below.{0,30}0\.10|not enough (?:evidence|of this)|could ?n.t find|no (?:statements|record|mention)|canno?t judge|no clear position|too little to judge', summary, re.I):
            errors.append('N/A summary must state insufficient evidence without assigning a stance')
    if not isinstance(result.get('model'), str) or not result['model'].strip():
        errors.append('missing generating model')
    return errors


def build_archive(responses_dir, queue_path, publication_id):
    queue = json.loads((ROOT / queue_path).read_text())
    archive = json.loads((ROOT / queue['archive_path']).read_text())
    mapping = archive['score_grade_mapping']
    rows = {r['id']: r for r in archive['rows']}
    entries, missing = [], []
    for item in queue['candidates']:
        row = rows[item['id']]
        if item['request_sha256'] != row['request_sha256'] or digest(dump(row['request']).encode()) != row['request_sha256']:
            raise ValueError('Queue/archive request hash mismatch: ' + item['id'])
        path = responses_dir / (item['id'] + '.json')
        grade = row_grade(row, mapping) or 'N/A'
        if not path.exists():
            if grade == 'N/A':
                # N/A paragraphs are hand-written editorial notes, not model output.
                name = row['candidate']
                result = {'candidate_id': row['id'], 'request_sha256': row['request_sha256'],
                          'publication_id': publication_id, 'model': NA_NOTE_MODEL,
                          'summary': NA_NOTE_TEMPLATE.format(name=name),
                          'generated_at': None}
            else:
                missing.append('%s (%s)' % (item['candidate'], item['id']))
                continue
        else:
            result = json.loads(path.read_text())
        errors = validate_summary(result, row, grade, publication_id)
        if errors:
            raise ValueError('%s %s: %s' % (item['id'], item['candidate'], '; '.join(errors)))
        entries.append({'candidate_id': row['id'], 'position_id': row['position_id'],
                        'candidate': row['candidate'], 'roster': row['roster'],
                        'request_sha256': row['request_sha256'], 'grade': grade,
                        'summary': result['summary'].strip(), 'model': result['model'],
                        'generated_at': result.get('generated_at')})
    if missing:
        raise ValueError('%d summaries still missing (first 10): %s' % (len(missing), ', '.join(missing[:10])))
    return {'format': 'published-jev-grade-explanations/v1', 'publication_id': publication_id,
            'source_queue_path': queue_path, 'grades_archive_path': archive['id'],
            'generator': sorted({e['model'] for e in entries}),
            'note': ('Evidence summaries supporting each saved score; generated from the exact archived '
                     'request state, rubric and answers. Not model reasoning transcripts; never regrade.'),
             'entries': sorted(entries, key=lambda e: (e['position_id'], e['candidate']))}


def attach(data, archive, archive_path):
    if archive.get('format') != 'published-jev-grade-explanations/v1':
        raise ValueError('Unsupported explanations format')
    result = deepcopy(data)
    targets = {}
    for p in result['positions']:
        for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates'):
            for c in p.get(roster) or []:
                c.pop(EXPLANATION_FIELD, None)
                if 'pro_palestine_evaluation' in c:
                    targets[c['pro_palestine_evaluation']['candidate_id']] = c
    seen = set()
    for e in archive['entries']:
        c = targets.get(e['candidate_id'])
        if c is None or e['request_sha256'] != c['pro_palestine_evaluation']['request_sha256']:
            raise ValueError('Explanation does not bind the published evaluation: ' + e['candidate_id'])
        c[EXPLANATION_FIELD] = {'publication_id': archive['publication_id'],
                                'candidate_id': e['candidate_id'], 'request_sha256': e['request_sha256'],
                                'summary': e['summary'], 'model': e['model']}
        seen.add(e['candidate_id'])
    if seen != set(targets):
        raise ValueError('Every published evaluation needs an explanation (%d of %d)' % (len(seen), len(targets)))
    result['pro_palestine_grading']['explanations'] = {
        'publication_id': archive['publication_id'], 'archive_path': archive_path,
        'archive_sha256': digest(dump(archive).encode()),
        'source_queue_path': archive['source_queue_path'], 'generator': archive['generator']}
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--responses', type=Path, required=True)
    ap.add_argument('--queue', default=QUEUE)
    ap.add_argument('--output-archive', type=Path, required=True)
    ap.add_argument('--publication-version', help='Set election.publication_version (YYYY-MM-DD.N)')
    ap.add_argument('--schema-version', help='Set top-level schema_version (e.g. 1.25)')
    args = ap.parse_args()
    queue = json.loads((ROOT / args.queue).read_text())
    archive = build_archive(args.responses.resolve(), args.queue, queue['publication_id'])
    path = args.output_archive.resolve()
    if not path.is_relative_to(ROOT / 'research/gaza-grading'):
        raise ValueError('Store the immutable explanations archive under research/gaza-grading')
    text = json.dumps(archive, ensure_ascii=False, indent=1) + '\n'
    if path.exists() and path.read_text() != text:
        raise ValueError('Preserve the existing explanations archive; use a new path')
    data = attach(json.loads(DATASET.read_text()), archive, str(path.relative_to(ROOT)))
    if args.publication_version:
        import re as _re
        if not _re.fullmatch(r'\d{4}-\d{2}-\d{2}\.\d+', args.publication_version):
            raise ValueError('publication_version must be YYYY-MM-DD.N')
        data['election']['publication_version'] = args.publication_version
    if args.schema_version:
        schema = json.loads((ROOT / 'elections.schema.json').read_text())
        if schema['properties']['schema_version']['const'] != args.schema_version:
            raise ValueError('schema_version must match the schema const')
        data['schema_version'] = args.schema_version
    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    print(json.dumps({'attached': len(archive['entries']), 'archive': str(path.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
