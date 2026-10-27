"""Capture FEC intercommittee contribution leads for organization-context review.

No automatic classification, candidate edits or model calls. Requires FEC_API_KEY
or --fec-key-file; the output never contains the credential or authenticated URL.
"""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from grade_gaza import DATASET
from organization_context import registry


FIELDS = ('committee_id', 'recipient_committee_id', 'recipient_name', 'disbursement_date',
          'disbursement_amount', 'memoed_subtotal', 'transaction_id', 'sub_id', 'pdf_url')


def fetch_transfers(donor_id, start, end, key, get=None):
    """Walk Schedule B keyset pagination, retaining only positive, non-memo committee transfers."""
    def request(params):
        url = 'https://api.open.fec.gov/v1/schedules/schedule_b/?' + urllib.parse.urlencode({**params, 'api_key': key})
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'FEC HTTP {error.code}; capture aborted') from None
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError('FEC unavailable; capture aborted') from None
    get = get or request
    params = {'committee_id': donor_id, 'line_number': 'F3X-23', 'min_date': start,
              'max_date': end, 'per_page': 100, 'sort': 'disbursement_date'}
    rows, seen_rows, seen_cursors = [], set(), set()
    while True:
        page = get(params)
        for row in page['results']:
            if (row.get('committee_id') != donor_id or not row.get('recipient_committee_id') or
                    row.get('memoed_subtotal') is not False or row.get('disbursement_amount', 0) <= 0 or
                    not start <= (row.get('disbursement_date') or '')[:10] <= end):
                continue
            if row['sub_id'] not in seen_rows:
                seen_rows.add(row['sub_id'])
                rows.append({key: row.get(key) for key in FIELDS})
        if len(page['results']) < params['per_page']:
            break
        cursor = page['pagination'].get('last_indexes')
        signature = json.dumps(cursor, sort_keys=True)
        if not cursor or signature in seen_cursors:
            raise ValueError('Missing/repeated FEC cursor; refusing an incomplete capture')
        seen_cursors.add(signature)
        params = {**params, **cursor}
    return rows


def packet(rows, data, donor_id, start, end):
    known = registry()[2]['fec_committee_ids']
    recipients = {}
    for row in rows:
        cid = row['recipient_committee_id']
        recipient = recipients.setdefault(cid, {'name': row['recipient_name'],
            'tracked_spender': cid in data.get('ie_spenders', {}),
            'registered_context': known.get(cid), 'transfers': []})
        recipient['transfers'].append(row)
    return {'format': 'organization-funding-leads/v1', 'checked_on': date.today().isoformat(),
            'donor_committee_id': donor_id, 'period': {'start':start,'end':end},
            'status': 'held_for_source_and_jev_review',
            'limitation': 'Reported contribution leads, not net totals or candidate earmarking. Refunds, other schedules, intermediaries and non-committee recipients are not covered. Check recipient filings and identity before registering context; if only donor evidence is available, explicitly retain that attribution.',
            'recipients': recipients}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--donor', default='C00799031')
    ap.add_argument('--start', default='2024-01-01')
    ap.add_argument('--end', default=date.today().isoformat())
    ap.add_argument('--fec-key-file', type=Path)
    ap.add_argument('--dataset', type=Path, default=DATASET)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if date.fromisoformat(args.start) > date.fromisoformat(args.end):
        ap.error('Start must precede end')
    key = os.environ.get('FEC_API_KEY') or (args.fec_key_file.read_text().strip() if args.fec_key_file else '')
    if not key:
        ap.error('Set FEC_API_KEY or --fec-key-file')
    result = packet(fetch_transfers(args.donor,args.start,args.end,key), json.loads(args.dataset.read_text()),
                    args.donor,args.start,args.end)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'recipients':len(result['recipients']),
                      'tracked':sum(r['tracked_spender'] for r in result['recipients'].values()),
                      'output':str(args.output)}))
