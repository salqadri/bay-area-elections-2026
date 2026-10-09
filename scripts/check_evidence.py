"""Guard against known evidence regressions; this does not certify political facts."""
import copy
import datetime
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
QUARANTINE = ROOT / 'docs/reviews/evidence-quarantine.json'


def canonical_url(url):
    parts = urlsplit(url)
    host = (parts.hostname or '').lower().removeprefix('www.')
    status = re.fullmatch(r'/[^/]+/status/(\d+)(?:/.*)?', parts.path)
    if host in {'x.com', 'twitter.com'} and status:
        return 'https://x.com/i/status/' + status[1]
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in {'fbclid', 'gclid'}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path.rstrip('/'), urlencode(sorted(query)), ''))


def check_evidence(data, quarantine=None):
    if quarantine is None:
        quarantine = json.loads(QUARANTINE.read_text(encoding='utf-8'))['items']
    # A duplicate's canonical URL also belongs to the retained representative.
    # Duplicate reintroduction is checked by source+excerpt below instead.
    blocked = {(r['position_id'], r['candidate'], canonical_url(r['evidence']['url']))
               for r in quarantine if r['reason'] != 'duplicate_source'}
    errors, identities = [], {}
    for position in data['positions']:
        for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates'):
            for candidate in position.get(roster) or []:
                sources = set()
                for evidence in candidate.get('gaza_evidence', []):
                    eid = evidence.get('id', '?')
                    context = f"{position['id']} / {candidate['name']} / {eid}"
                    url = canonical_url(evidence.get('url', ''))
                    if (position['id'], candidate['name'], url) in blocked:
                        errors.append(context + ': quarantined source reintroduced without a documented resolution')
                    identity = (candidate['name'], evidence)
                    if eid in identities and identities[eid] != identity:
                        errors.append(context + ': evidence ID reused with a different meaning')
                    identities[eid] = identity
                    excerpt = ' '.join((evidence.get('quote') or evidence.get('summary', '')).split()).casefold()
                    key = (url, excerpt)
                    if key in sources:
                        errors.append(context + ': duplicate source and excerpt, including equivalent X status URLs')
                    sources.add(key)
                    summary = evidence.get('summary', '')
                    if summary.startswith('X post:'):
                        errors.append(context + ': raw X excerpt is not a concise summary')
                    ending = summary.rstrip('"\u201d\u2019\' )')
                    if len(summary) == 240 and not ending.endswith(('.', '!', '?', '\u2026')):
                        errors.append(context + ': summary appears cut off at the field limit')
                    method = evidence.get('date_method')
                    if method == 'wayback_first_capture' and not evidence.get('date_note'):
                        errors.append(context + ': archive bound needs an explanatory date note')
                    if method == 'source_observed' and (not evidence.get('date_note') or
                            evidence.get('date') != evidence.get('checked_on') or
                            evidence.get('source_kind') != 'voter_guide'):
                        errors.append(context + ': guide observation needs its check date, voter_guide source kind and date note')
                    try:
                        parts = [int(p) for p in evidence['date'].split('-')]
                        lower_bound = datetime.date(parts[0], parts[1] if len(parts) > 1 else 1,
                                                    parts[2] if len(parts) > 2 else 1)
                        checked = datetime.date.fromisoformat(evidence['checked_on'])
                        if lower_bound > checked:
                            errors.append(context + ': evidence date is later than its verification date')
                    except (KeyError, ValueError, IndexError):
                        errors.append(context + ': invalid evidence or verification date')
    return errors


def regression_checks(data, quarantine):
    sample = copy.deepcopy(data)
    p = sample['positions'][0]
    c = p['candidates'][0]
    source = copy.deepcopy(c['gaza_evidence'][0])
    source.update(id='GE-99991', url='https://x.com/example/status/123456789',
                  summary='Candidate called for a bilateral ceasefire.', quote='A bilateral ceasefire is needed.')
    c['gaza_evidence'] = [source, {**source, 'id': 'GE-99992', 'url': 'https://twitter.com/renamed/status/123456789?utm_source=share'}]
    assert any('duplicate source' in error for error in check_evidence(sample, []))
    assert canonical_url('https://example.com/story/?utm_source=x#comment') == canonical_url('https://example.com/story')
    c['gaza_evidence'] = [{**source, 'date': '0000'}]
    assert any('invalid evidence' in error for error in check_evidence(sample, []))
    c['gaza_evidence'] = [{**source, 'date': '2100-01-01'}]
    assert any('later than' in error for error in check_evidence(sample, []))
    c['gaza_evidence'] = [{**source, 'summary': 'X post: I support a ceasefire.'}]
    assert any('raw X excerpt' in error for error in check_evidence(sample, []))
    restored = copy.deepcopy(data)
    record = quarantine[0]
    person = next(c for p in restored['positions'] if p['id'] == record['position_id']
                  for c in p['candidates'] if c['name'] == record['candidate'])
    person.setdefault('gaza_evidence', []).append({**record['evidence'], 'id': 'GE-99993'})
    assert any('quarantined source' in error for error in check_evidence(restored, quarantine))
    # Different statements from the same source are legitimate; shared source URLs alone are not duplicates.
    c['gaza_evidence'] = [source, {**source, 'id':'GE-99994', 'quote':'Hostages must be released.'}]
    assert not check_evidence(sample, [])
    return 7


if __name__ == '__main__':
    data = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text(encoding='utf-8'))
    quarantine = json.loads(QUARANTINE.read_text(encoding='utf-8'))['items']
    errors = check_evidence(data, quarantine)
    if errors:
        raise SystemExit('\n'.join(errors))
    count = regression_checks(data, quarantine)
    print(json.dumps({'passed': True, 'regression_cases': count, 'quarantined_items': len(quarantine),
                      'limitation': 'Checks known failure classes; identity and source truth still require review.'}, indent=2))
