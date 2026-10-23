"""Jev System One grader for Gaza/pro-Palestine positions, reusable across races and rubrics.

plan → grade → report over any candidate scope, using a versioned criteria file (score + choice
questions; output always carries pro_palestine_score and gaza_grade). The per-candidate state is
deliberately succinct: identity line, IE spenders for/against with amounts, campaign platform
points, Gaza evidence items — no boilerplate notes. Decisions are cached against the exact
request contract, so re-runs only pay for changed inputs. Nothing here publishes; results stay a
held batch until reviewed through the normal publication workflow.

    python3 scripts/grade_gaza.py plan --scope house-nationwide --batch house-2026-10-22
    python3 scripts/grade_gaza.py grade --batch house-2026-10-22 --jev-key-file /secure/key
    python3 scripts/grade_gaza.py report --batch house-2026-10-22
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ballotpedia_endorsements import accepted, digest, dump, save, now  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / '2026-11-03_Bay_Area_Elections.json'
WORK = ROOT / '.research/gaza-grading'
DEFAULT_CRITERIA = ROOT / 'research/gaza-grading/criteria-gaza-grade-v1.json'
MODEL = 'jev-latest'  # score-type questions require the current flagship model per TypeSafe docs


def jev_call(work, request, key):
    """POST to System One with the exact {model,state,questions} contract; cache by request hash."""
    path = work / 'decisions' / (digest(dump(request).encode()) + '.json')
    if path.exists():
        saved = json.loads(path.read_text())
        if saved['request'] != request:
            raise ValueError('Changed Jev request cache')
        return saved['response']
    body = dump(request).encode()
    last_error = None
    for attempt in range(6):
        req = urllib.request.Request('https://api.typesafe.ai/v1/systemone', data=body,
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                answer = json.load(response)
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            last_error = error
            status = getattr(error, 'code', None)
            if status not in (429, 502, 503, 529) and not isinstance(error, (urllib.error.URLError, TimeoutError)):
                raise
            time.sleep(min(60, 2 ** attempt * 2))
    else:
        raise RuntimeError(f'Jev call kept failing: {last_error}')
    if not str(answer.get('model', '')).startswith('jev-'):
        raise ValueError('Unexpected judgment model ' + str(answer.get('model')))
    save(path, {'request': request, 'response': answer})
    return answer

SCOPES = {
    # name: (office_category, id prefix) — extend for new regions/offices.
    'house-nationwide': ('U.S. House', 'US2026-'),
    'senate-nationwide': ('U.S. Senate', 'US2026-'),
    'governor-nationwide': ('Statewide executive', 'US2026-'),
}


def candidates(data, scope):
    category, prefix = SCOPES[scope] if scope in SCOPES else (None, None)
    rows = []
    for p in data['positions']:
        if category and p.get('office_category') != category:
            continue
        if prefix and not p['id'].startswith(prefix):
            continue
        for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot'):
            for c in p.get(roster) or []:
                rows.append((p, c, roster))
    return rows


def money(value):
    return f'${value:,.0f}'


def build_state(p, c, data):
    """Succinct evidence state: identity + IE money both directions + platform + Gaza evidence."""
    import re
    match = re.search(r'state:(\w\w)', p.get('ocd_division_id') or '')
    parts = {
        'candidate': c['name'],
        'office': f"{p.get('district_or_seat', '')} {p.get('office', '')}".strip(),
        'state': (match.group(1).upper() if match else ('CA' if p.get('counties') else '')),
        'party': data['codes']['party'].get(c.get('party'), c.get('party')),
    }
    ie = c.get('independent_expenditures') or {}
    spenders = data.get('ie_spenders', {})
    for direction, label in (('for', 'spenders_supporting'), ('against', 'spenders_opposing')):
        rows = [f"{spenders.get(str(i['spender_id']), {}).get('name', i['spender_id'])} {money(i['amount'])}"
                for i in sorted(ie.get('items', []), key=lambda x: -x['amount']) if i['direction'] == direction]
        if rows:
            parts[label] = rows[:12]
    grade = c.get('uscpr_grade') or {}
    official = [f"{g['period']}: {g.get('grade') or 'Not graded'}" for g in grade.get('grades', [])]
    if official:
        parts['official_uscpr_scorecard'] = official
    platform = c.get('platform_positions') or {}
    points = [f"{pt['topic']}: {pt['summary']}" for pt in (platform.get('points') or [])[:8]]
    if points:
        parts['campaign_platform_points'] = points
    gaza = c.get('gaza_platform') or {}
    if gaza.get('status') == 'statement_found' and gaza.get('summary'):
        parts['reviewed_gaza_platform_statement'] = gaza['summary']
    evidence = [f"{e['date']}: {e['summary']}" for e in (c.get('gaza_evidence') or [])[:12]]
    if evidence:
        parts['gaza_evidence'] = evidence
    records = []
    for record in c.get('gaza_voting_records') or []:
        for action in record.get('actions', [])[:8]:
            records.append(f"{action.get('date', '')} {action.get('kind', '')}: {action.get('title', '')}".strip())
    if records:
        parts['congressional_gaza_actions'] = records[:12]
    return parts


def plan(data, criteria, scope):
    rows = candidates(data, scope)
    items = []
    for p, c, roster in rows:
        state = build_state(p, c, data)
        request = {'model': MODEL, 'state': state, 'questions': criteria['questions']}
        items.append({'position_id': p['id'], 'candidate': c['name'], 'roster': roster,
                      'party': c.get('party'), 'district_or_seat': p.get('district_or_seat'),
                      'request_sha256': digest(dump(request).encode()), 'state': state})
    return {'format': 'gaza-grading-plan/v1', 'scope': scope, 'criteria_id': criteria['id'],
            'planned_on': now(), 'candidates': len(items), 'items': items}


def grade(work, plan_doc, criteria, key, workers=3):
    decisions = {}

    questions = criteria['questions']

    def one(item):
        request = {'model': MODEL, 'state': item['state'], 'questions': questions}
        ref = digest(dump(request).encode())
        base = {**{k: item[k] for k in ('position_id', 'candidate', 'roster', 'party', 'district_or_seat')},
                'request_sha256': ref}
        try:
            response = jev_call(work, request, key)
        except Exception as error:  # one failed candidate must not stop the batch; reruns retry via cache
            return {**base, 'error': type(error).__name__ + ': ' + str(error)[:200]}
        decisions[ref] = {'request': request, 'response': response}
        answers = response.get('answers', {})
        out = {**base, 'answers': answers}
        g = answers.get('gaza_grade', {})
        s = answers.get('pro_palestine_score', {})
        out['gaza_grade'] = g.get('choice')
        out['gaza_grade_confidence'] = g.get('confidence')
        out['gaza_grade_accepted'] = bool(g) and accepted(g, set(questions['gaza_grade']['criteria']), 0.75)
        out['pro_palestine_score'] = s.get('score')
        out['pro_palestine_confidence'] = s.get('confidence')
        return out

    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, result in enumerate(pool.map(one, plan_doc['items']), 1):
            results.append(result)
            if n % 20 == 0 or n == len(plan_doc['items']):
                print(json.dumps({'graded': n, 'total': len(plan_doc['items'])}), flush=True)
    batch = {'format': 'gaza-grading/v1', 'scope': plan_doc['scope'], 'criteria_id': plan_doc['criteria_id'],
             'model': MODEL, 'run_on': now(), 'results': results,
             'decisions': {ref: decisions[ref] for ref in {r['request_sha256'] for r in results} if ref in decisions}}
    save(work / 'results.json', batch)
    return summary(batch)


def summary(batch):
    from collections import Counter
    grades = Counter(r.get('gaza_grade') or 'none' for r in batch['results'])
    accepted_grades = sum(1 for r in batch['results'] if r.get('gaza_grade_accepted'))
    return {'graded': len(batch['results']), 'errors': sum('error' in r for r in batch['results']),
            'grades': dict(sorted(grades.items())),
            'grade_accepted_at_0.75': accepted_grades,
            'scores_recorded': sum(isinstance(r.get('pro_palestine_score'), (int, float)) for r in batch['results'])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', type=Path, default=DATASET)
    ap.add_argument('--criteria', type=Path, default=DEFAULT_CRITERIA)
    ap.add_argument('--work-root', type=Path, default=WORK)
    sub = ap.add_subparsers(dest='command', required=True)
    for name in ('plan', 'grade', 'report'):
        s = sub.add_parser(name)
        s.add_argument('--scope', choices=sorted(SCOPES), default='house-nationwide')
        s.add_argument('--batch', required=True)
        if name == 'grade':
            s.add_argument('--jev-key-file', type=Path, required=True)
            s.add_argument('--workers', type=int, default=3)
    args = ap.parse_args()
    criteria = json.loads(args.criteria.read_text())
    work = args.work_root / args.batch
    if args.command == 'plan':
        doc = plan(json.loads(args.dataset.read_text()), criteria, args.scope)
        save(work / 'plan.json', doc)
        print(json.dumps({'scope': doc['scope'], 'criteria': doc['criteria_id'], 'candidates': doc['candidates']}))
    elif args.command == 'grade':
        doc = json.loads((work / 'plan.json').read_text())
        if doc['criteria_id'] != criteria['id']:
            raise SystemExit('Batch plan was built against a different criteria file')
        print(json.dumps(grade(work, doc, criteria, args.jev_key_file.read_text().strip(), args.workers)))
    else:
        batch = json.loads((work / 'results.json').read_text())
        report = {**summary(batch), 'scope': batch['scope'], 'criteria_id': batch['criteria_id'], 'run_on': batch['run_on']}
        save(work / 'report.json', report)
        print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
