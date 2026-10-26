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
import math
import re
import unicodedata
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ballotpedia_endorsements import digest, dump, save, now  # noqa: E402
from candidate_community import community_state  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / '2026-11-03_Bay_Area_Elections.json'
WORK = ROOT / '.research/gaza-grading'
DEFAULT_CRITERIA = ROOT / 'research/gaza-grading/criteria-pro-palestine-v3.json'
STATE_VERSION = 'candidate-evidence-v7-community-observations'
MODEL = 'jev-latest'  # score-type questions require the current flagship model per TypeSafe docs


def validate_questions(questions):
    if not isinstance(questions, dict) or not questions:
        raise ValueError('Questions must be a nonempty JSON object keyed by question name')
    try:
        encoded = json.dumps(questions, allow_nan=False)
    except (ValueError, TypeError):
        raise ValueError('Questions must contain finite JSON values') from None
    if len(encoded.encode()) > 256000:
        raise ValueError('Questions exceed 256 KB')
    for name, q in questions.items():
        if not name or not isinstance(q, dict) or q.get('type') not in {'choice', 'score', 'noul'}:
            raise ValueError('Each named question must use choice, score, or noul')
        if set(q) - {'type', 'instructions', 'criteria'}:
            raise ValueError('Unknown question property in ' + name)
        if q.get('instructions') is not None and not isinstance(q['instructions'], (str, dict, list)):
            raise ValueError(name + ': instructions must be text, an object or an array')
        criteria = q.get('criteria')
        if q['type'] == 'choice' and (not isinstance(criteria, dict) or not 1 <= len(criteria) <= 255):
            raise ValueError(name + ': choice criteria must be a nonempty object (up to 255 choices)')
        if q['type'] == 'score' and (not isinstance(criteria, list) or not 1 <= len(criteria) <= 10):
            raise ValueError(name + ': score criteria must contain 1–10 ordered levels')
        if q['type'] == 'noul' and criteria is not None and (not isinstance(criteria, dict) or set(criteria) - {'true', 'false'}):
            raise ValueError(name + ': noul criteria may define true and false')
    return questions


def validate_response(questions, response):
    if not isinstance(response, dict) or not str(response.get('model', '')).startswith('jev-'):
        raise ValueError('Unexpected Jev response/model')
    answers = response.get('answers', {})
    if not isinstance(answers, dict):
        raise ValueError('Jev answers must be an object')
    if set(answers) != set(questions):
        raise ValueError('Jev response is missing or adds question answers')
    def number(v, low, high):
        return type(v) in (int, float) and math.isfinite(v) and low <= v <= high
    for name, q in questions.items():
        a = answers[name]
        if not isinstance(a, dict) or a.get('type') != q['type']:
            raise ValueError('Unexpected answer type for ' + name)
        if q['type'] == 'noul':
            if not number(a.get('noul'), 0, 1):
                raise ValueError('Invalid yes/true probability for ' + name)
            continue
        if not number(a.get('confidence'), 0, 1):
            raise ValueError('Invalid confidence for ' + name)
        keys = set(q['criteria']) if q['type'] == 'choice' else {str(i) for i in range(len(q['criteria']))}
        probs = a.get('probabilities', {})
        if not isinstance(probs, dict) or set(probs) != keys or any(not number(v, 0, 1) for v in probs.values()):
            raise ValueError('Invalid answer probabilities for ' + name)
        if q['type'] == 'choice' and a.get('choice') not in keys:
            raise ValueError('Invalid choice for ' + name)
        if q['type'] == 'score' and not number(a.get('score'), 0, len(keys) - 1):
            raise ValueError('Invalid score for ' + name)
    return response


def jev_call(work, request, key, force=False):
    """POST to System One with the exact {model,state,questions} contract; cache by request hash."""
    path = work / 'decisions' / (digest(dump(request).encode()) + '.json')
    if path.exists() and not force:
        saved = json.loads(path.read_text())
        if saved['request'] != request:
            raise ValueError('Changed Jev request cache')
        validate_response(request['questions'], saved['response'])
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
            if status in (401, 403):
                raise PermissionError('Jev authentication failed; check the local server key') from None
            if status is not None and status not in (429, 500, 502, 503, 504, 529):
                raise RuntimeError(f'Jev rejected the request (HTTP {status})') from None
            time.sleep(min(60, 2 ** attempt * 2))
    else:
        raise RuntimeError('Jev request failed after retries') from None
    validate_response(request['questions'], answer)
    save(path, {'request': request, 'response': answer})
    return answer

