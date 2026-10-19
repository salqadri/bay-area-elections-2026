"""Reconstruct dated enrichment fixtures in memory for historical importer tests.

Current publication validity is checked separately. Future reviewed changes must
not make a historical capture test assert that old recommendations are current.
"""
from copy import deepcopy
from datetime import date
from urllib.parse import urlsplit

from endorsement_extract import norm
from publication_reviews import load_reviews, RECORD_FIELDS, SINGLETON_FIELDS, candidate_records


def _endorsement_slot(record):
    """Duplicate-detection key mirroring check_published_endorsements."""
    host = (urlsplit(record.get('url', '')).hostname or '').removeprefix('www.').lower()
    return (norm(record.get('endorser', '')), record.get('relation'), record.get('phase'),
            (host, urlsplit(record.get('url', '')).path.rstrip('/').lower()),
            record.get('historical', False))


def before_registered_updates(data):
    result = deepcopy(data)
    people = {(p['id'], c['name']): c for p in result['positions'] for c in p.get('candidates') or []}
    for review in reversed(load_reviews()):
        for change in reversed(review['decisions']):
            if change['action'] != 'change':
                continue
            person = people[(change['position_id'], change['candidate'])]
            records = candidate_records(person, change['field'])
            if change['after'] is not None:
                records = [r for r in records if r != change['after']]
            if change['before'] is not None and change['before'] not in records:
                superseded = change['field'] == 'endorsements' and any(
                    _endorsement_slot(r) == _endorsement_slot(change['before'])
                    and str(r.get('checked_on', '')) > str(review.get('reviewed_on', ''))
                    for r in records)
                if not superseded:
                    records.append(deepcopy(change['before']))
            if records:
                person[change['field']] = records[0] if change['field'] in SINGLETON_FIELDS else records
            else:
                person.pop(change['field'], None)
        for change in reversed(review.get('shared_changes', [])):
            if change['before'] is None:
                result.pop(change['field'], None)
            else:
                result[change['field']] = deepcopy(change['before'])
    for field in RECORD_FIELDS:
        metric = 'printed_candidates_with_' + field
        if metric in result['coverage']:
            result['coverage'][metric] = sum(bool(c.get(field)) for c in people.values())
    return result
