"""Apply the dated, manually reviewed endorsement layer and reject known bad imports.

No network calls. Idempotent; preserves unrelated research and printed rosters.
The filtered collector export and curated manifest deliberately remain separate.
"""
from collections import Counter
import json
from pathlib import Path

from check_published_endorsements import blocked_reason, check_endorsements, source_key

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / '2026-11-03_Bay_Area_Elections.json'
REVIEW = ROOT / 'research/endorsements/targeted-2026-10-09.json'
EXPORT = ROOT / 'research/endorsements/endorsements-export-2026-10-09.json'


def encode(value, indent=2):
    return json.dumps(value, ensure_ascii=False, indent=indent) + '\n'


def apply_review(data, review, export):
    if data['schema_version'] not in {'1.12', '1.13'}:
        raise ValueError('Review this dated migration before applying to a different schema version')
    people = {(p['id'], c['name']): c for p in data['positions'] for c in p.get('candidates') or []}
    for ident, text in review['notes'].items():
        if ident in data['notes'] and data['notes'][ident] != text:
            raise ValueError('Note ID collision: ' + ident)
        data['notes'][ident] = text
    for key, c in people.items():
        retained = [r for r in c.get('endorsements', []) if not blocked_reason(r)]
        if retained:
            c['endorsements'] = retained
        else:
            c.pop('endorsements', None)
    for finding in review['findings']:
        key = (finding['position_id'], finding['candidate'])
        if key not in people:
            raise ValueError('Review candidacy no longer in the printed roster: ' + repr(key))
        r = finding['record']
        if r['url'] != review['sources'][finding['source_key']]['url']:
            raise ValueError('Review source/record URL mismatch')
        if blocked_reason(r):
            raise ValueError('Curated finding is quarantined')
        records = people[key].setdefault('endorsements', [])
        matches = [i for i, old in enumerate(records) if (old['endorser'], old['phase'], source_key(old['url'])) == (r['endorser'], r['phase'], source_key(r['url']))]
        if len(matches) > 1:
            raise ValueError('Ambiguous duplicate; review before replacing')
        if matches:
            old = records[matches[0]]
            if old['checked_on'] > r['checked_on']:
                raise ValueError('Refusing to overwrite newer endorsement research')
            records[matches[0]] = dict(r)
        else:
            records.append(dict(r))
    # Filter the historical export without pretending the separate manually
    # reviewed support records were produced by the deterministic collector.
    retained = []
    for r in export['records']:
        source = export['sources'][r['source_id']]
        endorser = export['endorsers'][r['endorser_id']]
        if not blocked_reason({'url': source['url'], 'endorser': endorser['name']}):
            retained.append(r)
    export['records'] = retained
    ids = {r['id'] for r in retained}
    for c in export['candidates'].values():
        c['record_ids'] = [i for i in c['record_ids'] if i in ids]
        if not c['record_ids']:
            c['research_status'] = 'incomplete'
    for registry, field in [('sources', 'source_id'), ('endorsers', 'endorser_id')]:
        used = {r[field] for r in retained}
        export[registry] = {k: v for k, v in export[registry].items() if k in used}
    export['scope'] = ('October 9 collector snapshot, filtered by quarantine-2026-10-09.json; '
                       'generated_at and source_dataset_sha256 describe the original collector run. '
                       'Separate manually reviewed findings: targeted-2026-10-09.json. '
                       'Not a complete or independently audited endorsement inventory.')
    data['schema_version'] = '1.13'
    data['coverage']['printed_candidates_with_endorsements'] = sum(bool(c.get('endorsements')) for c in people.values())
    limitation = ('Endorsement research was partially reviewed October 9, 2026. Records distinguish endorsements, '
                  'support ratings, campaign claims and secondary reports. Primary support is not automatically '
                  'a November endorsement. Missing or inaccessible evidence is unknown, not proof of no endorsements.')
    if limitation not in data['coverage']['limitations']:
        data['coverage']['limitations'].append(limitation)
    errors = check_endorsements(data)
    if errors:
        raise ValueError('\n'.join(errors))
    return data, export


if __name__ == '__main__':
    data, export = apply_review(json.loads(DATA.read_text()), json.loads(REVIEW.read_text()), json.loads(EXPORT.read_text()))
    # Validate everything before touching either destination.
    data_text, export_text = encode(data), encode(export, indent=1)
    DATA.write_text(data_text)
    EXPORT.write_text(export_text)
    records = [r for p in data['positions'] for c in p.get('candidates') or [] for r in c.get('endorsements', [])]
    print(json.dumps({'candidacies': data['coverage']['printed_candidates_with_endorsements'], 'records': len(records),
                      'relations': dict(Counter(r['relation'] for r in records))}, indent=2))
