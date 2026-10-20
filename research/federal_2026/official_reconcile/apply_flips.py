#!/usr/bin/env python3
"""Apply official-source reconciliation flips to the dataset (wave 1).

Reads adjudication.json. Two tiers, per the research contract ("flip as evidence
allows"):

FULL   — every compiled name is an accepted candidate row AND the extras scan
         found no additional active candidates: ballot_status confirmed,
         candidate_list_status complete, roster moved from
         filed_candidates_not_confirmed_on_ballot into candidates.
BALLOT — all names accepted but the official list shows extra active names
         (compiled roster incomplete): ballot_status confirmed only; printed
         roster stays null and filings remain provisional with an updated note.

Every flip replaces contest note N903 ("deliberately unverified") with a dated
official-source note, registers the capture as a source, recomputes coverage
with check_data.py formulas, bumps publication_version. Idempotent: contests
already confirmed are skipped. Review verdicts BEFORE running with --dry-run.
"""
import json, re, sys
from datetime import date

ROOT = '/workspace/bay-area-elections-2026'
DATASET = f'{ROOT}/2026-11-03_Bay_Area_Elections.json'
HERE = f'{ROOT}/research/federal_2026/official_reconcile'
CHECKED_ON = '2026-10-20'

WITHDRAWN = re.compile(r'\bWITHDRAWN\b|\(WI\)|WRITE[- ]?IN', re.I)

