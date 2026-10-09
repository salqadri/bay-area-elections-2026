"""Apply reviewed guide observations without changing rosters or inferring support.

The dated manifest accounts for every source card, including held/out-of-scope
entries. No network access, fuzzy matching or model calls occur here.
"""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from publication_reviews import load_reviews, revised_rows

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / 'research/endorsements/peace-guides-2026-10-09.json'
GUIDES = {'Vote for Peace', 'AROC Action'}


def reviewed_findings(data, review):
    people = {(p['id'], c['name']) for p in data['positions'] for c in p.get('candidates') or []}
    for field, count_key in [('vote_for_peace_cards', 'vote_for_peace_dispositions'), ('aroc_cards', 'aroc_dispositions')]:
        cards = review[field]
        if len(cards) != review['counts'][field] or dict(Counter(c['action'] for c in cards)) != review['counts'][count_key]:
            raise ValueError('Source card counts disagree with dispositions: ' + field)
        if any(not c.get('reason') for c in cards):
            raise ValueError('Every source card needs a review reason')
        expected = []
        for card in cards:
            if card['action'] != 'publish':
                continue
            key = (card['position_id'], card['candidate'])
            if key not in people:
                raise ValueError('Reviewed guide candidacy missing: ' + repr(key))
            relation = 'endorsed' if field == 'aroc_cards' else {'Ally': 'supported', 'Opposed': 'opposed'}[card['source_label']]
            expected.append((key, relation, card['phase']))
        source_key = 'aroc_action' if field == 'aroc_cards' else 'vote_for_peace'
        actual = [((f['position_id'], f['candidate']), f['record']['relation'], f['record']['phase'])
                  for f in review['findings'] if f['source_key'] == source_key and f['record']['endorser'] in GUIDES]
        if sorted(expected) != sorted(actual) or len(expected) != len(set(expected)):
            raise ValueError('Published records disagree with source cards: ' + field)
    for field in ('findings', 'gaza_findings'):
        if len(review[field]) != review['counts'][field]:
            raise ValueError('Finding count mismatch: ' + field)
        for finding in review[field]:
            if (finding['position_id'], finding['candidate']) not in people or not finding.get('reason'):
                raise ValueError('Finding needs a reviewed current candidacy and reason')
    return review['findings'], review['gaza_findings']


def apply_guides(data, review):
    findings, evidence = reviewed_findings(data, review)
    people = {(p['id'], c['name']): c for p in data['positions'] for c in p.get('candidates') or []}
    for ident, note in review['notes'].items():
        if ident in data['notes'] and data['notes'][ident] != note:
            raise ValueError('Note ID collision: ' + ident)
        data['notes'][ident] = note
    for field, rows in [('endorsements', findings), ('gaza_evidence', evidence)]:
        for finding in rows:
            records = people[(finding['position_id'], finding['candidate'])].setdefault(field, [])
            record = finding['record']
            if field == 'endorsements':
                matches = [old for old in records if (old['endorser'], old['phase'], old['url']) ==
                           (record['endorser'], record['phase'], record['url'])]
            else:
                matches = [old for old in records if old['id'] == record['id']]
            if matches:
                if len(matches) != 1 or matches[0] != record:
                    raise ValueError('Conflicting existing observation; review before replacing: ' + repr(finding))
            else:
                records.append(deepcopy(record))
    data['coverage']['printed_candidates_with_gaza_evidence'] = sum(bool(c.get('gaza_evidence')) for c in people.values())
    return data


def check_guides(data, review=None, updates=None):
    review = review or json.loads(REVIEW.read_text())
    findings, evidence = reviewed_findings(data, review)
    updates = load_reviews() if updates is None else updates
    findings = revised_rows(findings, 'endorsements', updates, lambda r: r['endorser'] in GUIDES)
    evidence = revised_rows(evidence, 'gaza_evidence', updates)
    people = {(p['id'], c['name']): c for p in data['positions'] for c in p.get('candidates') or []}
    errors = []
    for field, rows in [('endorsements', findings), ('gaza_evidence', evidence)]:
        for finding in rows:
            records = people[(finding['position_id'], finding['candidate'])].get(field, [])
            if records.count(finding['record']) != 1:
                errors.append(finding['candidate'] + ': missing or changed reviewed peace-guide ' + field)
    expected = [(f['position_id'], f['candidate'], f['record']) for f in findings if f['record']['endorser'] in GUIDES]
    for (position_id, name), c in people.items():
        for r in c.get('endorsements', []):
            if r['endorser'] in GUIDES and (position_id, name, r) not in expected:
                errors.append(name + ': unreviewed peace-guide recommendation')
    for ident, note in review['notes'].items():
        if data['notes'].get(ident) != note:
            errors.append('Changed peace-guide provenance note: ' + ident)
    return errors


if __name__ == '__main__':
    from apply_endorsement_review import apply_review, encode, DATA, EXPORT, REVIEW as PRIOR_REVIEW
    data, export = apply_review(json.loads(DATA.read_text()), json.loads(PRIOR_REVIEW.read_text()), json.loads(EXPORT.read_text()))
    DATA.write_text(encode(data))
    EXPORT.write_text(encode(export, indent=1))
    print('Applied reviewed Vote for Peace, AROC and linked-source findings.')
