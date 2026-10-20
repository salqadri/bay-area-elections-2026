"""Compare a published inventory with a v2 FEC export, without network or writes to it.

Snapshot deltas can include intervening filings and FEC processing differences;
this comparison is not a measurement of duplicate spending alone.
"""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from fec_independent_expenditures import METHOD_VERSION, eligible


def cents(value):
    return Decimal(str(value))


def compare(data, export):
    if export['format'] != 'fec-independent-expenditures/v2' or export['method_version'] != METHOD_VERSION:
        raise ValueError('Expected current-method FEC export')
    if export['cycle'] != data['ie_finance']['cycle']:
        raise ValueError('Cycle mismatch')
    required = {cid for cid, _, _ in eligible(data, None)}
    if not required <= export['candidates'].keys():
        raise ValueError('Incomplete candidate coverage')
    results = []
    for position in data['positions']:
        if position.get('government_level') != 'Federal':
            continue
        for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot'):
            for candidate in position.get(roster) or []:
                cid = (candidate.get('fec') or {}).get('id')
                if not cid:
                    continue
                before = candidate['independent_expenditures']
                after = export['candidates'][cid]
                old = {(r['spender_id'], r['direction']): r['amount'] for r in before['items']}
                new = {(r['spender_id'], r['direction']): r['amount'] for r in after['items']}
                changes = [{'spender_id': k[0], 'direction': k[1],
                            'before': old.get(k), 'after': new.get(k),
                            'delta': float(cents(new.get(k, 0)) - cents(old.get(k, 0)))}
                           for k in sorted(old.keys() | new.keys()) if old.get(k) != new.get(k)]
                results.append({'candidate_id': cid, 'name': candidate['name'],
                                'position_id': position['id'], 'roster': roster,
                                'fetched_at': after['fetched_at'],
                                'before': {k: before[k] for k in ('for_total', 'against_total')},
                                'after': {k: after[k] for k in ('for_total', 'against_total')},
                                'spender_changes': changes})
    summary = {}
    for cohort, rows in [('all', results), ('printed', [r for r in results if r['roster'] == 'candidates']),
                         ('provisional', [r for r in results if r['roster'] != 'candidates'])]:
        summary[cohort] = {
            'candidacies': len(rows), 'amounts_changed': sum(bool(r['spender_changes']) for r in rows),
            'totals_changed': sum(r['before'] != r['after'] for r in rows),
            'before_with_activity': sum(any(r['before'].values()) for r in rows),
            'after_with_activity': sum(any(r['after'].values()) for r in rows),
            **{when: {key: float(sum((cents(r[when][key]) for r in rows), Decimal(0)))
                      for key in ('for_total', 'against_total')} for when in ('before', 'after')},
        }
    return {'format': 'fec-ie-comparison/v1', 'cycle': export['cycle'],
            'baseline_publication': data['election']['publication_version'],
            'baseline_checked_on': data['ie_finance']['checked_on'],
            'limitation': 'Snapshot deltas include methodology changes and any intervening filings/processing. '
                          'Totals across candidates are candidate-attributed amounts, not deduplicated national spending.',
            'summary': summary, 'candidates': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(json.loads(args.baseline.read_text()), json.loads(args.snapshot.read_text()))
    report['baseline_sha256'] = hashlib.sha256(args.baseline.read_bytes()).hexdigest()
    report['snapshot_sha256'] = hashlib.sha256(args.snapshot.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report['summary'], indent=1))


if __name__ == '__main__':
    main()
