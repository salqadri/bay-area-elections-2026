#!/usr/bin/env python3
"""Integrate draft_positions.json into the canonical dataset + schema (1.20 -> 1.21).

- schema: top-level const bump; counties minItems 1 -> 0 with updated description
  (out-of-scope-geography contests appear only when no county filter is set).
- codes.party: register every new ballot party label present in the draft.
- sources/notes: Wikipedia compilation pages, per-candidate FEC data pages, and
  dated provenance notes; all new positions are inserted as ballot_status
  'unverified' pending official-source reconciliation (next phase).
- FEC money: receipts + coverage + authorized committees from fec_money_cache.json
  (candidate-level /totals/, same method as refresh_fec_money.py).
- coverage: recomputed with check_data.py formulas.
Insertion keeps display order: Senate block after the last Federal record;
governor block immediately after CA2026-014 (Governor first among other state offices).
"""
import json, subprocess
from datetime import date

ROOT = '/workspace/bay-area-elections-2026'
DATASET = f'{ROOT}/2026-11-03_Bay_Area_Elections.json'
SCHEMA = f'{ROOT}/elections.schema.json'
TODAY = '2026-10-17'  # America/Los_Angeles date of the money retrieval

data = json.loads(open(DATASET).read())
schema = json.loads(open(SCHEMA).read())
draft = json.load(open(f'{ROOT}/.research/federal-2026/draft_positions.json'))
money = json.load(open(f'{ROOT}/.research/federal-2026/fec_money_cache.json'))

assert data['schema_version'] == '1.20', 'expected 1.20 baseline'
existing_ids = {p['id'] for p in data['positions']}
assert not (existing_ids & {p['id'] for p in draft}), 'ID collision'

# ---------- schema 1.21 ----------
schema['properties']['schema_version']['const'] = '1.21'
cd = schema['$defs']['position']['properties']['counties']
cd['minItems'] = 0
cd['description'] = ("Names of in-scope counties whose residents may vote in this contest. Each must match an "
                     "election.counties_in_scope name. This is not necessarily every county intersected by the "
                     "jurisdiction. District residency still applies. An empty array marks a researched contest "
                     "whose electorate lies entirely outside the covered counties (nationwide federal and "
                     "out-of-state statewide races); such contests appear only when no county filter is selected.")
# OCD division IDs were California-only while coverage was Bay Area; nationwide races need any US state.
ocd = schema['$defs']['ocdDivisionId']
assert ocd['pattern'].startswith('^ocd-division/country:us/state:ca'), 'unexpected OCD pattern baseline'
ocd['pattern'] = '^ocd-division/country:us/state:[a-z]{2}(?:/[^\\s/]+:[^\\s/]+)*$'
ocd['description'] = ("Open Civic Data geographic division identifier for any US state. This identifies an "
                      "electorate or jurisdiction, not a unique office or candidate. A syntactically valid ID is "
                      "not proof that an API recognizes it or that its boundaries match this election.")

# ---------- party registry ----------
NEW_PARTY = {
 "I": "Independent or unaffiliated", "L": "Libertarian Party",
 "C": "Constitution Party", "DFL": "Minnesota Democratic–Farmer–Labor Party",
 "LMN": "Legal Marijuana Now Party", "NLP": "Natural Law Party",
 "PSL": "Party for Socialism and Liberation", "SWP": "Socialist Workers Party",
 "WCP": "Working Class Party", "UCP": "United Citizens Party",
 "AFP": "America First Party (Nebraska)", "AVP": "Approval Voting Party (Colorado)",
 "FWD": "Forward Party", "UP": "Unity Party of America",
 "AZIP": "Arizona's Independent Party", "GMPJ": "Green Mountain Peace and Justice Party",
 "OPP": "Oregon Progressive Party", "PGP": "Pacific Green Party",
 "NWPP": "Nebraska Working People Party",
}
used = {c['party'] for p in draft for c in p['candidates'] if 'party' in c}
for code in sorted(used):
    assert code in NEW_PARTY or code in data['codes']['party'], f'unregistered new party code {code}'
    if code in NEW_PARTY:
        data['codes']['party'].setdefault(code, NEW_PARTY[code])

# ---------- sources & notes ----------
src = data['sources']; notes = data['notes']
next_s = max(int(k[1:]) for k in src) + 1
def add_source(url, title):
    global next_s
    key = f'S{next_s:04d}'; next_s += 1
    src[key] = {'url': url, 'title': title}
    return key

S_WIKI_SENATE = add_source('https://en.wikipedia.org/wiki/2026_United_States_Senate_elections',
    'Wikipedia: 2026 United States Senate elections — race summary tables (retrieved October 18, 2026; each row cites state election-office sources)')
S_WIKI_GOV = add_source('https://en.wikipedia.org/wiki/2026_United_States_gubernatorial_elections',
    'Wikipedia: 2026 United States gubernatorial elections — race summary tables (retrieved October 18, 2026; each row cites state election-office sources)')

