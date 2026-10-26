"""Deterministic 0–5 score bands; each upper bound belongs to the lower grade."""
from copy import deepcopy
import json
import math
from pathlib import Path

DEFAULT_MAPPING = json.loads((Path(__file__).resolve().parent.parent /
                              'research/gaza-grading/score-grade-mapping.json').read_text())


def validate_mapping(mapping):
    if not isinstance(mapping, dict) or set(mapping) != {'upper_bounds'}:
        raise ValueError('Provide upper_bounds: five increasing numbers for F, E, D, C, B. A ends at 5.')
    bounds = mapping['upper_bounds']
    if (not isinstance(bounds, list) or len(bounds) != 5 or
            any(type(n) not in (int, float) or not math.isfinite(n) for n in bounds) or
            not all(a < b for a, b in zip([0] + bounds, bounds + [5]))):
        raise ValueError('Grade bounds must be five finite, strictly increasing numbers between 0 and 5.')
    return deepcopy(mapping)


def score_grade(score, mapping=DEFAULT_MAPPING):
    bounds = validate_mapping(mapping)['upper_bounds']
    if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 5:
        return None
    return next(grade for grade, upper in zip('FEDCBA', bounds + [5]) if score <= upper)


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
            math.isfinite(evidence) and 0 <= evidence < .10):
        return 'Insufficient Info'
    return grade


def present_run(run, mapping):
    """Attach derived fields to a response/export, never alter saved model records."""
    result = {**run, 'score_grade_mapping': validate_mapping(mapping)}
    if 'rows' in run:
        result['rows'] = [{**row, 'pro_palestine_score_grade': row_grade(row, mapping)} for row in run['rows']]
    return result
