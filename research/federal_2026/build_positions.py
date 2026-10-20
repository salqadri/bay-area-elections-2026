#!/usr/bin/env python3
"""Build draft dataset positions for nationwide 2026 U.S. Senate + governor races
from wiki_inventory.json, matched against cached FEC Senate filers.

Draft records are inserted with ballot_status 'unverified' and a shared note:
Wikipedia race-summary tables (which cite state election-office pages) are the
compilation source; official certification reconciliation is the next phase.
California's governor race already exists in the dataset (CA2026-014); Guam is
out of scope. Territories excluded by owner decision.
"""
import json, re, unicodedata

STATE_OCD = {s: f"ocd-division/country:us/state:{ab}" for s, ab in {
 'Alabama':'al','Alaska':'ak','Arizona':'az','Arkansas':'ar','California':'ca','Colorado':'co',
 'Connecticut':'ct','Delaware':'de','Florida':'fl','Georgia':'ga','Hawaii':'hi','Idaho':'id',
 'Illinois':'il','Indiana':'in','Iowa':'ia','Kansas':'ks','Kentucky':'ky','Louisiana':'la',
 'Maine':'me','Maryland':'md','Massachusetts':'ma','Michigan':'mi','Minnesota':'mn',
 'Mississippi':'ms','Missouri':'mo','Montana':'mt','Nebraska':'ne','Nevada':'nv',
 'New Hampshire':'nh','New Jersey':'nj','New Mexico':'nm','New York':'ny',
 'North Carolina':'nc','North Dakota':'nd','Ohio':'oh','Oklahoma':'ok','Oregon':'or',
 'Pennsylvania':'pa','Rhode Island':'ri','South Carolina':'sc','South Dakota':'sd',
 'Tennessee':'tn','Texas':'tx','Utah':'ut','Vermont':'vt','Virginia':'va','Washington':'wa',
 'West Virginia':'wv','Wisconsin':'wi','Wyoming':'wy'}.items()}

STATE_ABBR = {s: v.split('state:')[-1].upper() for s, v in STATE_OCD.items()}
STATE_ABBR['Guam'] = 'GU'

PARTY_CODES = {  # raw wikitext party -> registry code
 'Democratic Party (US)':'D','Democratic Party (United States)':'D',
 'Republican Party (US)':'R','Republican Party (United States)':'R',
 'Minnesota Democratic–Farmer–Labor Party':'DFL',
 'Independent':'I','Unaffiliated':'I',
 'Libertarian Party (US)':'L','Libertarian Party (United States)':'L',
 'Constitution Party (US)':'C','Constitution Party (United States)':'C',
 'American Constitution Party (Colorado)':'C',
 'Green Party (US)':'G','Pacific Green Party':'PGP',
 'Legal Marijuana Now Party':'LMN','Natural Law Party':'NLP',
 'Party for Socialism and Liberation':'PSL',
 'Socialist Workers Party (United States)':'SWP',
 'Working Class Party':'WCP','United Citizens Party':'UCP',
 'America First Party (Nebraska)':'AFP','Approval Voting Party':'AVP',
 'Forward Party (United States)':'FWD','Unity Party of America':'UP',
 'Arizona Independent Party':'AZIP',
 'Green Mountain Peace and Justice Party':'GMPJ',
 'Oregon Progressive Party':'OPP','Nebraska Working People Party':'NWPP',
}

