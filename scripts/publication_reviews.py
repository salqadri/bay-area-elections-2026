"""Immutable, ordered review history used by publication guards and importers."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / 'research/publication-reviews.json'


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_reviews():
    registry = json.loads(REGISTRY.read_text())
    if registry['version'] != 1:
        raise ValueError('Unknown publication review registry version')
    result, seen = [], set()
    for entry in registry['reviews']:
        path = (ROOT / entry['path']).resolve()
        if not path.is_relative_to(ROOT / 'research/reviews') or file_sha(path) != entry['sha256']:
            raise ValueError('Registered review moved or changed: ' + entry['path'])
        review = json.loads(path.read_text())
        if review['id'] in seen:
            raise ValueError('Duplicate publication review ID')
        if result and review['reviewed_on'] < result[-1]['reviewed_on']:
            raise ValueError('Publication reviews must be in chronological order')
        result.append(review)
        seen.add(review['id'])
    return result


def revised_rows(rows, field, reviews, include_new=lambda record: False):
    """Project dated baseline expectations through explicit reviewed changes."""
    result = deepcopy(rows)
    for review in reviews:
        for change in review['decisions']:
            if change['action'] != 'change' or change['field'] != field:
                continue
            def matches(row, record):
                return row['position_id'] == change['position_id'] and row['candidate'] == change['candidate'] and row['record'] == record
            touched = any(matches(row, change['before']) for row in result)
            result = [row for row in result if not matches(row, change['before'])]
            after = change['after']
            if after is not None and (touched or include_new(after)) and not any(matches(row, after) for row in result):
                result.append({'position_id': change['position_id'], 'candidate': change['candidate'], 'record': deepcopy(after)})
    return result


def check_registered_reviews(data, reviews):
    people = {(p['id'], c['name']): c for p in data['positions'] for c in p.get('candidates') or []}
    errors = []
    for field in ('endorsements', 'gaza_evidence'):
        expected = revised_rows([], field, reviews, lambda r: True)
        for row in expected:
            records = people.get((row['position_id'], row['candidate']), {}).get(field, [])
            if records.count(row['record']) != 1:
                errors.append(row['candidate'] + ': missing or changed registered review record')
        for review in reviews:
            for change in review['decisions']:
                if change['action'] != 'change' or change['field'] != field or change['before'] is None:
                    continue
                key = change['position_id'], change['candidate']
                before = change['before']
                restored = any((row['position_id'], row['candidate']) == key and row['record'] == before for row in expected)
                if not restored and before in people.get(key, {}).get(field, []):
                    errors.append(change['candidate'] + ': superseded registered record reintroduced')
    for review in reviews:
        for ident, note in review['notes'].items():
            if data['notes'].get(ident) != note:
                errors.append('Registered review note missing or changed: ' + ident)
    return errors
