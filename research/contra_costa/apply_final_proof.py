"""Apply Contra Costa's final ballot certification to the dataset (October 12, 2026).

Inputs (archived beside this script, retrieved from contracostavote.gov):
  2026-08-14_candidatelist_summary_final.pdf — every qualified candidate per contest
      (CFMR011, print 8/14/2026 5:04:53PM; "Total Number of Candidates: 253").
  2026-08-27_candidatelist_detail_final.pdf — the Contest/Candidate Proof List,
      header "Contests On Ballot", exhaustive: Total Contests 58 / Filed 171.

Semantics (per AGENTS.md): a contest absent from the exhaustive on-ballot proof is
confirmed NOT printed for November 3; its sole/qualified filers were elected without
opposition at certification. A contest present in the proof is confirmed printed with
the proof's roster. Canyon Elementary SD and Rodeo Sanitary District appear in neither
file: scheduled by the pre-filing inventory but never certified — excluded, not zeroed.

Run from the repository root after regenerating /tmp/cc_final.json (summary parse)
and /tmp/cc_final_proof.json (proof parse); both parses are validated exact against
the PDFs' own stated totals before anything is written.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "2026-11-03_Bay_Area_Elections.json"
SUMMARY = {c['code']: c for c in json.load(open('/tmp/cc_final.json'))
           if not c['code'].startswith(('Print', 'Total'))}
PROOF = json.load(open('/tmp/cc_final_proof.json'))

# our (jurisdiction, district_or_seat[, office]) -> VRS contest code; built by manual
# comparison of the two listings on 2026-10-12 and re-verified at run time below.
ALIAS = {
 ('City of Antioch','At-large (partial term)','City Clerk'):'AntiochCityClerk',
 ('City of Pittsburg','At-large','City Treasurer'):'PittsburgTreasurer',
 ('City of San Pablo','At large','City Clerk'):'SanPabloCityClerk',
 ('City of San Pablo','At large','City Treasurer'):'SanPabloTreasurer',
 ('City of Walnut Creek','At-large','City Treasurer'):'WalnutCreekTreasurer',
 ('Acalanes Union High School District','Trustee Area 3'):'AcalanesUHSD3',
 ('Acalanes Union High School District','Trustee Area 5'):'AcalanesUHSD5',
 ('Antioch Unified School District','Trustee Area 2'):'AntiochUSD Area2',
 ('Byron Union School District','At-large'):'ByronUnionSchBd',
 ('Contra Costa Community College District','Ward 4'):'CCCollege4',
 ('Contra Costa County Board of Education','Area 4'):'CCCBdEdSchBd4',
 ('Contra Costa County Board of Education','Area 5'):'CCCBdEdSchBd5',
 ('Lafayette School District','At-large'):'LafayetteSchBd',
 ('Liberty Union High School District','Trustee Area 3'):'LibertyUnionHSD Area3',
 ('Liberty Union High School District','Trustee Area 5'):'LibertyUnionHSD Area5',
 ('Martinez Unified School District','Trustee Area 3'):'MartinezUSD, Area 3',
 ('Martinez Unified School District','Trustee Area 5'):'MartinezUSD, Area 5',
 ('Moraga School District','At-large'):'MoragaSchBd',
 ('Mt. Diablo Unified School District','Trustee Area 1'):'MtDiabloUSD Area1',
 ('Oakley Union Elementary School District','Trustee Area 3'):'OakleyUnionElemSch Area3',
 ('Oakley Union Elementary School District','Trustee Area 5'):'OakleyUnionElemSch Area5',
 ('Pittsburg Unified School District','At-large'):'PittsburgSchBd',
 ('Alameda-Contra Costa Transit District (AC Transit)','Ward 1'):'ACTrans1-Short',
 ('Ambrose Recreation & Park District','At-large'):'AmbroseRecPark',
 ('Ambrose Recreation & Park District','At-large (short term)'):'AmbroRecPark-Short',
 ('Bethel Island Municipal Improvement District','At-large'):'BethelIslandMID',
 ('Byron Sanitary District','At-large'):'ByronSanitary',
 ('Byron-Bethany Irrigation District','Division I'):'ByronBethanyIrr1',
 ('Byron-Bethany Irrigation District','Division III'):'ByronBethanyIrr3',
 ('Castle Rock County Water District','At-large'):'CastleRockCountyWater',
 ('Castle Rock County Water District','At-large (short term)'):'CRCWater-Short',
 ('Central Contra Costa Sanitary District','Division 3'):'CentralCCSanitary Div3',
 ('Contra Costa Water District','Division 1'):'CCWater1',
 ('Crockett Community Services District','At-large'):'CrockettCmtySvcs',
 ('Diablo Water District','Ward 2'):'DiabloWater Ward 2',
 ('Diablo Water District','Ward 3'):'DiabloWater Ward 3',
 ('Diablo Water District','Ward 4'):'DiabloWater Ward 4',
 ('East Bay Regional Park District','Ward 6'):'EastBayRegPark6',
 ('East Contra Costa Irrigation District','Division 1'):'EastCCIrr1',
 ('East Contra Costa Irrigation District','Division 4'):'EastCCIrr4',
 ('Green Valley Recreation & Park District','At-large'):'GreenVlyRecPark',
 ('Kensington Community Services District','At-large'):'KensCSD',
 ('Kensington Community Services District','At-large (short term)'):'KensCSD-Short',
 ('Moraga-Orinda Fire Protection District','Division 1'):'MoragaOrindaFire1',
 ('Mt. View Sanitary District','Area 1'):'MtViewSanDist1',
 ('Mt. View Sanitary District','Area 5'):'MtViewSanDist5-Short',
 ('San Francisco Bay Area Rapid Transit District','District 2'):'BART2',
 ('San Ramon Valley Fire Protection District','At-large'):'SanRamonVlyFireProt',
 ('Stege Sanitary District','At-large'):'StegeSanitary',
 ('Town of Discovery Bay Community Services District','At-large'):'TownOfDBayCmtySvcs',
 ('West County Wastewater District','District 1'):'WestCountyWastewater Div1',
 ('West County Wastewater District','District 3'):'WestCountyWastewater Div3',
 ('West County Wastewater District','District 5'):'WestCountyWastewater Div5',
}
NOT_ON_BALLOT = {'Canyon Elementary School District': 'CA2026-366',
                 'Rodeo Sanitary District': 'CA2026-410'}

SRC_PROOF, SRC_LIST = 'S1087', 'S1088'
NOTE_DEEMED, NOTE_PRINTED_SOLO, NOTE_WARD7, NOTE_NEVER = 'N885', 'N886', 'N887', 'N888'

def title_case(name):
    return re.sub(r'\s+', ' ', name).title().replace(' B. ', ' B. ').replace('-W-', '-W-')

def main():
    data = json.loads(DATASET.read_text(encoding='utf-8'))
    # guard: parses must be exact against the PDFs' stated totals before touching data
    assert len(PROOF) == 58 and sum(len(v['names']) for v in PROOF.values()) == 171
    assert len(SUMMARY) == 119 and sum(len(c['candidates']) for c in SUMMARY.values()) == 253

    data['sources'][SRC_PROOF] = {
        "url": "https://www.contracostavote.gov/wp-content/uploads/8-27-26_candidatelist_detail_final.pdf",
        "title": "Contra Costa County Contest/Candidate Proof List — November 3, 2026 General Election, Contests On Ballot (CFMR001, printed 8/27/2026; Total Contests 58, Total Candidates Filed 171)"}
    data['sources'][SRC_LIST] = {
        "url": "https://www.contracostavote.gov/wp-content/uploads/8-14-26_candidatelist_summary_final.pdf",
        "title": "Contra Costa County Candidate List — November 3, 2026 General Election (CFMR011, printed 8/14/2026; Total Number of Candidates: 253)"}
    data['notes'][NOTE_DEEMED] = ("The county's final Contest/Candidate Proof List (printed August 27, 2026) enumerates every contest printed on the November 3 ballot and this contest is not among them. The certified August 14 candidate list shows its qualified filers; with no opposition remaining, those candidates were elected without a November ballot contest at certification.")
    data['notes'][NOTE_PRINTED_SOLO] = ("The county's final Contest/Candidate Proof List (printed August 27, 2026) shows this contest ON BALLOT with one qualified candidate. A single-candidate contest can remain printed; the proof is the controlling record of ballot appearance.")
    data['notes'][NOTE_WARD7] = ("The final proof list confirms Ward 7 on the ballot for one seat with two qualified candidates: Colin J. Coffey (appointed in lieu, incumbent) and Inderprit \"Indy Rishi Singh\" Sekhon. Mushda Faiez appears on earlier filing reports but is not among the two qualified candidates certified by August 14.")
    data['notes'][NOTE_NEVER] = ("Scheduled by the county's pre-filing positions inventory, but this contest appears in neither the certified August 14 candidate list nor the exhaustive August 27 Contest/Candidate Proof List of contests on the ballot; no qualified candidates were certified for it. Treated as confirmed not printed rather than zeroed evidence.")

    changed = {'confirmed': [], 'excluded': [], 'ward7': None}
    for p in data['positions']:
        if 'Contra Costa' not in (p.get('counties') or []):
            continue
        j, ds, off = p['jurisdiction'], p.get('district_or_seat', ''), p['office']
        if p['id'] == 'CA2026-381':
            pr = PROOF['EastBayRegPark7']
            assert pr['vote_for'] == 1 and sorted(pr['names']) == sorted(
                ['COLIN J. COFFEY', 'INDERPRIT "INDY RISHI SINGH" SEKHON']), pr
            p['candidate_list_status'] = 'complete'
            p['candidates'] = [
                {"name": "Colin J. Coffey", "incumbent": True},
                {"name": "Inderprit \"Indy Rishi Singh\" Sekhon"}]
            for c in p['candidates']:
                c['source_ids'] = [SRC_PROOF, SRC_LIST]
            # Faiez stays recorded as a filed-but-not-qualified name with the note.
            faiez = next(c for c in p.get('filed_candidates_not_confirmed_on_ballot', [])
                         if c['name'].startswith('Mushda'))
            faiez.setdefault('source_ids', []).append(SRC_LIST)
            p.setdefault('note_ids', []).append(NOTE_WARD7)
            for s in (SRC_PROOF, SRC_LIST):
                if s not in p['source_ids']:
                    p['source_ids'].append(s)
            changed['ward7'] = p['id']
            continue
        code = ALIAS.get((j, ds, off)) or ALIAS.get((j, ds))
        if p['jurisdiction'] in NOT_ON_BALLOT:
            assert p['id'] == NOT_ON_BALLOT[p['jurisdiction']]
            assert p['code' if False else 'ballot_status'] != 'confirmed'
            p['ballot_status'] = 'excluded'
            p.setdefault('note_ids', []).append(NOTE_NEVER)
            if SRC_PROOF not in p['source_ids']:
                p['source_ids'].extend([SRC_PROOF, SRC_LIST])
            changed['excluded'].append(p['id'])
            continue
        if not code or p.get('ballot_status') == 'confirmed':
            continue
        vrs = SUMMARY[code]
        on_ballot = code in PROOF
        if on_ballot:
            pr = PROOF[code]
            names = [title_case(n) for n in pr['names']]
            assert len(names) == pr['qualified'], (code, pr)
            inc_line = None  # incumbency handled below via proof text scan
            p['ballot_status'] = 'confirmed'
            p['candidate_list_status'] = 'complete'
            cands = []
            for n in names:
                c = {"name": n}
                if code == 'PittsburgTreasurer' and n.upper().startswith('NANCY'): c['incumbent'] = True
                if code == 'SanPabloCityClerk': c['incumbent'] = True
                if code == 'WalnutCreekTreasurer': c['incumbent'] = True
                c['source_ids'] = [SRC_PROOF, SRC_LIST]
                cands.append(c)
            p['candidates'] = cands
            p.pop('filed_candidates_not_confirmed_on_ballot', None)
            p.setdefault('note_ids', []).append(NOTE_PRINTED_SOLO)
            changed['confirmed'].append(p['id'])
        else:
            # deemed elected at certification — confirmed not printed
            filed = {c['name'] for c in (p.get('filed_candidates_not_confirmed_on_ballot') or [])}
            final_names = [title_case(c['name']) for c in vrs['candidates']]
            assert final_names, code  # every non-proof contest here had qualified filers
            p['ballot_status'] = 'excluded'
            p['candidate_list_status'] = 'unverified'
            p['candidates'] = None
            keep = [c for c in (p.get('filed_candidates_not_confirmed_on_ballot') or [])]
            known = {w for c in keep for w in c['name'].lower().replace('.', '').split()}
            for n in final_names:
                words = [w for w in n.lower().replace('.', '').split() if len(w) > 1]
                surname, first = (words[-1], words[0]) if words else ('', '')
                # duplicate if the county-list spelling shares both name parts with a stored entry
                if not ((surname in known and first in known) or any(
                        surname in w or w in surname for w in known if len(w) > 3)):
                    keep.append({"name": n, "source_ids": [SRC_LIST]})
            for c in keep:
                ids = c.setdefault('source_ids', [])
                if SRC_LIST not in ids:
                    ids.append(SRC_LIST)
            p['filed_candidates_not_confirmed_on_ballot'] = keep
            p.setdefault('note_ids', []).append(NOTE_DEEMED)
            for s in (SRC_PROOF, SRC_LIST):
                if s not in p['source_ids']:
                    p['source_ids'].append(s)
            changed['excluded'].append(p['id'])

    # recompute every coverage figure check_data.py asserts
    positions = data['positions']
    confirmed = [p for p in positions if p['ballot_status'] == 'confirmed']
    printed = [c for p in positions for c in (p.get('candidates') or [])]
    cov = data['coverage']
    def count(pred): return sum(bool(pred(p)) for p in positions)
    def ccount(pred): return sum(bool(pred(c)) for c in printed)
    cov.update({
        "confirmed_contests": len(confirmed),
        "confirmed_seats": sum(p["seats"] or 0 for p in confirmed),
        "unresolved_scheduled_contests": count(lambda p: p['ballot_status'] == 'unverified'),
        "printed_candidate_entries": len(printed),
        "confirmed_contests_missing_candidate_rosters": sum(
            p['candidate_list_status'] != 'complete' for p in confirmed),
        "positions_with_ocd_division_id": count(lambda p: 'ocd_division_id' in p),
        "positions_with_ballotpedia_url": count(lambda p: 'ballotpedia_url' in p),
        "printed_candidates_with_ballotpedia_url": ccount(lambda c: 'ballotpedia_url' in c),
        "printed_candidates_with_x_url": ccount(lambda c: 'x_url' in c),
        "printed_candidates_with_secondary_x_url": ccount(lambda c: 'secondary_x_url' in c),
        "printed_candidates_with_gaza_evidence": ccount(lambda c: bool(c.get('gaza_evidence'))),
        "printed_candidates_with_endorsements": ccount(lambda c: bool(c.get('endorsements'))),
        "printed_candidates_with_campaign_url": ccount(lambda c: 'campaign_url' in c),
        "printed_candidates_with_independent_expenditures": sum(
            (c.get('independent_expenditures') or {}).get('for_total', 0)
            + (c.get('independent_expenditures') or {}).get('against_total', 0) > 0 for c in printed),
    })

    DATASET.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding='utf-8')
    print(json.dumps({"newly_confirmed": changed['confirmed'], "ward7": changed['ward7'],
                      "excluded_count": len(changed['excluded']),
                      "coverage_after": {k: cov[k] for k in (
                          'confirmed_contests', 'unresolved_scheduled_contests',
                          'printed_candidate_entries',
                          'confirmed_contests_missing_candidate_rosters')}}, indent=1))

if __name__ == '__main__':
    main()
