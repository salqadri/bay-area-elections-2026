"""Editorial source selection for prose, independent of saved Jev scoring."""
import re

SAMIR = re.compile(r'\bsamir(?:\s+laymoun)?\b|\blaymoun\b', re.I)
CLASSIFICATION_PADDING = re.compile(
    r'\b(?:individual|activist) opinion(?: source)?\b|\bowner[- ]requested\b|'
    r'\bindividual activist\b|\bindependent activist\b|'
    r'\b(?:rather than|separate from|distinct from)\b.{0,90}'
    r'\b(?:institutional endorsement|organizational endorsement|official BAMC Action positions)\b', re.I)
VOTER_RULES = (
    "Samir Laymoun source policy: omit his support, opposition and comments from voter prose "
    "when other relevant directional evidence exists. Do not retain his opinion anonymously "
    "as 'an activist' or 'a personal guide'. Exceptions: the Kamal Yassin race, or a candidate "
    "for whom his opinion is the only relevant directional evidence. Check the complete current "
    "research, not just an old summary. Where allowed, state the support/opposition or relevant "
    "comment briefly and accurately. Never relabel his opinion as BAMC Action's position or as "
    "the candidate's own policy. Never explain that he is an individual rather than an institution, "
    "an activist opinion source, owner-requested, or separate from official organizational positions. "
    "Those classifications belong in the audit, not the voter paragraph. Preserve genuinely material "
    "facts and qualifications; do not turn a tactical recommendation into agreement on policy."
)


def _directional(value):
    if isinstance(value, dict):
        if str(value.get('response', '')).lower() in ('not elected','not voting','not applicable','unknown'):
            return False
        if value.get('grade') in ('N/A','unknown','neutral'):
            return False
    text = str(value)
    if not text.strip() or SAMIR.search(text):
        return False
    # Absence of tracked money alone is not a stance or an endorsement.
    if re.search(r'no AIPAC-linked|no tracked pro-Israel|received \$0|spent for \$0', text, re.I):
        return False
    return True


def policy_for_state(state, position_id=None):
    observations = state.get('focused_endorsement_observations') or []
    present = any(SAMIR.search(str(o.get('endorser', ''))) for o in observations)
    if not present:
        return {'samir_allowed': False, 'reason': 'not_in_candidate_record'}
    if position_id == 'CA2026-174' or state.get('candidate') == 'Kamal Yassin':
        return {'samir_allowed': True, 'reason': 'kamal_yassin_race'}
    other = state.get('part_of_muslim_community') is True or state.get('relevant_funding_signal') is True
    for field in ('spenders_supporting','spenders_opposing','ca_spenders_supporting','ca_spenders_opposing'):
        if any(row.get('organization_context') and row.get('amount_usd',0) > 0 for row in state.get(field) or []):
            other = True
    for observation in observations:
        if (not SAMIR.search(str(observation.get('endorser', ''))) and
                observation.get('relation') in ('endorsed','preferred','supported','opposed','recommended') and
                str(observation.get('rating', '')).lower() not in ('neutral','no endorsement')):
            other = True
    for field in ('gaza_evidence','antisemitism_education_policy_evidence','reviewed_gaza_platform_statement',
                  'official_uscpr_scorecard','congressional_gaza_actions'):
        value = state.get(field)
        if value and any(_directional(item) for item in (value if isinstance(value, list) else [value])):
            other = True
    for point in state.get('campaign_platform_points') or []:
        if re.search(r'gaza|palestin|israel|zionis|ihra|unrwa|ceasefire', str(point), re.I) and _directional(point):
            other = True
    return {'samir_allowed': not other,
            'reason': 'other_relevant_evidence' if other else 'only_relevant_directional_evidence'}


def policy_for_candidate(position, candidate):
    from candidate_community import community_state
    from grade_gaza import focused_endorsements
    from organization_context import registry
    position = {'id': '', **position}
    state = {'candidate': candidate['name'], **community_state(position, candidate),
             'focused_endorsement_observations': focused_endorsements(position, candidate),
             'gaza_evidence': candidate.get('gaza_evidence') or [],
             'official_uscpr_scorecard': candidate.get('uscpr_grade'),
             'congressional_gaza_actions': candidate.get('gaza_voting_records') or []}
    platform = candidate.get('gaza_platform') or {}
    if platform.get('status') == 'statement_found':
        state['reviewed_gaza_platform_statement'] = platform.get('summary')
    points = candidate.get('platform_positions') or {}
    state['campaign_platform_points'] = points.get('points') or points.get('positions') or []
    indexes = registry()[2]
    state['relevant_funding_signal'] = any(
        item.get('amount',0) > 0 and str(item.get('spender_id')) in indexes[index]
        for prefix,index in (('','fec_committee_ids'),('ca_','cal_access_ids'))
        for item in (candidate.get(prefix+'independent_expenditures') or {}).get('items',[]))
    return policy_for_state(state, position.get('id'))


def prose_errors(text, policy):
    errors = []
    if SAMIR.search(text) and not policy.get('samir_allowed'):
        errors.append('Samir reference outside the permitted editorial exceptions')
    source_present = bool(SAMIR.search(text)) or policy.get('reason') in (
        'kamal_yassin_race','other_relevant_evidence','only_relevant_directional_evidence')
    if source_present and CLASSIFICATION_PADDING.search(text):
        errors.append('source-classification boilerplate in voter prose')
    return errors