SCOPES = {
    # name: (office_category, id prefix) — extend for new regions/offices.
    'house-all': ('U.S. House', None),
    'house-nationwide': ('U.S. House', 'US2026-'),
    'senate-nationwide': ('U.S. Senate', 'US2026-'),
    'governor-nationwide': ('Statewide executive', 'US2026-'),
}


def candidates(data, scope):
    category, prefix = SCOPES[scope] if scope in SCOPES else (None, None)
    rows = []
    for p in data['positions']:
        if p.get('ballot_status') == 'excluded':
            continue
        if category and p.get('office_category') != category:
            continue
        if prefix and not p['id'].startswith(prefix):
            continue
        for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates'):
            for c in p.get(roster) or []:
                rows.append((p, c, roster))
    return rows


def money(value):
    return f'${value:,.0f}'


def endorser_key(name):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower())


def focused_endorsements(p, c):
    focus = json.loads((ROOT / 'research/gaza-grading/endorsement-focus-v3.json').read_text())
    aliases = {endorser_key(name) for entity in focus['entities'] for name in entity['aliases']}
    observations = [{k: e[k] for k in ('endorser', 'relation', 'phase', 'historical', 'rating', 'verification', 'shared') if k in e}
                    for e in c.get('endorsements') or [] if endorser_key(e['endorser']) in aliases]
    original = [e for e in c.get('endorsements') or [] if endorser_key(e['endorser']) in aliases]
    for record, source in zip(observations, original):
        if endorser_key(record['endorser']) == 'voteforpeace':
            record.update({k: source[k] for k in ('url', 'checked_on', 'source_label') if k in source})
    # Exact reviewed candidacy mappings, including Neutral cards deliberately held
    # out of the public endorsement import. Neutral is an observation, not support.
    guide = json.loads((ROOT / 'research/endorsements/peace-guides-2026-10-09.json').read_text())
    for card in guide['vote_for_peace_cards']:
        if ((card.get('position_id'), card.get('candidate')) != (p['id'], c['name']) or
                card['action'] not in {'publish', 'neutral_no_recommendation'}):
            continue
        matches = [e for e in observations if endorser_key(e['endorser']) == 'voteforpeace'
                   and e.get('phase') == card['phase'] and e.get('url') == card['url'] and not e.get('historical')]
        if matches:
            for record in matches:
                # Keep canonical observations authoritative if research was updated.
                if record.get('rating', card['source_label']) == card['source_label'] and record['relation'] == {'Ally': 'supported', 'Opposed': 'opposed', 'Neutral': 'neutral'}[card['source_label']]:
                    record['source_label'] = card['source_label']
        elif card['action'] == 'neutral_no_recommendation':
            # A newer canonical record, even for a different phase, supersedes
            # this held observation rather than implicitly becoming Neutral.
            if any(endorser_key(e['endorser']) == 'voteforpeace' for e in observations):
                continue
            observations.append({'endorser': 'Vote for Peace', 'relation': 'neutral', 'rating': 'Neutral',
                                 'source_label': card['source_label'], 'phase': card['phase'],
                                 'url': card['url'], 'checked_on': guide['reviewed_on'],
                                 'verification': 'endorser_statement'})
    return observations


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
    parts.update(community_state(p, c))
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
    endorsements = focused_endorsements(p, c)
    if endorsements:
        parts['focused_endorsement_observations'] = endorsements
    records = []
    registry = (data.get('gaza_voting') or {}).get('actions', {})
    for record in sorted(c.get('gaza_voting_records') or [], key=lambda r: -r.get('congress', 0)):
        for action in record.get('actions', []):
            metadata = registry.get(action.get('action_id'), {})
            records.append({'congress': record.get('congress'), 'title': metadata.get('title', action.get('title', '')),
                            'kind': metadata.get('kind', action.get('kind', '')),
                            'date': metadata.get('date', metadata.get('date_label')),
                            'response': action.get('value')})
    if records:
        parts['congressional_gaza_actions'] = records
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
    return {'format': 'gaza-grading-plan/v2', 'dataset_sha256': digest(dump(data).encode()), 'state_version': STATE_VERSION, 'scope': scope, 'criteria_id': criteria['id'],
            'planned_on': now(), 'candidates': len(items), 'items': items}


