"""Draft, preview and apply scoped endorsement/evidence updates from any publisher.

No network or automatic political judgments. A draft holds every observation for
review. Changes require exact before/after values, office identity and provenance.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re

from endorsement_extract import candidates_from_data, norm, office_matches
from publication_reviews import ROOT, REGISTRY, file_sha, load_reviews, check_registered_reviews
from research_scope import DATA, select_scope, add_scope_arguments
from research_endorsements import atomic_json, digest, dump
from schema_validation import SCHEMA, check

FIELDS = {'endorsements': 'endorsementRecord', 'gaza_evidence': 'stanceEvidence'}


def identity(position):
    return {key: position.get(key) for key in ('office', 'jurisdiction', 'district_or_seat', 'term', 'election_type')}


def record_key(field, record):
    if field == 'gaza_evidence':
        return record['id']
    from check_published_endorsements import source_key
    return norm(record['endorser']), record['phase'], source_key(record['url'])


def prepare(data, review, prior_reviews=None, validate=True):
    """Return a new dataset and a reviewable delta; never mutate caller input."""
    prior_reviews = load_reviews() if prior_reviews is None else prior_reviews
    if review['version'] != 1 or not re.fullmatch(r'[a-z0-9][a-z0-9-]{3,100}', review['id']):
        raise ValueError('Invalid review version or ID')
    if review['election_date'] != data['election']['date'] or date.fromisoformat(review['reviewed_on']) > date.today():
        raise ValueError('Wrong election or future review date')
    if prior_reviews and review['reviewed_on'] < prior_reviews[-1]['reviewed_on']:
        raise ValueError('Review predates registered research')
    if not review['counties']:
        raise ValueError('Explicit county scope is required')
    selection = select_scope(data, review['counties'])
    if selection['missing_counties']:
        raise ValueError('Add verified official rosters before applying research to a new county')
    selected = {p['id']: p for p in selection['positions']}
    result = deepcopy(data)
    people = {(p['id'], c['name']): c for p in result['positions'] for c in p.get('candidates') or []}
    for ident, note in review['notes'].items():
        if not re.fullmatch(r'N[0-9]{3,}', ident) or not isinstance(note, str) or not note.strip():
            raise ValueError('Invalid provenance note')
        if ident in result['notes'] and result['notes'][ident] != note:
            raise ValueError('Cannot overwrite a shared note: ' + ident)
        result['notes'][ident] = note
    counts, seen, changed_keys = Counter(), set(), set()
    for decision in review['decisions']:
        ident = decision['id']
        if ident in seen or not isinstance(ident, str) or not ident:
            raise ValueError('Every source observation needs a unique decision ID')
        seen.add(ident)
        if len(decision.get('reason', '').strip()) < 8:
            raise ValueError('Every decision needs a concrete review reason')
        source = review['sources'][decision['source_key']]
        if not re.fullmatch(r'[0-9a-f]{64}', source.get('content_sha256', '')):
            raise ValueError('Source needs the hash of the actual retrieved content')
        if not source.get('retrieval') or not source.get('publisher') or not source.get('url', '').startswith('https://'):
            raise ValueError('Source needs publisher, retrieval method and HTTPS URL')
        if not (date.fromisoformat(source['checked_on']) <= date.fromisoformat(review['reviewed_on'])):
            raise ValueError('Source check date is later than review')
        if decision['action'] == 'hold':
            counts['held'] += 1
            continue
        if decision['action'] != 'change' or decision['field'] not in FIELDS:
            raise ValueError('Unknown decision action or field')
        field, before, after = decision['field'], decision['before'], decision['after']
        basis = decision.get('evidence', {})
        for required in ('identity_basis', 'date_basis', 'relationship_basis' if field == 'endorsements' else 'issue_basis'):
            if len(basis.get(required, '').strip()) < 8:
                raise ValueError('Reviewed change needs explicit ' + required)
        key = decision['position_id'], decision['candidate']
        if key not in people or key[0] not in selected or decision['identity'] != identity(selected[key[0]]):
            raise ValueError('Candidacy is outside scope or its office identity changed: ' + repr(key))
        if before == after:
            raise ValueError('A change needs different before/after values; use hold for unchanged findings')
        for record in [before, after]:
            if record is not None:
                errors = check(record, SCHEMA['$defs'][FIELDS[field]])
                if errors:
                    raise ValueError('\n'.join(errors))
        if after is not None:
            if after['url'] != source['url'] or after['checked_on'] != source['checked_on']:
                raise ValueError('Record URL/check date must match its actual source capture')
            if field == 'endorsements' and not after.get('verification'):
                raise ValueError('New recommendations require explicit provenance')
            if field == 'endorsements' and after.get('verification') == 'endorser_statement':
                if source.get('role') not in {'endorser', 'aggregator'} or norm(source['publisher']) != norm(after['endorser']):
                    raise ValueError('First-party recommendation requires a verified matching publisher')
            if field == 'endorsements' and after.get('verification') == 'campaign_claim':
                if source.get('role') != 'campaign' or source.get('candidate') != decision['candidate']:
                    raise ValueError('Campaign claim requires a matching campaign source')
            if field == 'gaza_evidence' and not after.get('date_method'):
                raise ValueError('New evidence requires date provenance')
        if before is not None and after is not None and before['checked_on'] > after['checked_on']:
            raise ValueError('Cannot replace newer research with an older observation')
        if before is not None and before['checked_on'] > source['checked_on']:
            raise ValueError('Cannot remove or replace newer research with an older source check')
        target = before if before is not None else after
        collision = key, field, record_key(field, target)
        if collision in changed_keys:
            raise ValueError('Multiple changes to one observation in a review')
        changed_keys.add(collision)
        records = people[key].get(field, [])
        # Exact post-state recognition makes a rerun a no-op, including removals.
        if after is not None and records.count(after) == 1 and (before is None or before not in records):
            counts['unchanged'] += 1
            continue
        if before is not None and after is None and not any(record_key(field, r) == record_key(field, before) for r in records):
            counts['unchanged'] += 1
            continue
        if before is not None and records.count(before) != 1:
            raise ValueError('Stale before value; review the current record: ' + repr(key))
        if after is not None and any(r != before and record_key(field, r) == record_key(field, after) for r in records):
            raise ValueError('Conflicting existing observation; use an explicit replacement')
        if before is None:
            records = [*records, deepcopy(after)]
            counts['added'] += 1
        else:
            index = records.index(before)
            records = records[:index] + ([deepcopy(after)] if after is not None else []) + records[index + 1:]
            counts['replaced' if after is not None else 'removed'] += 1
        if records:
            people[key][field] = records
        else:
            people[key].pop(field, None)
    for field in FIELDS:
        result['coverage']['printed_candidates_with_' + field] = sum(bool(c.get(field)) for c in people.values())
    reviews = [*prior_reviews, review]
    if validate:
        from check_evidence import check_evidence
        from check_published_endorsements import check_endorsements
        errors = check(result, SCHEMA) + check_evidence(result) + check_endorsements(result, reviews=reviews)
        if errors:
            raise ValueError('\n'.join(errors[:30]))
    return result, {'review_id': review['id'], 'counts': dict(counts), 'counties': selection['requested_counties'],
                    'shared_contests_updated_once': sorted({d['position_id'] for d in review['decisions'] if d['action'] == 'change' and len(selected[d['position_id']]['counties']) > 1}),
                    'dataset_changed': result != data}


def draft(data, capture, review_id, reviewed_on, counties=None, scope='current', aliases=None):
    # Reuse the existing CAIR parser; labels and cross-election annotations are
    # carried into held observations, never converted into recommendations here.
    if capture.get('source_url') == 'https://cairactionguide.org/explore' and 'capture_sha256' in capture:
        capture = {'sources': {'cair': {'url': capture['source_url'], 'publisher': 'CAIR Action', 'role': 'endorser',
                                      'checked_on': capture['reviewed_on'], 'content_sha256': capture['capture_sha256'],
                                      'retrieval': capture['retrieval']}},
                   'cards': [{'id': card['id'], 'source_key': 'cair', 'name': card['name'], 'office_context': card['office'],
                              'label': card['level'], 'annotations': card['annotations'], 'phase': 'unspecified'} for card in capture['cards']]}
    selected = select_scope(data, counties, scope)
    people = candidates_from_data({**data, 'positions': selected['positions']})
    positions = {p['id']: p for p in selected['positions']}
    names = {}
    for candidate in people.values():
        for name in {norm(n) for n in [candidate['name'], *(aliases or {}).get(candidate['id'], [])]}:
            names.setdefault(name, []).append(candidate)
    decisions = []
    for card in capture['cards']:
        matches = [c for c in names.get(norm(card['name']), []) if office_matches(c, card['office_context'])]
        decisions.append({'id': card['id'], 'action': 'hold', 'source_key': card['source_key'],
                          'reason': 'Manual source, identity, election phase and relationship review required.',
                          'source_observation': card,
                          'suggested_matches': [{'position_id': c['position_id'], 'candidate': c['name'], 'identity': identity(positions[c['position_id']])} for c in matches]})
    return {'version': 1, 'id': review_id, 'election_date': data['election']['date'], 'reviewed_on': reviewed_on,
            'counties': selected['requested_counties'], 'base_dataset_sha256': digest(dump(data)),
            'sources': capture['sources'], 'notes': {}, 'decisions': decisions}


def apply_file(dataset, review_path):
    """Validate first, then write the dataset and register an immutable review."""
    path = review_path.resolve()
    if not path.is_relative_to(ROOT / 'research/reviews'):
        raise ValueError('An applied review must be saved under research/reviews/ for version control')
    registry = json.loads(REGISTRY.read_text())
    reviews = load_reviews()
    review = json.loads(path.read_text())
    data = json.loads(dataset.read_text())
    if any(r['id'] == review['id'] for r in reviews):
        if not any((ROOT / e['path']).resolve() == path for e in registry['reviews']):
            raise ValueError('Review ID is already registered at a different path')
        errors = check_registered_reviews(data, reviews)
        if errors:
            raise ValueError('\n'.join(errors))
        return {'review_id': review['id'], 'already_applied': True, 'dataset_changed': False}
    result, report = prepare(data, review, reviews)
    if not any(d['action'] == 'change' for d in review['decisions']):
        raise ValueError('Nothing to apply; all observations remain held')
    registry['reviews'].append({'path': str(path.relative_to(ROOT)), 'sha256': file_sha(path)})
    old_dataset, old_registry = dataset.read_bytes(), REGISTRY.read_bytes()
    try:
        atomic_json(dataset, result)
        atomic_json(REGISTRY, registry)
    except BaseException:
        dataset.write_bytes(old_dataset)
        REGISTRY.write_bytes(old_registry)
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DATA)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('draft')
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--id', required=True)
    p.add_argument('--reviewed-on', required=True)
    p.add_argument('--aliases', type=Path)
    p.add_argument('--output', type=Path, required=True)
    add_scope_arguments(p)
    p = sub.add_parser('preview')
    p.add_argument('review', type=Path)
    p.add_argument('--output', type=Path, help='Optional proposed dataset; cannot overwrite maintained inputs')
    p = sub.add_parser('apply')
    p.add_argument('review', type=Path)
    args = parser.parse_args()
    data = json.loads(args.dataset.read_text())
    if args.command == 'apply':
        if args.dataset.resolve() != DATA.resolve():
            parser.error('Apply uses the canonical dataset; use preview for another dataset')
        lock = ROOT / '.research/publication.lock'
        lock.parent.mkdir(exist_ok=True)
        with lock.open('x'):
            try:
                report = apply_file(args.dataset, args.review)
            finally:
                lock.unlink()
    else:
        if args.output and (args.output.resolve() in {args.dataset.resolve(), REGISTRY.resolve(), (ROOT / 'elections.schema.json').resolve(), (ROOT / 'index.html').resolve(), (ROOT / 'ballot.html').resolve()} or (args.command == 'preview' and args.output.resolve() == args.review.resolve())):
            parser.error('Output cannot overwrite a maintained input')
        if args.command == 'draft':
            if args.output.exists():
                parser.error('Draft output already exists; preserve existing review decisions')
            result = draft(data, json.loads(args.capture.read_text()), args.id, args.reviewed_on, args.county, args.scope, json.loads(args.aliases.read_text()) if args.aliases else None)
            report = {'held_observations': len(result['decisions']), 'output': str(args.output)}
        else:
            result, report = prepare(data, json.loads(args.review.read_text()))
        if args.output:
            atomic_json(args.output, result)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
