"""Source-date ordering and explicit tracker alignment; no political inference."""
import calendar
from datetime import date
import json
import re

CUTOFF = '2023-12-01'
ALIGNMENT = {'positive': 'aligned', 'negative': 'not_aligned', 'neutral': 'neutral', 'unclassified': 'unknown'}
MONTHS = {name.lower(): i for i, name in enumerate(
    ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'), 1)}


def action_date(metadata):
    label = str(metadata.get('date') or metadata.get('date_label') or '').strip()
    unknown = {'start': None, 'end': None, 'precision': 'unknown'}
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', label):
            exact = date.fromisoformat(label).isoformat()
            return {'start': exact, 'end': exact, 'precision': 'day'}
        period = re.fullmatch(r'(\d{4})\s*[-–—]\s*(\d{4})', label)
        if period:
            first, last = map(int, period.groups())
            if first > last:
                return unknown
            return {'start': date(first, 1, 1).isoformat(), 'end': date(last, 12, 31).isoformat(), 'precision': 'period'}
        month = re.fullmatch(r'(\d{4})-(\d{2})', label)
        if month:
            year, number = map(int, month.groups())
            return {'start': date(year, number, 1).isoformat(),
                    'end': date(year, number, calendar.monthrange(year, number)[1]).isoformat(), 'precision': 'month'}
        if re.fullmatch(r'\d{4}', label):
            year = int(label)
            return {'start': date(year, 1, 1).isoformat(), 'end': date(year, 12, 31).isoformat(), 'precision': 'year'}
        named = re.fullmatch(r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})', label)
        if named and named[1].lower() in MONTHS:
            exact = date(int(named[3]), MONTHS[named[1].lower()], int(named[2])).isoformat()
            return {'start': exact, 'end': exact, 'precision': 'day'}
    except (ValueError, OverflowError):
        pass
    return unknown


def order_key(metadata):
    parsed = action_date(metadata)
    # Period-only entries cannot interleave with actual action dates as if
    # December 31 of a Congress's final year were a real vote timestamp.
    return (parsed['precision'] == 'day', parsed['start'] or '')


def jev_actions(candidate, data):
    registry = (data.get('gaza_voting') or {}).get('actions', {})
    rows = []
    for record in candidate.get('gaza_voting_records') or []:
        for item in record.get('actions', []):
            metadata = registry.get(item.get('action_id'), {})
            parsed = action_date(metadata)
            # A range spanning the cutoff, unknown date, or year-only 2023 does
            # not establish that this action occurred after the cutoff.
            if not parsed['start'] or parsed['start'] < CUTOFF:
                continue
            assessment = item.get('assessment')
            assessment = assessment if assessment in ALIGNMENT else 'unclassified'
            kind = metadata.get('kind', item.get('kind', ''))
            row = {'title': metadata.get('title', item.get('title', '')),
                   'kind': 'vote' if kind == 'roll_call_vote' else kind,
                   'date': metadata.get('date') or metadata.get('date_label'),
                   'response': item.get('value'), 'alignment': ALIGNMENT[assessment]}
            if item.get('note'):
                row['note'] = item['note']
            rows.append((order_key(metadata), row, metadata.get('source_url')))
    seen, result = set(), []
    for _, row, url in sorted(rows, key=lambda pair: pair[0], reverse=True):
        # Collapse only identical statements about the same linked action.
        # Different titles, responses, alignment or qualifications stay distinct.
        key = (url, json.dumps(row, sort_keys=True, ensure_ascii=False))
        if url and key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result