def main():
    dry = '--dry-run' in sys.argv
    adj = json.load(open(f'{HERE}/adjudication.json'))
    data = json.load(open(DATASET))
    pos = {p['id']: p for p in data['positions']}
    src, notes = data['sources'], data['notes']
    next_s = max(int(k[1:]) for k in src) + 1
    next_n = max(int(k[1:]) for k in notes) + 1

    def add_source(url, title):
        nonlocal next_s
        key = f'S{next_s:04d}'; next_s += 1
        src[key] = {'url': url, 'title': title}
        return key

    full_flips, ballot_flips, skipped = [], [], []
    for pid, r in sorted(adj.items()):
        p = pos[pid]
        if p['ballot_status'] == 'confirmed':
            # Upgrade path: a later FULL adjudication (e.g. Ballotpedia+Jev pass)
            # can complete a roster that an earlier BALLOT-tier flip left provisional.
            if p.get('candidate_list_status') == 'complete' or not r.get('mechanical_all_accepted'):
                skipped.append((pid, 'already confirmed')); continue
        mechanical = bool(r.get('mechanical_all_accepted'))
        # A documented election-context note (e.g. certified list dated after the
        # nomination deadline) satisfies the general-election-marker requirement.
        marker_ok = r.get('election_marker') or (mechanical and r.get('override_election_context'))
        if not (((r.get('all_accepted') or mechanical) and marker_ok
                 and r.get('block_chars', 0) > 200)):
            skipped.append((pid, f"not accepted (all={r.get('all_accepted')} marker={r.get('election_marker')})"))
            continue
        # extras are only a completeness problem when they look ACTIVE.
        # A mechanical row-extraction override may assert verified extras=[]
        # (exact office-row match) when the party-adjacency scan is noise-heavy.
        if 'mechanical_extras' in r:
            active_extras = [e for e in r['mechanical_extras'] if not WITHDRAWN.search(e)]
        else:
            active_extras = [e for e in r.get('extras_candidates', []) if not WITHDRAWN.search(e)]
        roster = p['filed_candidates_not_confirmed_on_ballot'] or []
        by_name = {c['name']: c for c in roster}
        ordered = [by_name[n] for n in r['roster'] if n in by_name]
        assert len(ordered) == len(r['roster']), f'{pid}: roster name vanished'
        bp = r.get('source_kind') == 'ballotpedia'
        skey = add_source(r['source_url'], r.get('title_override') or (
            f"Ballotpedia race page, November 3, 2026 general election slate "
            f"(retrieved {CHECKED_ON}; every published candidacy matched)" if bp else
            f"Official {r['state']} candidate list, November 3, 2026 general election "
            f"(retrieved {CHECKED_ON}; office block verified for every published candidacy)"))
        tier = 'FULL' if not active_extras else 'BALLOT'
        nkey = f'N{next_n:04d}'; next_n += 1
        if tier == 'FULL':
            wi = r.get('mechanical_write_ins') or []
            srcdesc = ("the cited Ballotpedia race page (cross-checked against contemporaneous reporting)"
                       if bp else f"the cited official {r['state']} source")
            notes[nkey] = (f"Ballot appearance and complete candidate roster verified {CHECKED_ON} against "
                           f"{srcdesc}; each published candidacy was confirmed as a "
                           f"candidate row for this race. Filed-but-not-certified names, if any, would remain "
                           f"recorded separately." + (f" The official list also identifies qualified write-in "
                           f"candidates ({', '.join(wi)}); they are not printed ballot candidates." if wi else ""))
            p['ballot_status'] = 'confirmed'
            p['candidate_list_status'] = 'complete'
            p['candidates'] = ordered
            # schema minItems=1: omit rather than store an empty array
            p.pop('filed_candidates_not_confirmed_on_ballot', None)
        else:
            notes[nkey] = (f"Ballot appearance verified {CHECKED_ON} against the cited official {r['state']} "
                           f"source, which lists every published candidacy for this race. The official list also "
                           f"shows additional active candidates not in the compiled roster ({len(active_extras)} "
                           f"name(s)), so the printed roster remains unverified and filings stay provisional.")
            p['ballot_status'] = 'confirmed'
        nids = [n for n in (p.get('note_ids') or []) if n != 'N903'
                and 'printed roster remains unverified' not in str(notes.get(n, ''))] + [nkey]
        p['note_ids'] = sorted(set(nids))
        if skey not in p['source_ids']:
            p['source_ids'].append(skey)
        (full_flips if tier == 'FULL' else ballot_flips).append(
            {'pid': pid, 'state': r['state'], 'office': r['office'], 'note': nkey, 'source': skey,
             'extras': active_extras[:8]})

    # coverage recompute (check_data.py formulas)
    P = data['positions']
    confirmed = [p for p in P if p['ballot_status'] == 'confirmed']
    printed = [c for p in P for c in (p.get('candidates') or [])]
    cov = {
        "confirmed_contests": len(confirmed),
        "confirmed_seats": sum(p['seats'] or 0 for p in confirmed),
        "unresolved_scheduled_contests": sum(p['ballot_status'] == 'unverified' for p in P),
        "printed_candidate_entries": len(printed),
        "confirmed_contests_missing_candidate_rosters": sum(p['candidate_list_status'] != 'complete' for p in confirmed),
        "positions_with_ocd_division_id": sum('ocd_division_id' in p for p in P),
        "positions_with_ballotpedia_url": sum('ballotpedia_url' in p for p in P),
        "printed_candidates_with_ballotpedia_url": sum('ballotpedia_url' in c for c in printed),
        "printed_candidates_with_x_url": sum('x_url' in c for c in printed),
        "printed_candidates_with_secondary_x_url": sum('secondary_x_url' in c for c in printed),
        "printed_candidates_with_gaza_evidence": sum(bool(c.get('gaza_evidence')) for c in printed),
        "printed_candidates_with_gaza_voting_records": sum(bool(c.get('gaza_voting_records')) for c in printed),
        "printed_candidates_with_uscpr_grade": sum(bool(c.get('uscpr_grade')) for c in printed),
        "printed_candidates_with_gaza_platform": sum(bool(c.get('gaza_platform')) for c in printed),
        "printed_candidates_with_platform_positions": sum(bool(c.get('platform_positions')) for c in printed),
        "printed_candidates_with_endorsements": sum(bool(c.get('endorsements')) for c in printed),
        "printed_candidates_with_campaign_url": sum('campaign_url' in c for c in printed),
        "printed_candidates_with_independent_expenditures": sum(
            (c.get('independent_expenditures') or {}).get('for_total', 0)
            + (c.get('independent_expenditures') or {}).get('against_total', 0) > 0 for c in printed),
    }
    old = dict(data['coverage'])
    data['coverage'].update(cov)

    today = date.today().isoformat()
    cur = data['election']['publication_version']
    data['election']['publication_version'] = (
        f"{today}.{int(cur.rsplit('.', 1)[1]) + 1}" if cur.startswith(today + '.') else today + '.1')

    print(json.dumps({'full': full_flips, 'ballot_only': ballot_flips,
                      'skipped_count': len(skipped), 'skipped': skipped[:8],
                      'coverage_delta': {k: (old.get(k), v) for k, v in cov.items() if old.get(k) != v},
                      'publication_version': data['election']['publication_version']}, indent=1))
    if not dry:
        open(DATASET, 'w').write(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
        print('WRITTEN' if (full_flips or ballot_flips) else 'nothing to write')

if __name__ == '__main__':
    main()
