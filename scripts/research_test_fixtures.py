"""Reconstruct dated enrichment fixtures in memory for historical importer tests.

Current publication validity is checked separately. Future reviewed changes must
not make a historical capture test assert that old recommendations are current.
"""
from copy import deepcopy
from publication_reviews import load_reviews


def before_registered_updates(data):
    result = deepcopy(data)
    people = {(p['id'], c['name']): c for p in result['positions'] for c in p.get('candidates') or []}
    for review in reversed(load_reviews()):
        for change in reversed(review['decisions']):
            if change['action'] != 'change':
                continue
            person = people[(change['position_id'], change['candidate'])]
            records = person.get(change['field'], [])
            if change['after'] is not None:
                records = [r for r in records if r != change['after']]
            if change['before'] is not None and change['before'] not in records:
                records.append(deepcopy(change['before']))
            if records:
                person[change['field']] = records
            else:
                person.pop(change['field'], None)
    for field in ('endorsements', 'gaza_evidence'):
        result['coverage']['printed_candidates_with_' + field] = sum(bool(c.get(field)) for c in people.values())
    return result
