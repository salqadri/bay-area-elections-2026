"""Conservative Jev projection of reviewed funding observations.

A report/check date never dates a donation. Unreviewed or changed financial
observations are held out, rather than converted into a finding of no funding.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / 'research/funding/jev-funding-policy-v1.json'
CUTOFF = '2024-01-01'


def signature(evidence):
    return hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def needs_review(evidence):
    if evidence.get('dimension') == 'aipac_funding':
        return True
    text = evidence.get('summary', '')
    # Catch mixed position/funding sentences filed under another dimension.
    return bool(re.search(r'\$[\d,]+.*(?:donat|contribut|receiv)|(?:donat|contribut|receiv).*\$[\d,]+', text, re.I))


def organization_receipt(receipt):
    """Known organizational receipt dated 2024+, excluding individual conduits."""
    from datetime import date
    value = (receipt.get('contribution_receipt_date') or '')[:10]
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return (value >= CUTOFF and receipt.get('entity_type') in {'COM', 'ORG'}
            and receipt.get('memoed_subtotal') is False
            and not re.search(r'earmark|conduit', receipt.get('memo_text') or '', re.I))


@lru_cache(maxsize=1)
def policy():
    return json.loads(POLICY.read_text())['observations']


def model_text(evidence, observations=None):
    if not needs_review(evidence):
        return f"{evidence['date']}: {evidence['summary']}"
    record = (policy() if observations is None else observations).get(evidence['id'], {})
    if record.get('evidence_sha256') != signature(evidence):
        return None
    # Only reviewed projections can enter new requests. Never use e.date as
    # a transaction date or slice a multi-year total by proportion.
    if record.get('disposition') == 'nonfinancial':
        return f"{evidence['date']}: {record.get('model_text') or evidence['summary']}"
    if record.get('disposition') != 'organization_since_2024':
        return None
    period = record.get('period', {})
    from datetime import date
    try:
        date.fromisoformat(period['start'])
        date.fromisoformat(period['end'])
    except (KeyError, ValueError, TypeError):
        return None
    if (not period.get('start') or not period.get('end') or
            period['start'] < CUTOFF or period['end'] < period['start'] or
            record.get('donor_type') != 'organization' or
            record.get('kind') not in {'contribution', 'independent_expenditure'} or
            not record.get('model_text')):
        return None
    return record['model_text']
