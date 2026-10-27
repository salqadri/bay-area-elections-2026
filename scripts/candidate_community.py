"""Explicit candidate-community observations. Missing means unknown, never false."""
import json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent.parent / 'research/candidate-community/observations.json'
COMMUNITY_CONTEXT = ('Owner-confirmed membership in the pro-Palestine Muslim community, not religious identity alone. '
                     'This is affirmative evidence of general pro-Palestine alignment under this guide. '
                     'It does not establish every specific policy position; false or absent is not an adverse stance.')


def load_observations(path=REGISTRY):
    document = json.loads(Path(path).read_text())
    if document.get('format') != 'candidate-community-observations/v1':
        raise ValueError('Unknown candidate community observation format')
    records = {}
    for row in document['observations']:
        key = (row['position_id'], row['candidate'])
        if key in records or type(row.get('part_of_muslim_community')) is not bool:
            raise ValueError('Duplicate candidacy or nonboolean community observation')
        if row.get('basis') != 'owner_confirmation':
            raise ValueError('Community membership requires an owner confirmation; public religion alone is not community membership')
        records[key] = row
    return records


def community_state(position, candidate, observations=None):
    records = load_observations() if observations is None else observations
    observation = records.get((position['id'], candidate['name']))
    if observation and any(observation.get(k) != position.get(k) for k in
                           ('office', 'jurisdiction', 'district_or_seat') if k in observation):
        raise ValueError('Community observation office identity changed; review before reuse')
    if not observation:
        return {}
    value = observation['part_of_muslim_community']
    return {'part_of_muslim_community': value, **({'community_alignment_context': COMMUNITY_CONTEXT} if value else {})}


def check_observations(data, path=REGISTRY):
    records = load_observations(path)
    people = {(p['id'], c['name']): (p, c) for p in data['positions'] if p.get('ballot_status') != 'excluded'
              for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates')
              for c in p.get(roster) or []}
    errors = []
    for key, record in records.items():
        if key not in people:
            errors.append('Community observation has no current candidacy: ' + repr(key))
            continue
        try:
            community_state(*people[key], observations=records)
        except ValueError as error:
            errors.append(str(error) + ': ' + repr(key))
    return errors
