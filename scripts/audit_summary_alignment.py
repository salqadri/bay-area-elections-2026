"""Audit narrative claims against recorded legislative responses and alignments.

This is a factual-consistency audit, not candidate grading or selection. It
never edits a summary, score, source record or recommendation. Provider inputs
and outputs are cached under the requested work directory.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re

from grade_gaza import build_state, jev_call
from build_recommendations import all_candidates

ROOT = Path(__file__).resolve().parent.parent
MENTION = re.compile(r'\b(?:voted|voting|(?:co-?)?sponsor(?:ed|ing)?|abstain(?:ed)?|AB\s*715|boycott|defund)', re.I)
INSTRUCTIONS = (
    'Audit factual consistency only. Do not grade candidates, endorse anyone, or decide whether a policy is good. '
    'Compare the paragraph with the supplied candidate records. An explicit tracker alignment is authoritative '
    'for how THIS dataset classifies an action: aligned, not aligned, neutral, unclassified. '
    'A No vote against defunding universities for boycotting Israel, when marked aligned, must not be described '
    'as a contrary/negative item. A Yes vote can support an adverse bill. Do not infer alignment from the word No, '
    'the bill title alone, or the paragraph\'s overall tone. Not elected/not voting is not an adverse vote. '
    'Distinguish cosponsoring, intending to cosponsor, and casting a vote. Preserve later corrections and dates. '
    'Do not treat the absence of unrelated material in this bounded input as a contradiction. '
    'If a claim lacks enough explicit information to decide its direction, choose needs_review rather than guessing.'
)


def collect(data, batch):
    positions = {p['id']: p for p in data['positions']}
    records = {}
    counts = {'paragraph_occurrences': 0, 'no_legislative_mention': 0, 'no_legislative_context': 0}

    def add(pid, candidate, text, origin):
        if not text:
            return
        counts['paragraph_occurrences'] += 1
        if not MENTION.search(text):
            counts['no_legislative_mention'] += 1
            return
        position = positions[pid]
        people = [c for c in all_candidates(position) if candidate is None or c['name'] == candidate]
        context = []
        for person in people:
            state = build_state(position, person, data)
            current = {field: state[field] for field in (
                'congressional_gaza_actions', 'congressional_gaza_context',
                'antisemitism_education_policy_evidence', 'gaza_evidence',
                'reviewed_gaza_platform_statement', 'reviewed_evidence_context',
            ) if state.get(field)}
            if current:
                context.append({'candidate': person['name'], **current})
        if not any(c.get('congressional_gaza_actions') or c.get('antisemitism_education_policy_evidence')
                   for c in context):
            counts['no_legislative_context'] += 1
            return
        identity = hashlib.sha256((pid + '\n' + str(candidate) + '\n' + text).encode()).hexdigest()
        if identity not in records:
            records[identity] = {'id': identity, 'position_id': pid, 'candidate': candidate,
                                 'paragraph': text, 'candidate_records': context, 'origins': []}
        records[identity]['origins'].append(origin)

    for p in data['positions']:
        for c in all_candidates(p):
            add(p['id'], c['name'], (c.get('pro_palestine_explanation') or {}).get('summary'),
                'pr_dataset_candidate')
    public_plan = json.loads((ROOT/'research/candidate-recommendations/recommendations-2026-10-28-latest.json').read_text())
    for race in public_plan['races']:
        if race.get('recommended'):
            add(race['position_id'], None, (race.get('summary') or {}).get('text'), 'pr_race_plan')
    for kind, field in (('candidate-results', 'summary'), ('race-results', 'text')):
        for path in sorted((batch/kind).glob('*.json')):
            item = json.loads(path.read_text())
            add(item['position_id'], item.get('candidate') if kind == 'candidate-results' else None,
                item[field], str(path.relative_to(ROOT)))
    counts['unique_paragraphs_to_audit'] = len(records)
    return list(records.values()), counts


def request_for(row):
    return {'model': 'jev-latest',
            'state': {k: row[k] for k in ('position_id', 'candidate', 'paragraph', 'candidate_records')},
            'questions': {'legislative_consistency': {
                'type': 'choice', 'instructions': INSTRUCTIONS,
                'criteria': {
                    'contradiction': 'A specific legislative response or explicit recorded alignment is reversed or materially misstated.',
                    'consistent': 'Assessable legislative claims agree with the supplied responses and explicit alignments.',
                    'needs_review': 'The paragraph makes a material legislative interpretation that the supplied record cannot resolve.',
                    'no_assessable_claim': 'There is no specific legislative response/alignment claim to assess.'}}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=Path, default=ROOT/'.research/summary-refresh-v9-2026-10-31')
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--jev-key-file', type=Path)
    parser.add_argument('--only', help='Optional stable position ID')
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    rows, counts = collect(json.loads((ROOT/'2026-11-03_Bay_Area_Elections.json').read_text()), args.batch)
    if args.only:
        rows = [row for row in rows if row['position_id'] == args.only]
    args.work_dir.mkdir(parents=True, exist_ok=True)
    (args.work_dir/'plan.json').write_text(json.dumps({'counts': counts, 'rows': rows}, indent=2) + '\n')
    print(json.dumps({'scope_counts': counts, 'selected': len(rows)}), flush=True)
    if args.plan_only:
        return
    if not args.jev_key_file:
        raise SystemExit('--jev-key-file is required for an uncached audit')
    key = args.jev_key_file.read_text().strip()

    def one(row):
        try:
            answer = jev_call(args.work_dir, request_for(row), key)['answers']['legislative_consistency']
            return {**row, 'audit': answer}
        except Exception as error:
            return {**row, 'error': type(error).__name__ + ': ' + str(error)[:200]}

    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(one, row) for row in rows]):
            row = future.result(); results.append(row)
            (args.work_dir/'results.json').write_text(json.dumps({'counts': counts, 'rows': results}, indent=2) + '\n')
            if row.get('error') or row.get('audit', {}).get('choice') in {'contradiction', 'needs_review'}:
                print(json.dumps({k: row.get(k) for k in ('position_id', 'candidate', 'audit', 'error')}), flush=True)
    print(json.dumps({'completed': len(results), 'errors': sum('error' in r for r in results)}), flush=True)


if __name__ == '__main__':
    main()