def grade(work, plan_doc, criteria, key, workers=3, force=False, score_grade_mapping=None):
    from score_grade import DEFAULT_MAPPING, validate_mapping, row_grade
    mapping = validate_mapping(score_grade_mapping if score_grade_mapping is not None else DEFAULT_MAPPING)
    validate_questions(criteria['questions'])
    decisions = {}

    questions = criteria['questions']

    def one(item):
        request = {'model': MODEL, 'state': item['state'], 'questions': questions}
        ref = digest(dump(request).encode())
        base = {**{k: item[k] for k in ('position_id', 'candidate', 'roster', 'party', 'district_or_seat')},
                'request_sha256': ref}
        try:
            response = jev_call(work, request, key, force=force)
        except Exception as error:  # one failed candidate must not stop the batch; reruns retry via cache
            return {**base, 'error': type(error).__name__ + ': ' + str(error)[:200]}
        decisions[ref] = {'request': request, 'response': response}
        answers = response.get('answers', {})
        out = {**base, 'state': item['state'], 'answers': answers}
        g = answers.get('gaza_grade', {})
        s = answers.get('pro_palestine_score', {})
        out['gaza_grade'] = g.get('choice')
        out['gaza_grade_confidence'] = g.get('confidence')
        out['pro_palestine_score'] = s.get('score')
        out['pro_palestine_confidence'] = s.get('confidence')
        out['pro_palestine_score_grade'] = row_grade({'status': 'complete', 'request': request, 'response': response}, mapping)
        return out

    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, result in enumerate(pool.map(one, plan_doc['items']), 1):
            results.append(result)
            if n % 20 == 0 or n == len(plan_doc['items']):
                print(json.dumps({'graded': n, 'total': len(plan_doc['items'])}), flush=True)
    batch = {'format': 'gaza-grading/v2', 'state_version': plan_doc['state_version'], 'questions': questions, 'scope': plan_doc['scope'], 'criteria_id': plan_doc['criteria_id'],
             'model': MODEL, 'dataset_sha256': plan_doc.get('dataset_sha256'), 'run_on': now(), 'results': results,
             'score_grade_mapping': mapping,
             'decisions': {ref: decisions[ref] for ref in {r['request_sha256'] for r in results} if ref in decisions}}
    save(work / 'results.json', batch)
    return summary(batch)


def summary(batch):
    from collections import Counter
    grades = Counter(r.get('gaza_grade') or 'none' for r in batch['results'])
    return {'graded': len(batch['results']), 'errors': sum('error' in r for r in batch['results']),
            'grades': dict(sorted(grades.items())),
            'scores_recorded': sum(isinstance(r.get('pro_palestine_score'), (int, float)) for r in batch['results'])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', type=Path, default=DATASET)
    ap.add_argument('--criteria', type=Path, default=DEFAULT_CRITERIA)
    ap.add_argument('--work-root', type=Path, default=WORK)
    sub = ap.add_subparsers(dest='command', required=True)
    for name in ('plan', 'grade', 'report'):
        s = sub.add_parser(name)
        s.add_argument('--scope', choices=sorted(SCOPES), default='house-all')
        s.add_argument('--batch', required=True)
        if name == 'grade':
            s.add_argument('--jev-key-file', type=Path, required=True)
            s.add_argument('--workers', type=int, default=3)
            s.add_argument('--force', action='store_true', help='Make fresh calls even for cached requests')
            s.add_argument('--score-grade-mapping', type=Path, help='JSON with five inclusive upper_bounds for F–B; A ends at 5')
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
        mapping = json.loads(args.score_grade_mapping.read_text()) if args.score_grade_mapping else None
        print(json.dumps(grade(work, doc, criteria, args.jev_key_file.read_text().strip(), args.workers, args.force, mapping)))
    else:
        batch = json.loads((work / 'results.json').read_text())
        report = {**summary(batch), 'scope': batch['scope'], 'criteria_id': batch['criteria_id'], 'run_on': batch['run_on']}
        save(work / 'report.json', report)
        print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
