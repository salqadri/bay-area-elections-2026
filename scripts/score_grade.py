"""Deterministic 0–5 score bands; each upper bound belongs to the lower grade."""
from copy import deepcopy
import json
import math
import re
from pathlib import Path

DEFAULT_MAPPING = json.loads((Path(__file__).resolve().parent.parent /
                              'research/gaza-grading/score-grade-mapping.json').read_text())


def validate_mapping(mapping):
    if not isinstance(mapping, dict) or 'upper_bounds' not in mapping or set(mapping) - {'upper_bounds', 'minimum_evidence_score', 'require_issue_observation'}:
        raise ValueError('Provide upper_bounds: five increasing numbers for F, E, D, C, B. A ends at 5.')
    bounds = mapping['upper_bounds']
    if (not isinstance(bounds, list) or len(bounds) != 5 or
            any(type(n) not in (int, float) or not math.isfinite(n) for n in bounds) or
            not all(a < b for a, b in zip([0] + bounds, bounds + [5]))):
        raise ValueError('Grade bounds must be five finite, strictly increasing numbers between 0 and 5.')
    if 'minimum_evidence_score' in mapping:
        minimum = mapping['minimum_evidence_score']
        if type(minimum) not in (int, float) or not math.isfinite(minimum) or not 0 <= minimum <= 1:
            raise ValueError('Minimum evidence score must be a finite number from 0 to 1.')
    if 'require_issue_observation' in mapping and type(mapping['require_issue_observation']) is not bool:
        raise ValueError('require_issue_observation must be boolean.')
    return deepcopy(mapping)


def score_grade(score, mapping=DEFAULT_MAPPING):
    bounds = validate_mapping(mapping)['upper_bounds']
    if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 5:
        return None
    return next(grade for grade, upper in zip('FEDCBA', bounds + [5]) if score <= upper)


# Identity and unrelated local platforms are not observations about this issue.
# Unknown nonempty fields are preserved conservatively; this is not a stance classifier.
IDENTITY_FIELDS = {'candidate', 'office', 'state', 'party', 'election_date', 'jurisdiction',
                   'office_category', 'government_level', 'district_or_seat', 'counties',
                   'election_type', 'partisan', 'incumbent', 'candidate_roster',
                   'part_of_muslim_community', 'community_alignment_context', 'campaign_platform_points'}
ISSUE_TERMS = r'gaza|palestin|israel|zionis|aipac|cease.?fire|genocide|divest|\bbds\b|ihra|antisemit|anti.semit|arms|foreign policy|middle east|military aid|unrwa|netanyahu'


def has_issue_observation(state):
    if not isinstance(state, dict):
        return True  # Missing historic inputs are not a new finding of silence.
    if state.get('part_of_muslim_community') is True:
        return True
    if any(value for key, value in state.items() if key not in IDENTITY_FIELDS):
        return True
    return bool(re.search(ISSUE_TERMS, json.dumps(state.get('campaign_platform_points', [])), re.I))


def row_grade(row, mapping=DEFAULT_MAPPING):
    question = (row.get('request') or {}).get('questions', {}).get('pro_palestine_score', {})
    answer = (row.get('response') or {}).get('answers', {}).get('pro_palestine_score', {})
    if (row.get('status') != 'complete' or question.get('type') != 'score' or
            not isinstance(question.get('criteria'), list) or len(question['criteria']) != 6 or
            answer.get('type') != 'score'):
        return None
    grade = score_grade(answer.get('score'), mapping)
    evidence_question = (row.get('request') or {}).get('questions', {}).get('evidence_score', {})
    evidence_answer = (row.get('response') or {}).get('answers', {}).get('evidence_score', {})
    evidence = evidence_answer.get('score')
    # Only the explicitly submitted 0–1 evidence question can suppress a grade.
    # Historic prompts without that question retain their original mapping.
    if (grade and evidence_question.get('type') == 'score' and
            isinstance(evidence_question.get('criteria'), list) and len(evidence_question['criteria']) == 2 and
            evidence_answer.get('type') == 'score' and type(evidence) in (int, float) and
            math.isfinite(evidence) and 0 <= evidence < mapping.get('minimum_evidence_score', .10)):
        return 'N/A'
    if grade and mapping.get('require_issue_observation') and not has_issue_observation((row.get('request') or {}).get('state')):
        return 'N/A'
    return grade


def present_run(run, mapping):
    """Attach derived fields to a response/export, never alter saved model records."""
    result = {**run, 'score_grade_mapping': validate_mapping(mapping)}
    if 'rows' in run:
        result['rows'] = [{**row, 'pro_palestine_score_grade': row_grade(row, mapping)} for row in run['rows']]
    return result
