#!/usr/bin/env python3
"""Attach the FEC records missed by the original single-token surname matcher.

build_positions.py compared only the first token of the FEC surname against the
last token of the printed name, so hyphenated/compound surnames (El-Sayed,
Hyde-Smith, Fetty Anderson) and a legal-name difference (Hinson -> 'ARENHOLZ,
ASHLEY HINSON') were left unmatched. The matcher is fixed; this script applies
the six newly matched candidacies to the published dataset:

- Abdul El-Sayed MI S6MI00418, Cindy Hyde-Smith MS S8MS00261,
  Ashley Hinson IA S6IA00314, Rachel Fetty Anderson WV S6WV00188 (real 2026
  filings with published totals), and the two Alaska Sullivan names whose
  reviewed overrides existed in the script but were never re-run into the draft.

Money fields come from fec_money_cache.json (candidate-level /totals/, same
method as integrate.py). Idempotent: a candidate that already has an fec block
is left untouched. Independent expenditures are attached separately by
scripts/fec_independent_expenditures.py run+attach, which keys off fec.id.
"""
import json

ROOT = '/workspace/bay-area-elections-2026'
DATASET = f'{ROOT}/2026-11-03_Bay_Area_Elections.json'
TODAY = '2026-10-19'  # America/Los_Angeles date of the money retrieval

FIXES = {  # (position_id, candidate name) -> FEC candidate ID
    ('US2026-002', 'Dan J. Sullivan'): 'S6AK00326',
    ('US2026-002', 'Dan S. Sullivan'): 'S4AK00214',
    ('US2026-010', 'Ashley Hinson'): 'S6IA00314',
    ('US2026-016', 'Abdul El-Sayed'): 'S6MI00418',
    ('US2026-018', 'Cindy Hyde-Smith'): 'S8MS00261',
    ('US2026-034', 'Rachel Fetty Anderson'): 'S6WV00188',
}

data = json.load(open(DATASET))
money = json.load(open(f'{ROOT}/.research/federal-2026/fec_money_cache.json'))
src = data['sources']
next_s = max(int(k[1:]) for k in src) + 1

def add_source(url, title):
    global next_s
    key = f'S{next_s:04d}'
    next_s += 1
    src[key] = {'url': url, 'title': title}
    return key

notes = data['notes']
next_n = max(int(k[1:]) for k in notes) + 1
N_FIX = f'N{next_n}'
notes[N_FIX] = (
    "This FEC candidate record was linked on October 19, 2026 after the initial "
    "nationwide name-matching pass missed hyphenated or compound surnames and one "
    "legal-name difference; receipts were retrieved that day from candidate-level "
    "totals (aggregating all authorized committees), the same method as note N904.")

by_id = {p['id']: p for p in data['positions']}
applied, skipped = [], []
for (pid, name), fid in FIXES.items():
    cand = next(c for c in by_id[pid]['filed_candidates_not_confirmed_on_ballot'] if c['name'] == name)
    if 'fec' in cand:
        skipped.append(f'{pid} {name}: already has fec')
        continue
    totals_rows = money.get(fid, {}).get('totals') or []
    row = next((r for r in totals_rows if r.get('cycle') == 2026), None)
    fec = {'id': fid}
    receipts = (row or {}).get('receipts')
    if receipts is not None:
        start = str(row.get('coverage_start_date'))[:10]
        end = str(row.get('coverage_end_date'))[:10]
        committees = money[fid].get('committees') or []
        assert committees and start <= end <= TODAY, f'{fid}: unexpected totals shape'
        fec.update(receipts=round(float(receipts), 2), **{'from': start, 'through': end},
                   committee_ids=sorted(committees))
        fec['note_id'] = N_FIX if int(start[:4]) >= 2025 else 'N906'
    else:
        fec.update(receipts=None, note_id='N905')
    fec['source_id'] = add_source(f'https://www.fec.gov/data/candidate/{fid}/',
                                  f'FEC candidate summary {fid} (2026 cycle)')
    cand['fec'] = fec
    nids = by_id[pid].setdefault('note_ids', [])
    for n in ('N904', N_FIX):
        if n not in nids:
            nids.append(n)
    applied.append(f"{pid} {name}: {fid} receipts={fec.get('receipts')}")

# N907 asserts at least one candidacy in the contest has no FEC filing; drop it
# from contests where every filed candidate now carries an FEC record.
dropped_907 = []
for pid in {pid for (pid, _) in FIXES}:
    p = by_id[pid]
    roster = p['filed_candidates_not_confirmed_on_ballot'] or []
    if all('fec' in c for c in roster) and 'N907' in (p.get('note_ids') or []):
        p['note_ids'].remove('N907')
        dropped_907.append(pid)

print(json.dumps({'applied': applied, 'skipped': skipped, 'n907_dropped': dropped_907}, indent=1))
json_path = json.dumps(data, indent=1, ensure_ascii=False) + '\n'
open(DATASET, 'w').write(json_path)
print('dataset written; new note', N_FIX)