NEW_PARTY_REGISTRY = {
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

SUFFIXES = {'JR','SR','II','III','IV','V','DR','MR','MS','MRS','MD'}

# (state, printed name) -> FEC candidate ID. Reviewed one-by-one: legal-name or
# nickname differences where the public candidacy and FEC filing are unambiguous.
REVIEWED_OVERRIDES = {
 ('MN', 'Peggy Flanagan'): 'S6MN00440',   # FEC legal name "FLANAGAN, MARGARET"; DFL nominee for US Senate MN 2026
 ('AK', 'Dan J. Sullivan'): 'S6AK00326',  # challenger "SULLIVAN, DANIEL J", F2 2026-07-14, incumbent_challenge=C
 ('AK', 'Dan S. Sullivan'): 'S4AK00214',  # incumbent senator "SULLIVAN, DAN" (incumbent_challenge=I); only consistent assignment for the two printed names
 ('IA', 'Ashley Hinson'): 'S6IA00314',    # FEC legal name "ARENHOLZ, ASHLEY HINSON"; committee "ASHLEY FOR IOWA" P, F2 filed; US Senate IA 2026
}

def tokens(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'[^A-Za-z ]', ' ', s).upper()
    return [t for t in s.split() if len(t) > 1 and t not in SUFFIXES]

def surname_forms(wiki_tokens):
    """Normalized joined strings of the trailing 1..3 wiki name tokens. A hyphenated
    or compound FEC surname ('EL-SAYED', 'HYDE-SMITH', 'FETTY ANDERSON') tokenizes to
    several tokens on both sides; comparing only single first/last tokens missed real
    filers (El-Sayed, Hyde-Smith). Trailing sequences cover the case where a printed
    middle name is part of the FEC compound surname."""
    out = set()
    for n in (1, 2, 3):
        if len(wiki_tokens) >= n:
            out.add(''.join(wiki_tokens[-n:]))
    return out

def norm_name(s):
    """canonical (first, last) from either 'First Last' or FEC 'Last, First M' form."""
    if ',' in s:
        last_part, _, first_part = s.partition(',')
        lt = tokens(last_part); ft = tokens(first_part)
        first = ft[0] if ft else ''
        last = lt[0] if lt else ''
    else:
        t = tokens(s)
        first = t[0] if t else ''
        last = t[-1] if len(t) > 1 else ''
    return (first, last)

def fec_match(cand_name, state_abbr, party, fec_rows, is_incumbent=False):
    # reviewed overrides (identity established from public candidacy + FEC filing record)
    ov = REVIEWED_OVERRIDES.get((state_abbr, cand_name))
    if ov: return next(r for r in fec_rows if r['candidate_id'] == ov)
    if ',' in cand_name:  # wiki names are plain 'First Last'
        return None
    wt = tokens(cand_name)
    if not wt: return None
    wlast, wfirsts = wt[-1], set(wt[:-1])
    winits = {list(f)[0] for f in wfirsts if f}
    wsurnames = surname_forms(wt)
    best = []
    for r in fec_rows:
        if r.get('state') != state_abbr: continue
        rn = r['name']
        if ',' not in rn: continue
        last_part, _, first_part = rn.partition(',')
        lt = tokens(last_part); ft = set(tokens(first_part))
        # full FEC surname (hyphens/spaces dropped) must equal one of the wiki name's
        # trailing token sequences — single, hyphenated or compound surnames.
        if not lt or ''.join(lt) not in wsurnames: continue
        given_ok = bool(wfirsts & ft) or bool(winits & {list(f)[0] for f in ft})
        inc_ok = (is_incumbent and r['candidate_status'] == 'C'
                  and {'DEM': 'D', 'REP': 'R'}.get(r.get('party'), '?') == party)
        if not given_ok and not inc_ok: continue
        best.append((0 if given_ok else 1, r))
    if not best: return None
    # prefer exact given-name matches, then registered (C), party alignment, most recent F2
    def rank(tr):
        tier, r = tr
        p = {'DEM':'D','REP':'R'}.get(r.get('party'), '?')
        return (tier, r['candidate_status'] != 'C', p != party, r.get('last_f2_date') or '')
    best.sort(key=rank)
    return best[0][1]

def main():
    inv = json.load(open('wiki_inventory.json'))
    fec_rows = json.load(open('fec_senate_2026.json'))
    positions = []
    unmatched = []
    collisions = []
    ambiguous_incumbent = []
    n = 0
    for r in sorted(inv['senate'], key=lambda x: x['state']):
        n += 1
        pid = f"US2026-{n:03d}"
        st_abbr = STATE_ABBR[r['state']]
        cands = []
        for c in r['candidates']:
            code = PARTY_CODES.get(c['party_raw'])
            if code is None: raise SystemExit(f"unmapped party {c['party_raw']!r} ({c['name']}, {r['state']})")
            entry = {'name': c['name']}
            if code != 'NPP': entry['party'] = code
            inc_tokens = tokens(r['incumbent']) if r.get('incumbent') and ',' not in c['name'] else None
            is_inc = bool(inc_tokens) and inc_tokens[-1] == tokens(c['name'])[-1]
            m = fec_match(c['name'], st_abbr, code, fec_rows, is_incumbent=is_inc)
            if m: entry['_fec_id'] = m['candidate_id']; entry['_fec_status'] = m['candidate_status']
            else: unmatched.append((r['state'], c['name'], code))
            if inc_tokens and inc_tokens == tokens(c['name']):
                entry['_incumbent_candidate'] = True
            cands.append(entry)
        # collision guard: two different printed names mapped to one FEC ID -> hold for review
        by_fec = {}
        for e in cands:
            if '_fec_id' in e: by_fec.setdefault(e['_fec_id'], []).append(e)
        for fid, group in by_fec.items():
            if len(group) > 1:
                collisions.append((r['state'], fid, [e['name'] for e in group]))
                for e in group:
                    unmatched.append((r['state'], e['name'], 'COLLISION-' + fid))
                    del e['_fec_id']; del e['_fec_status']
        # incumbent flag only when exactly one printed name reduces to the incumbent's tokens
        inc_flags = [e for e in cands if e.pop('_incumbent_candidate', False)]
        if len(inc_flags) == 1:
            inc_flags[0]['incumbent'] = True
        elif len(inc_flags) > 1:
            ambiguous_incumbent.append((r['state'], r.get('incumbent'), [e['name'] for e in inc_flags]))
        pos = {
            'id': pid, 'counties': [], 'government_level': 'Federal',
            'office_category': 'U.S. Senate', 'jurisdiction': 'United States Senate',
            'office': 'United States Senator', 'district_or_seat': STATE_ABBR[r['state']] + ' — Statewide',
            'seats': 1,
            'term': 'Unexpired term ending January 3, 2029' if r['special'] else '6 years',
            'election_type': 'special' if r['special'] else 'general',
            'ballot_status': 'unverified', 'partisan': True,
            'ocd_division_id': STATE_OCD[r['state']], 'ocd_id_status': 'convention',
            'candidate_list_status': 'unverified',
            'candidates': cands,
            '_wiki_refs': r.get('refs', []), '_incumbent': r.get('incumbent'), '_status': r.get('status'),
        }
        positions.append(pos)
    for r in sorted(inv['governor'], key=lambda x: x['state']):
        if r['state'] == 'California': continue   # already CA2026-014 (owner scope)
        if r['state'] == 'Guam': continue         # territories excluded by owner decision
        n += 1
        pid = f"US2026-{n:03d}"
        cands = []
        for c in r['candidates']:
            code = PARTY_CODES.get(c['party_raw'])
            if code is None: raise SystemExit(f"unmapped party {c['party_raw']!r} ({c['name']}, {r['state']})")
            entry = {'name': c['name']}
            if code != 'NPP': entry['party'] = code
            if r.get('incumbent') and norm_name(r['incumbent']) == norm_name(c['name']):
                entry['incumbent'] = True
            cands.append(entry)
        pos = {
            'id': pid, 'counties': [], 'government_level': 'State',
            'office_category': 'Statewide executive', 'jurisdiction': f"State of {r['state']}",
            'office': 'Governor', 'district_or_seat': STATE_ABBR[r['state']] + ' — Statewide',
            'seats': 1, 'term': '4 years' if r['state'] not in ('New Hampshire','Vermont') else '2 years',
            'election_type': 'general',
            'ballot_status': 'unverified', 'partisan': True,
            'ocd_division_id': STATE_OCD[r['state']], 'ocd_id_status': 'convention',
            'candidate_list_status': 'unverified',
            'candidates': cands,
            '_wiki_refs': r.get('refs', []), '_incumbent': r.get('incumbent'), '_status': r.get('status'),
        }
        positions.append(pos)

    json.dump(positions, open('draft_positions.json', 'w'), indent=1)
    sen = [p for p in positions if p['office_category'] == 'U.S. Senate']
    gov = [p for p in positions if p['office'] == 'Governor']
    ncand = sum(len(p['candidates']) for p in positions)
    matched = sum(1 for p in sen for c in p['candidates'] if '_fec_id' in c)
    print(f"positions: {len(sen)} senate + {len(gov)} governor = {len(positions)}; candidates {ncand}")
    print(f"FEC-matched Senate candidates: {matched}/{sum(len(p['candidates']) for p in sen)}")
    print("UNMATCHED (no FEC filer found):")
    for s, name, code in unmatched: print(f"  {s} {name} ({code})")
    print("COLLISIONS held:")
    for c in collisions: print(' ', c)
    print("AMBIGUOUS INCUMBENT (flag withheld):")
    for a in ambiguous_incumbent: print(' ', a)

if __name__ == '__main__':
    main()
