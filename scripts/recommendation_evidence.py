"""Direction-preserving selection inputs; no scoring, ranking or provider calls.

An opposition record is evidence about a candidate, not support for that
candidate. This narrow gate covers the owner's existing recommendation sources;
opposition from an unrelated organization cannot acquire that meaning by name.
"""
import re

from grade_gaza import build_state, compact_endorsements
from organization_context import name_key

POLICY_VERSION = 'direction-aware-selection-v1'
OPPOSITION_SOURCES = {
    name_key(name) for name in (
        'CAIR Action', 'AROC Action', 'BAMC Action', 'Bay Area Muslim Council',
        'Vote for Peace', 'VoteForPeace', 'Track AIPAC',
        'Track AIPAC / Citizens Against AIPAC Corruption', 'Samir Laymoun',
        'USAMPAC',
    )
}
DIRECTIONAL = {'endorsed', 'preferred', 'supported', 'recommended', 'opposed'}
ISSUE = re.compile(r'gaza|palestin|israel|zionis|ihra|unrwa|ceasefire|divest', re.I)


def evidence_from_state(state):
    observations = compact_endorsements(state.get('focused_endorsement_observations') or [])
    current = [o for o in observations if not o.get('historical')
               and o.get('relation') in DIRECTIONAL
               and str(o.get('rating', '')).strip().lower() not in {'neutral', 'no endorsement'}]
    # Presence does not assign a favorable direction. Unrelated campaign
    # priorities and zero/unmapped spending do not establish an issue record.
    other = state.get('part_of_muslim_community') is True or any(state.get(field) for field in (
        'gaza_evidence', 'antisemitism_education_policy_evidence',
        'reviewed_gaza_platform_statement', 'reviewed_evidence_context',
    ))
    other = other or any(ISSUE.search(str(point)) for point in state.get('campaign_platform_points') or [])
    other = other or any('not graded' not in str(item).lower()
                         for item in state.get('official_uscpr_scorecard') or [])
    other = other or any(str(item.get('response', '')).lower() not in {
        'not elected', 'not voting', 'not applicable', 'unknown', ''
    } for item in state.get('congressional_gaza_actions') or [])
    other = other or any(item.get('organization_context') and item.get('amount_usd', 0) > 0
                         for field in ('spenders_supporting', 'spenders_opposing',
                                       'ca_spenders_supporting', 'ca_spenders_opposing')
                         for item in state.get(field) or [])
    only_opposition = bool(current) and all(
        o['relation'] == 'opposed' and name_key(o['endorser']) in OPPOSITION_SOURCES
        for o in current)
    return {'observations': observations, 'other_issue_evidence': bool(other),
            'opposition_only': only_opposition and not other}


def candidate_evidence(position, candidate, data):
    return evidence_from_state(build_state(position, candidate, data))
