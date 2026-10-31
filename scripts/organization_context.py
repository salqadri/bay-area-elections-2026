"""Sourced organization context for newly generated model states; no grading or network calls.

Committee identity uses provider-specific IDs. Exact normalized aliases are only for
endorsement names and explicit prose mentions, never a substitute for a committee ID.
"""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata

REGISTRY = Path(__file__).resolve().parent.parent / 'research/gaza-grading/organization-context-v1.json'
SPENDING_CONTEXT = (
    'Independent spending, not campaign contributions or proof of candidate policy. '
    'Organization context explains documented relevance; unmapped spenders have unestablished relevance '
    'and should not explain a Palestine assessment without other explicit evidence. '
    'Top 12 per direction plus all registered relevant spenders; not exhaustive totals. '
    'Funding links do not establish earmarking, control, or that every ad concerns Israel/Palestine.'
)
FUNDING_LINK_ASSESSMENT = (
    'Owner criterion: receiving UDP funding is sufficient to treat this organization as a negative '
    'funding signal for Palestinian justice; no candidate-specific earmarking proof is required. '
    'Keep the recorded support/opposition direction when assessing a candidate.'
)
# Owner-specified endorsement context, separate from the reviewed spending registry.
CJD_ALIASES = ('California Jewish Democrats', 'Democrats for Israel California',
               'Democrats for Israel CA', 'DFI California')
CJD_ENDORSEMENT_CONTEXT = (
    'California Jewish Democrats is the renamed Democrats for Israel California '
    '(same organization; dfi-ca.org).'
)


def name_key(name):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower())


@lru_cache(maxsize=1)
def registry():
    data = json.loads(REGISTRY.read_text())
    entities = {e['id']: e for e in data['entities']}
    if len(entities) != len(data['entities']):
        raise ValueError('Duplicate organization ID')
    indexes = {key: {} for key in ('aliases', 'fec_committee_ids', 'cal_access_ids')}
    for entity in entities.values():
        for source in entity['source_ids']:
            if source not in data['sources']:
                raise ValueError('Missing organization source: ' + source)
        for kind, index in indexes.items():
            for value in entity[kind]:
                key = name_key(value) if kind == 'aliases' else str(value)
                if key in index and index[key] != entity['id']:
                    raise ValueError('Ambiguous organization identity: ' + value)
                index[key] = entity['id']
    return data, entities, indexes


def add_context(state, entity_id, observed_name):
    data, entities, _ = registry()
    entity = entities[entity_id]
    context = state.setdefault('organization_context', {})
    row = context.setdefault(entity['name'], {
        'role': entity['role'], 'relevance': entity['relevance'],
        'sources': [data['sources'][s]['url'] for s in entity['source_ids']],
        **({'relationship': deepcopy(entity['relationship'])} if entity.get('relationship') else {}),
    })
    if entity.get('relationship', {}).get('type') in {'received_funding_from', 'funding_reported_by_donor'}:
        row['guide_assessment'] = FUNDING_LINK_ASSESSMENT
    # Bind original displayed spellings to the description without changing observations.
    if observed_name != entity['name']:
        aliases = row.setdefault('observed_as', [])
        if observed_name not in aliases:
            aliases.append(observed_name)


def add_spending(state, candidate, data, *, california=False):
    """Preserve direction and exact amounts; relevant rows cannot fall below the cap."""
    _, _, indexes = registry()
    prefix = 'ca_' if california else ''
    items = (candidate.get(prefix + 'independent_expenditures') or {}).get('items', [])
    spenders = data.get(prefix + 'ie_spenders', {})
    ids = indexes['cal_access_ids' if california else 'fec_committee_ids']
    for direction, label in (('for', 'spenders_supporting'), ('against', 'spenders_opposing')):
        rows = []
        ordered = sorted((i for i in items if i['direction'] == direction),
                         key=lambda i: (-i['amount'], str(i['spender_id'])))
        for rank, item in enumerate(ordered):
            spender_id = str(item['spender_id'])
            entity_id = ids.get(spender_id)
            if rank >= 12 and not entity_id:
                continue
            name = spenders.get(spender_id, {}).get('name', spender_id)
            row = {'spender': name, 'amount_usd': item['amount']}
            if entity_id:
                add_context(state, entity_id, name)
                row['organization_context'] = registry()[1][entity_id]['name']
            else:
                row['relevance'] = 'unestablished'
            rows.append(row)
        if rows:
            state[prefix + label] = rows
            state['spending_context'] = SPENDING_CONTEXT


@lru_cache(maxsize=1)
def mention_pattern():
    """Whole explicit aliases, longest first; Track AIPAC must not also match AIPAC."""
    _, entities, _ = registry()
    aliases = {alias for e in entities.values() for alias in e['aliases']}
    return re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(a) for a in sorted(aliases, key=lambda a: (-len(a), a))) + r')(?!\w)', re.I)


def add_observation_context(state):
    _, _, indexes = registry()
    for observation in state.get('focused_endorsement_observations', []):
        name = observation['endorser']
        entity_id = indexes['aliases'].get(name_key(name))
        if entity_id:
            add_context(state, entity_id, name)
        elif not observation.get('historical') and name_key(name) in {name_key(alias) for alias in CJD_ALIASES}:
            state.setdefault('organization_context', {})['California Jewish Democrats'] = {
                'role': 'endorsement organization',
                'relevance': CJD_ENDORSEMENT_CONTEXT,
                'sources': ['https://www.dfi-ca.org/news/13476586'],
            }
    # Explicit mentions already in projected, date-reviewed Gaza evidence. Never
    # scan discarded historical funding, names of people, or all canonical prose.
    for text in state.get('gaza_evidence', []):
        for match in mention_pattern().finditer(text):
            name = match.group(0)
            add_context(state, indexes['aliases'][name_key(name)], name)