notes['N903'] = ("Nationwide federal and out-of-state statewide roster compiled October 18, 2026 from the cited "
                 "Wikipedia race-summary tables, which aggregate certified candidate lists published by each state's "
                 "election office. Ballot status is deliberately unverified until this inventory is reconciled "
                 "against those official state sources; printed names and party labels follow the compilation.")
notes['N904'] = ("2026-cycle FEC receipts retrieved October 17, 2026 from candidate-level totals (aggregating all "
                 "authorized committees), the same method as the existing federal finance layer. Coverage periods "
                 "vary by filer; amounts are dated snapshots, not a live feed.")
notes['N905'] = ("The FEC published no 2026-cycle total-receipts summary for this candidate's filings at the "
                 "October 17, 2026 retrieval (no authorized committee reported receipts, or none was found). "
                 "Unknown is not zero; a later filing may add a total.")
notes['N906'] = ("The FEC totals response reported coverage beginning before the nominal 2025–2026 cycle; the "
                 "source period and amount are preserved as published, not relabelled as a cycle subtotal.")
notes['N907'] = ("No FEC candidate filing was found for this printed federal candidacy at the October 17, 2026 "
                 "check (many minor-party candidates do not file). Absence of an FEC record is not absence from "
                 "the ballot and does not imply zero fundraising outside the federal reporting system.")

# ---------- positions ----------
def clean_candidate(c, wiki_source):
    out = {'name': c['name']}
    if 'party' in c: out['party'] = c['party']
    if c.get('incumbent'): out['incumbent'] = True
    fid = c.pop('_fec_id', None); c.pop('_fec_status', None)
    if fid:
        totals_rows = money.get(fid, {}).get('totals') or []
        row = next((r for r in totals_rows if r.get('cycle') == 2026), None)
        fec = {'id': fid}
        receipts = (row or {}).get('receipts')
        if receipts is not None:
            start = str(row.get('coverage_start_date'))[:10]
            end = str(row.get('coverage_end_date'))[:10]
            committees = money[fid].get('committees') or []
            if committees and start <= end <= TODAY:
                fec.update(receipts=round(float(receipts), 2), **{'from': start, 'through': end},
                           committee_ids=sorted(committees))
                if int(start[:4]) < 2025:
                    fec['note_id'] = 'N906'
            else:
                fec.update(receipts=None, note_id='N905')
        else:
            fec.update(receipts=None, note_id='N905')
        fec['source_id'] = add_source(f'https://www.fec.gov/data/candidate/{fid}/',
                                      f'FEC candidate summary {fid} (2026 cycle)')
        out['fec'] = fec
    out['source_ids'] = [wiki_source]
    return out

senate, governor = [], []
for p in draft:
    is_fed = p['office_category'] == 'U.S. Senate'
    wiki = S_WIKI_SENATE if is_fed else S_WIKI_GOV
    refs = p.pop('_wiki_refs', []); p.pop('_incumbent', None); p.pop('_status', None)
    roster = [clean_candidate(c, wiki) for c in p['candidates']]
    # Repo research contract: ballot appearance not yet established from official state sources ->
    # candidates stays null and the compiled roster is retained as provisional filings.
    p['candidates'] = None
    p['filed_candidates_not_confirmed_on_ballot'] = roster
    p['source_ids'] = [wiki]
    note_ids = ['N903'] + (['N904'] if any('fec' in c for c in roster) else []) \
        + (['N907'] if is_fed and any('fec' not in c for c in roster) else [])
    if note_ids: p['note_ids'] = note_ids
    (senate if is_fed else governor).append(p)

positions = data['positions']
last_fed = max(i for i, p in enumerate(positions) if p['government_level'] == 'Federal')
for offset, sp in enumerate(senate):
    positions.insert(last_fed + 1 + offset, sp)
gov_idx = next(i for i, p in enumerate(positions) if p['id'] == 'CA2026-014')
for offset, gp in enumerate(governor):
    positions.insert(gov_idx + 1 + offset, gp)

# ---------- coverage recompute (check_data.py formulas) ----------
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
old_cov = dict(data['coverage'])
data['coverage'].update(cov)

# finance snapshot: new Senate receipts fetched today; existing totals untouched.
data['finance']['checked_on'] = TODAY
data['schema_version'] = '1.21'
# publication_version intentionally NOT bumped until official-source reconciliation + build/gate pass.

open(DATASET, 'w').write(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
open(SCHEMA, 'w').write(json.dumps(schema, indent=1, ensure_ascii=False) + '\n')

# sidecar audit for the research record (committed later under research/)
audit = {'compiled_on': TODAY, 'positions_added': len(P and senate + governor),
         'senate_races': len(senate), 'governor_races': len(governor),
         'wiki_refs_by_state': {}, 'coverage_before': old_cov}
json.dump(audit, open(f'{ROOT}/.research/federal-2026/integration_audit.json', 'w'), indent=1)

print(json.dumps({'schema': data['schema_version'], 'positions_total': len(P),
                  'added_senate': len(senate), 'added_governor': len(governor),
                  'new_sources': next_s - (max(int(k[1:]) for k in src) - len(senate + governor)) ,
                  'coverage_delta': {k: (old_cov.get(k), v) for k, v in cov.items() if old_cov.get(k) != v}}, indent=1))
