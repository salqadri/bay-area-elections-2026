"""Apply Fresno County coverage to the dataset from the CFMR001 Contest/Candidate
Proof List (printed 10/12/2026), cross-checked against Exhibit G of the county
Candidate Guide (offices up for election; terms).

Machine guard (Contra Costa precedent): validate every parsed roster against
the county's qualified-candidate count before anything is written.

- Only ON BALLOT contests become confirmed records (the proof is the county's
  exhaustive on-ballot list; nothing here is left 'unverified').
- Shared statewide / Supreme Court / congressional records reuse their stable
  IDs and gain the Fresno county name (EXTEND below, roster-verified).
- Incumbent flags combine the proof's Incumbent(s) lines with per-candidate
  'Incumbent' designations.
- Terms come from Exhibit G; ST/Short Term contests become specials.
"""
import json
import re
import sys
from pathlib import Path
from parse_proof import validate as validate_proof

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "2026-11-03_Bay_Area_Elections.json"
PARSED = Path(__file__).resolve().parent / "proof-parsed.json"

PROOF_SRC = "S1510"
GUIDE_SRC = "S1511"
PARTY_CODE = {"Republican": "R", "Democratic": "D", "Libertarian": "L",
              "No Party Preference": "NPP", "Green": "G"}

SMALL = {"de", "del", "van", "la", "el", "di", "da"}

# proof contest -> existing stable dataset record (rosters verified equal below)
EXTEND = {
    "1100": "CA2026-014", "1110": "CA2026-016", "1120": "CA2026-017",
    "1130": "CA2026-013", "1140": "CA2026-019", "1150": "CA2026-012",
    "1160": "CA2026-015", "2000": "CA2026-018",
    "1651": "CA2026-040", "1653": "CA2026-039",
    "1232": "US2026-075", "1234": "US2026-076", "1235": "CA2026-006",
}

JURIS = {
    "1170": "California State Board of Equalization",
    "1230": "United States House of Representatives", "1231": "United States House of Representatives",
    "1233": "United States House of Representatives",
    "1301": "California State Senate", "1304": "California State Senate", "1308": "California State Senate",
    "1335": "California State Assembly", "1337": "California State Assembly",
    "1340": "California State Assembly", "1348": "California State Assembly",
    "1545": "Fresno County Superior Court", "1547": "Fresno County Superior Court",
    "1621": "California Court of Appeal, Fifth Appellate District",
    "1625": "California Court of Appeal, Fifth Appellate District",
    "1627": "California Court of Appeal, Fifth Appellate District",
    "1629": "California Court of Appeal, Fifth Appellate District",
    "1631": "California Court of Appeal, Fifth Appellate District",
    "1635": "California Court of Appeal, Fifth Appellate District",
    "2010": "Fresno County", "4001": "Fresno County",
    "2028": "Merced County Board of Education",
    "2021": "Fresno County Board of Education", "2024": "Fresno County Board of Education",
}
# convention-derived OCD IDs for new federal/legislative records (ocd_id_status: convention)
OCD = {
    "1230": "ocd-division/country:us/state:ca/cd:5", "1231": "ocd-division/country:us/state:ca/cd:21",
    "1233": "ocd-division/country:us/state:ca/cd:20",
    "1301": "ocd-division/country:us/state:ca/sldu:12", "1304": "ocd-division/country:us/state:ca/sldu:14",
    "1308": "ocd-division/country:us/state:ca/sldu:16",
    "1335": "ocd-division/country:us/state:ca/sldl:8", "1337": "ocd-division/country:us/state:ca/sldl:27",
    "1340": "ocd-division/country:us/state:ca/sldl:31", "1348": "ocd-division/country:us/state:ca/sldl:33",
}
OFFICE = {
    "1170": "Member", "1545": "Judge", "1547": "Judge",
    "1621": "Associate Justice", "1625": "Associate Justice", "1627": "Associate Justice",
    "1629": "Associate Justice", "1631": "Associate Justice", "1635": "Associate Justice",
    "2010": "County Superintendent of Schools", "4001": "Supervisor",
    "2028": "Member", "2021": "Member", "2024": "Member",
    "1230": "United States Representative", "1231": "United States Representative",
    "1232": "United States Representative", "1233": "United States Representative",
    "1234": "United States Representative", "1235": "United States Representative",
    "1301": "State Senator", "1304": "State Senator", "1308": "State Senator",
    "1335": "Member of the State Assembly", "1337": "Member of the State Assembly",
    "1340": "Member of the State Assembly", "1348": "Member of the State Assembly",
}
SEAT = {
    "1170": "District 1", "1545": "Position 6", "1547": "Position 7",
    "1621": "No. 1 seat - Arlan L. Harrell", "1625": "No. 3 seat - Amy K. Guerra",
    "1627": "No. 4 seat - Kathleen A. Meehan", "1629": "No. 5 seat - Mark W. Snauffer",
    "1631": "No. 6 seat - Thomas DeSantos", "1635": "No. 8 seat - Sonny S. Sandhu",
    "4001": "District 1",
    "1230": "CD-5", "1231": "CD-21", "1233": "CD-20",
    "1301": "SD-12", "1304": "SD-14", "1308": "SD-16",
    "1335": "AD-8", "1337": "AD-27", "1340": "AD-31", "1348": "AD-33",
}
# Exhibit G: 2-year mayor terms (Kerman, Selma, Sanger)
MAYOR_2Y = {"5090", "5195", "5170"}
DISTRICT_SUFFIX = {"Malaga County Water", "Pinedale County Water"}

COUNTY_NOTE = "N1553"
EXTEND_NOTE = "N1555"
SHARED_NOTE = "N1562"
SOLO_NOTE = "N1560"
NULL_NOTE = "N1557"
RUNOFF_NOTE = "N1558"
EXCLUDED_NOTE = "N1564"
PROOF_NOT_ON_BALLOT = Path(__file__).resolve().parent / "not-on-ballot-parsed.json"


def smart_title(name: str) -> str:
    parts = re.split(r"([ ,.'\-()\"‘’“”]+)", name)
    out = []
    for p in parts:
        if not p or re.fullmatch(r"[ ,.'\-()\"‘’“”]+", p):
            out.append(p)
            continue
        core = p
        low = core.lower()
        out.append(low if low in SMALL else core.title())
    joined = "".join(out)
    # title() flattens Mc/Mac prefixes: "Mcclintock" -> "McClintock"
    joined = re.sub(r"\b(Mc|Mac)([a-z])", lambda m: m.group(1) + m.group(2).upper(), joined)
    return joined


SMALL = {"de", "del", "van", "la", "el", "di", "da"}

def strip_noise(s: str):
    """Tokens of a name with parenthetical/quoted nicknames, JR/SR, and single
    initials removed (incumbent lines and printed names differ in these)."""
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[\"‘’“”][^\"‘’“”]*[\"‘’“”]", " ", s)
    s = re.sub(r"\b(I{1,3}|JR|SR)\.?\b", " ", s)
    return [t for t in re.findall(r"[A-Za-zÁ-úá-ú'.-]+", s) if len(t.strip(".'-")) > 1]


def norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", "".join(strip_noise(s)).lower())


def names_match(a: str, b: str) -> bool:
    ta, tb = {t.lower().strip(".'-") for t in strip_noise(a)}, {t.lower().strip(".'-") for t in strip_noise(b)}
    if not ta or not tb:
        return False
    if ta == tb or ta <= tb or tb <= ta:
        return True
    alias = {frozenset({'john', 'johnny'}), frozenset({'michael', 'mike'}), frozenset({'robert', 'bob'}),
             frozenset({'william', 'bill'}), frozenset({'jose', 'pepe'})}
    # one-sided nickname substitution: same size, differing by one alias pair
    if len(ta) == len(tb) and sum(1 for t in ta if t not in tb) == 1:
        odd_a = next(t for t in ta if t not in tb)
        odd_b = next(t for t in tb if t not in ta)
        if frozenset({odd_a, odd_b}) in alias:
            return True
    return False


def is_incumbent(candidate, proof):
    if candidate['incumbent_flag']:
        return True
    for inc in proof['incumbents']:
        name = re.sub(r'\s+(Elected|Appointed to Vacancy|Appointed in Lieu|Appointed|Vacated|Declared Elected)$', '', inc, flags=re.I)
        matches = [c for c in proof['candidates'] if names_match(c['name'], name)]
        if len(matches) == 1 and matches[0]['name'] == candidate['name']:
            return True
    return False


def header_split(header: str):
    m = re.match(r"^(NONPARTISAN OFFICES|VOTER NOMINATED OFFICES|JUDICIAL OFFICES|VOTER APPROVED)\s+(\S+)\s+(.*)$", header)
    assert m, header
    kind, domain, rest = m.groups()
    words = rest.split(" ")
    j = 0
    while j < len(words) and re.fullmatch(r"[A-Z][A-Z'’\-]*", words[j] or "x"):
        j += 1
    return kind, domain, " ".join(words[:j]), " ".join(words[j:])


def level_category(header: str, cid: str):
    kind, domain, juris, office = header_split(header)
    h = header.upper()
    if kind == "VOTER APPROVED":
        raise ValueError("ballot measures are out of scope: " + header)
    if kind == "VOTER NOMINATED OFFICES":
        if "UNITED STATES REPRESENTATIVE" in h:
            return "Federal", "U.S. House"
        if "STATE SENATOR" in h:
            return "State", "State Senate"
        if "ASSEMBLY" in h:
            return "State", "State Assembly"
        if "BOARD OF EQUALIZATION" in h:
            return "State", "Board of Equalization"
        raise ValueError(header)
    if kind == "JUDICIAL OFFICES" or domain == "JUDICIAL":
        if "SUPREME COURT" in h:
            return "State judiciary", "Supreme Court"
        if "APPEAL" in h:
            return "State judiciary", "Court of Appeal"
        return "State judiciary", "Superior Court"
    # NONPARTISAN
    if domain == "SCHOOL":
        if cid == "2010":
            return "County", "County elected officer"
        j = juris.upper()
        if "COMMUNITY COLLEGE" in j:
            return "Education", "Community college district"
        if "BOARD OF EDUCATION" in h:
            return "Education", "County board of education"
        if "UNIFIED" in j:
            return "Education", "Unified school district"
        if "ELEMENTARY" in j:
            return "Education", "Elementary school district"
        return "Education", "School district"
    if domain == "COUNTY":
        return "County", "County supervisor" if "SUPERVISOR" in h else "County elected officer"
    if domain == "CITY":
        return ("City or town", "Mayor") if "MAYOR" in h else ("City or town", "City Council")
    if domain == "DISTRICT":
        j = juris.upper()
        if "RECREATION" in j:
            return "Special district", "Parks and recreation"
        if "IRRIGATION" in j:
            return "Special district", "Irrigation"
        if "HEALTH" in j:
            return "Special district", "Healthcare"
        if "POLICE" in j:
            return "Special district", "Police protection"
        if "COMMUNITY SERVICE" in j:
            return "Special district", "Community services district"
        return "Special district", "Water"
    raise ValueError(header)


def is_short(header: str, title: str) -> bool:
    h = header.upper()
    return "SHORT TERM" in h or title.upper().endswith(" ST") or " ST," in title.upper()


def term_for(header: str, cid: str, title: str) -> str:
    h = header.upper()
    if is_short(header, title):
        return "Short term"
    if "SUPREME COURT" in h or "COURTS OF APPEAL" in h:
        return "12 years (full term)"
    if "SUPERIOR COURT" in h:
        return "6 years"
    if "UNITED STATES REPRESENTATIVE" in h:
        return "2 years"
    if "STATE SENATOR" in h:
        return "4 years"
    if "ASSEMBLY" in h:
        return "2 years"
    if "BOARD OF EQUALIZATION" in h:
        return "4 years"
    if "MAYOR" in h and cid in MAYOR_2Y:
        return "2 years"
    return "4 years"


def district_seat(header: str, title: str, cid: str) -> str:
    if cid in SEAT:
        return SEAT[cid]
    h = header
    parts = []
    m = re.search(r"Trustee Area No\.?\s*(\d+)", h)
    if m:
        parts.append("Trustee Area " + m.group(1))
    m = re.search(r"Member No\.?\s*(\d+)", h)
    if m and not parts:
        parts.append("Trustee Area " + m.group(1))
    m = re.search(r"Division No\.?\s*(\d+)", h)
    if m and not parts:
        parts.append("Division " + m.group(1))
    m = re.search(r"Zone No\.?\s*(\d+)", h)
    if m and not parts:
        parts.append("Zone " + m.group(1))
    m = re.search(r"District Area (\d+)", h)
    if m and not parts:
        parts.append("District Area " + m.group(1))
    m = re.search(r"District No\.?\s*(\d+)", h)
    if m and not parts:
        parts.append("District " + m.group(1))
    if is_short(header, title):
        return (parts[0] + " (short term)") if parts else "At-large (short term)"
    return parts[0] if parts else "At large"


def office_name(header: str, cid: str):
    if cid in OFFICE:
        return OFFICE[cid]
    _, _, _, office = header_split(header)
    office = re.sub(r"[,]?\s*(Trustee Area No\.?\s*\d+|Division No\.?\s*\d+|Zone No\.?\s*\d+|"
                    r"District Area \d+|District No\.?\s*\d+|District \d+|Member No\.?\s*\d+|"
                    r"No\.?\s*\d+|Office No\.?\s*\d+|Short Term|At Large)\s*$", "", office).strip().rstrip(",")
    o = office.lower()
    if o.startswith("member, city council"):
        return "City Council Member"
    if o.startswith("governing board member"):
        return "Governing Board Member"
    if o.startswith("member, board of directors"):
        return "Director"
    if o.startswith("member, board of education"):
        return "Member"
    return office


def jurisdiction_name(header: str, cid: str):
    if cid in JURIS:
        return JURIS[cid]
    _, _, juris, _ = header_split(header)
    if not juris:
        return None
    j = juris.title()
    if j.upper().startswith("CITY OF "):
        j = "City of " + j[8:]
    if j in DISTRICT_SUFFIX:
        j += " District"
    return j


def main():
    data = json.loads(DATA_PATH.read_text())
    original_ids = {p['id'] for p in data['positions']}
    parsed = json.loads(PARSED.read_text())
    validate_proof(parsed, on_ballot=True)
    off = json.loads(PROOF_NOT_ON_BALLOT.read_text())
    validate_proof(off, on_ballot=False)
    by_id = {p["id"]: p for p in data["positions"]}
    nums = [int(p["id"].split("-")[1]) for p in data["positions"] if p["id"].startswith("CA2026-")]
    next_num = max(nums) + 1

    # Guard 1: EXTEND targets must carry exactly the proof's printed roster.
    for cid, pid in EXTEND.items():
        proof = parsed[cid]
        printed = [smart_title(c["name"]) for c in proof["candidates"]]
        have = [c["name"] for c in (by_id[pid].get("candidates") or [])]
        extra_p = [a for a in printed if not any(names_match(a, b) for b in have)]
        extra_h = [b for b in have if not any(names_match(a, b) for a in printed)]
        if len(printed) != len(have) or extra_p or extra_h:
            raise ValueError(f'Existing roster mismatch: {cid}, {pid}, {extra_p}, {extra_h}')
        if 'Fresno' in by_id[pid]['counties']:
            raise ValueError('Fresno already imported; refusing duplicate IDs/counties')

    # Guard 2: every ON BALLOT contest's roster matches the county's own counts.
    for cid, c in parsed.items():
        if not c['on_ballot']:raise ValueError('Unexpected off-ballot contest: ' + cid)
        want = max(d["qualified"] for d in c["districts"])
        if want != len(c['candidates']):raise ValueError('Qualified roster mismatch: ' + cid)

    # alphabetical insertion keeps every derived county list in the established order
    scope = data["election"]["counties_in_scope"]
    entry = {"name": "Fresno", "ocd_division_id": "ocd-division/country:us/state:ca/county:fresno"}
    idx = next((i for i, c in enumerate(scope) if c["name"] > entry["name"]), len(scope))
    scope.insert(idx, entry)
    data["election"]["publication_version"] = "2026-11-03.2"

    urls = data["address_lookup"]["county_election_urls"]
    urls["Fresno"] = "https://www.fresnocountyca.gov/Departments/County-ClerkRegistrar-of-Voters/Elections"
    data["address_lookup"]["county_election_urls"] = {k: urls[k] for k in sorted(urls)}
    for i, lim in enumerate(data["address_lookup"]["lookup_limitations"]):
        data["address_lookup"]["lookup_limitations"][i] = lim.replace(
            "the five researched counties", "the researched counties")

    for cid, pid in EXTEND.items():
        p = by_id[pid]
        p["counties"] = p["counties"] + ["Fresno"]
        p.setdefault("note_ids", [])
        if EXTEND_NOTE not in p["note_ids"]:
            p["note_ids"].append(EXTEND_NOTE)
        if PROOF_SRC not in p.setdefault("source_ids", []):
            p["source_ids"].append(PROOF_SRC)

    new_recs = {"senate": [], "assembly": [], "rest": []}
    id_log = {}
    for cid in sorted(parsed, key=int):
        if cid in EXTEND:
            continue
        proof = parsed[cid]
        header = proof["office_header"]
        level, category = level_category(header, cid)
        seats = max(d["vote_for"] for d in proof["districts"])
        incumbent_names = set()
        for inc in proof["incumbents"]:
            base = re.sub(r"\s+(Elected|Appointed to Vacancy|Appointed in Lieu|Appointed|Vacated|Declared Elected)$",
                          "", inc, flags=re.I)
            incumbent_names.add(norm(base))
        roster = []
        for cand in proof["candidates"]:
            name = smart_title(cand["name"])
            entry = {"name": name}
            if cand["party"]:
                entry["party"] = PARTY_CODE[cand["party"]]
            if is_incumbent(cand, proof):
                entry["incumbent"] = True
            roster.append(entry)
        retention = "JUSTICE" in header.upper() and ("APPEAL" in header.upper() or "SUPREME" in header.upper())
        short = is_short(header, proof["title"])
        pid = f"CA2026-{next_num:03d}"
        id_log[cid] = pid
        next_num += 1
        note_ids = [COUNTY_NOTE]
        if short:
            note_ids.append("N1556")
        rec = {
            "id": pid,
            "counties": ["Fresno"],
            "government_level": level,
            "office_category": category,
            "jurisdiction": jurisdiction_name(header, cid),
            "office": office_name(header, cid),
            "district_or_seat": district_seat(header, proof["title"], cid),
            "seats": seats,
            "term": term_for(header, cid, proof["title"]),
            "election_type": "retention" if retention else ("special" if short else "general"),
            "ballot_status": "confirmed",
            "partisan": header.startswith("VOTER NOMINATED OFFICES"),
            "ocd_id_status": "convention" if cid in OCD else "unverified",
            "candidate_list_status": "complete",
            "source_ids": [PROOF_SRC, GUIDE_SRC],
            "primary_source_page": f"CFMR001 contest {cid}",
            "note_ids": note_ids,
            "candidate_list_note_id": "N1561",
        }
        if cid in OCD:
            rec["ocd_division_id"] = OCD[cid]
            rec["jurisdiction_ocd_division_id"] = "ocd-division/country:us/state:ca"
        elif level == "City or town":
            key = rec["jurisdiction"].split("City of ", 1)[-1].lower().replace(" ", "_")
            place = f"ocd-division/country:us/state:ca/place:{key}"
            rec["jurisdiction_ocd_division_id"] = place
            m = re.match(r"District (\d+)", rec["district_or_seat"])
            rec["ocd_division_id"] = f"{place}/council_district:{m.group(1)}" if m else place
            rec["ocd_id_status"] = "convention"
        elif cid == "4001":
            rec["ocd_division_id"] = "ocd-division/country:us/state:ca/county:fresno/council_district:1"
            rec["jurisdiction_ocd_division_id"] = "ocd-division/country:us/state:ca/county:fresno"
            rec["ocd_id_status"] = "convention"
        elif cid in ("1545", "1547", "2010"):
            # countywide electorates: Superior Court seats and the County Superintendent
            rec["ocd_division_id"] = "ocd-division/country:us/state:ca/county:fresno"
            rec["jurisdiction_ocd_division_id"] = "ocd-division/country:us/state:ca/county:fresno"
            rec["ocd_id_status"] = "convention"
        if retention:
            rec["ballot_responses"] = ["Yes", "No"]
        if cid in ("1170", "1545", "1547", "2010") or header.startswith("JUDICIAL") or "COURTS OF APPEAL" in header.upper():
            # Fresno lies wholly inside these electorates (BOE D1, Superior Court,
            # Court of Appeal 5th District, county office) — countywide flag per the
            # existing appellate/BOE record convention.
            rec["countywide_electorate"] = True
        if level == "Federal":
            # no FEC money layer in this county pass; absence of FEC records is N907, never zero
            note_ids.append("N907")
        local = level in ("County", "City or town", "Education", "Special district")
        if local:
            rec["ballotpedia_url"] = "https://ballotpedia.org/Fresno_County,_California,_elections,_2026"
            rec["ballotpedia_page_scope"] = "county_election_coverage"
            note_ids.append(SHARED_NOTE) if proof["shared_with"] else None
        if len(roster) == 0:
            rec["candidates"] = None
            rec["candidate_list_status"] = "unverified"
            rec["candidate_list_note_id"] = NULL_NOTE
            note_ids.append(NULL_NOTE)
        else:
            rec["candidates"] = roster
            if len(roster) == 1:
                note_ids.append(SOLO_NOTE)
        if cid in ("1545", "1547"):
            note_ids.append(RUNOFF_NOTE)
        if cid == "2028":
            note_ids.append(SHARED_NOTE)
        rec["note_ids"] = sorted(set(note_ids))
        bucket = "senate" if category == "State Senate" else ("assembly" if category == "State Assembly" else "rest")
        new_recs[bucket].append(rec)

    # Excluded determinations from the companion 'Contests not on Ballot' proof
    # (same CFMR001 print run): June-elected/appointed officers and zero-filing
    # seats — Contra Costa precedent records these as excluded with filed names.
    for cid, proof in sorted(off.items(), key=lambda kv: int(kv[0])):
        header = proof["office_header"]
        level, category = level_category(header, cid)
        seats = max(d["vote_for"] for d in proof["districts"])
        rec = {
            "id": f"CA2026-{next_num:03d}",
            "counties": ["Fresno"],
            "government_level": level,
            "office_category": category,
            "jurisdiction": jurisdiction_name(header, cid),
            "office": office_name(header, cid),
            "district_or_seat": district_seat(header, proof["title"], cid),
            "seats": seats,
            "term": term_for(header, cid, proof["title"]),
            "election_type": "special" if is_short(header, proof["title"]) else "general",
            "ballot_status": "excluded",
            "partisan": header.startswith("VOTER NOMINATED OFFICES"),
            "ocd_id_status": "unverified",
            "candidate_list_status": "unverified",
            "candidates": None,
            "source_ids": ["S1514", GUIDE_SRC],
            "primary_source_page": f"CFMR001 contests-not-on-ballot contest {cid}",
            "note_ids": [EXCLUDED_NOTE],
        }
        id_log[cid] = rec["id"]
        next_num += 1
        if proof["candidates"]:
            filed = []
            for cand in proof["candidates"]:
                entry = {"name": smart_title(cand["name"]), "source_ids": ["S1514"]}
                if cand["party"]:
                    entry["party"] = PARTY_CODE[cand["party"]]
                if is_incumbent(cand, proof):
                    entry["incumbent"] = True
                filed.append(entry)
            rec["filed_candidates_not_confirmed_on_ballot"] = filed
        if proof["shared_with"]:
            rec["note_ids"].append(SHARED_NOTE)
        if cid == "2028":
            rec["note_ids"].append(SHARED_NOTE)
        bucket = "senate" if category == "State Senate" else ("assembly" if category == "State Assembly" else "rest")
        new_recs[bucket].append(rec)

    def insert_after(positions, predicate, records):
        idx = max(i for i, p in enumerate(positions) if predicate(p))
        positions[idx + 1:idx + 1] = records

    insert_after(data["positions"], lambda p: p.get("office_category") == "State Senate", new_recs["senate"])
    insert_after(data["positions"], lambda p: p.get("office_category") == "State Assembly", new_recs["assembly"])
    data["positions"].extend(new_recs["rest"])

    data["sources"]["S1510"] = {
        "url": "https://www2.fresnocountyca.gov/2850/post/2026NOV/Contests%20on%20Ballot%20with%20Qualified%20Candidates.pdf",
        "title": "Fresno County Registrar of Voters — Contest/Candidate Proof List, November 3, 2026 Consolidated Statewide General Election (CFMR001, printed 10/12/2026; contests on ballot with qualified candidates and per-contest on-ballot status)",
    }
    data["sources"]["S1511"] = {
        "url": "https://www.fresnocountyca.gov/files/sharedassets/county/v/1/county-clerk-registrar-of-voters/1_election-pages/2026_3_nov_statewide-general/important-information/2026-6-5_candidate-guide-for-november-3-2026-election.pdf",
        "title": "County of Fresno Candidate Guide — November 3, 2026 Consolidated Statewide General Election (last updated 6/29/2026; Exhibit G: Offices Up for Election, terms of office)",
    }
    data["sources"]["S1512"] = {
        "url": "https://www.fresnocountyca.gov/Departments/County-ClerkRegistrar-of-Voters/Elections/Election-Information/2026/November-3-2026-Consolidated-Statewide-General-Election",
        "title": "Fresno County Clerk/Registrar of Voters — November 3, 2026 Consolidated Statewide General Election information page",
    }
    data["sources"]["S1513"] = {
        "url": "https://ballotpedia.org/Fresno_County,_California,_elections,_2026",
        "title": "Ballotpedia — Fresno County, California, elections, 2026 (corroboration only)",
    }

    data["sources"]["S1514"] = {
        "url": "https://www2.fresnocountyca.gov/2850/post/2026Nov/Contests%20not%20on%20Ballot.pdf",
        "title": "Fresno County Registrar of Voters — Contest/Candidate Proof List, November 3, 2026 (CFMR001, printed 10/12/2026; contests NOT on the ballot with filed candidates)",
    }

    data["notes"]["N1553"] = ("Fresno County was added to coverage on November 3, 2026 from the Registrar's exhaustive CFMR001 "
                              "Contest/Candidate Proof List printed 10/12/2026: every contest the on-ballot list carries is confirmed on the "
                              "November ballot with its complete printed roster, machine-verified to equal the county's own qualified-candidate counts (filings may exceed qualified candidates) (research/fresno/). Terms and short-term designations come from Exhibit G of the "
                              "county Candidate Guide. Ballot measures are outside this dataset's scope and are not included.")
    data["notes"]["N1555"] = ("Fresno County residents vote in this contest per the CFMR001 district line and shared-county list "
                              "(printed 10/12/2026); the Fresno county name was added to the existing stable record rather than "
                              "cloning it. Counties arrays still list only researched counties.")
    data["notes"]["N1556"] = ("This contest was certified by Fresno County as a short-term (ST) office on the November 3, 2026 "
                              "ballot per CFMR001 and Exhibit G; the county's Exhibit G term column may state the full seat term — "
                              "the elected term runs only to the seat's expiry, which the county does not print as a date here.")
    data["notes"]["N1557"] = ("The Huron City Council short-term contest (CFMR001 contest 5088) is ON BALLOT with one filing and zero "
                              "qualified candidates: no names print, so the roster is null (write-in only) and never an empty array. "
                              "The county records the seat as Vacant/Vacated.")
    data["notes"]["N1558"] = ("Fresno County Superior Court judge Positions 6 and 7 appear on the November 3 ballot between two "
                              "candidates each; the CFMR001 incumbent line names the sitting judge (Jon Conklin, D. Tyler Tharpe) "
                              "whose seats these are; both printed names seek the same continuing office.")
    data["notes"]["N1560"] = ("Solo-candidate contest confirmed on ballot by the exhaustive CFMR001 proof; the single printed name is "
                              "elected unless write-in totals exceed it, which this dataset does not assert.")
    data["notes"]["N1561"] = ("Roster: printed names per the CFMR001 proof (the county prints candidates in random alpha order); the "
                              "county's qualified-candidate counts match the published roster exactly for every Fresno contest.")
    data["notes"]["N1562"] = ("The CFMR001 shared list shows this electorate extends beyond Fresno County (adjacent counties named by "
                              "the county); only Fresno is researched, so the counties array lists Fresno alone. Shared territory alone "
                              "is never treated as electorate membership — the county's own district line is the evidence.")
    data["notes"]["N1563"] = ("Fresno County lies wholly within Board of Equalization District 1 per CFMR001 contest 1170 (its "
                              "shared-county list covers all of Fresno and 27 other counties), not the District 2 record shared by "
                              "the original five counties; Fresno voters therefore see the separate District 1 contest.")
    data["notes"]["N1564"] = ("This Fresno contest appears on the county's companion CFMR001 'Contests not on Ballot' proof (printed "
                              "10/12/2026): the seat was decided without a November contest — officer elected in June or appointed in "
                              "lieu — or the filing produced no qualified ballot entry. Provisional filed names are retained where the "
                              "county printed them. How each excluded seat was filled follows the county's incumbent line; no runoff or "
                              "write-in outcome is asserted.")

    # BOE note for the new District 1 record
    boe = next(p for p in data["positions"] if p["id"] == id_log["1170"])
    boe["note_ids"] = boe.get("note_ids", []) + ["N1563"]

    data["coverage"]["limitations"].append(
        "Fresno County was added November 3, 2026 from the Registrar's exhaustive CFMR001 Contest/Candidate Proof List (printed "
        "10/12/2026): all 106 contests it carries are confirmed with complete printed rosters, machine-verified against the county's own "
        "candidate counts; terms come from Exhibit G of the county Candidate Guide. Fresno lies wholly in Board of Equalization District 1. "
        "Shared statewide, Supreme Court and congressional contests reuse existing stable IDs extended with the Fresno county name.")
    data["coverage"]["limitations"].append(
        "The Fresno inventory includes one cross-county electorate where Fresno residents vote in another county's board: Merced County "
        "Board of Education Trustee Area 5. Fresno districts shared with adjacent counties (Kings, Tulare, Madera et al. per the CFMR001 "
        "shared lists) list Fresno only — those counties are unresearched, and territory alone is never electorate evidence. The county's "
        "companion 'Contests not on Ballot' proof (also printed 10/12/2026) records 114 contests as excluded determinations: officers "
        "elected in June or appointed in lieu with no November contest, and zero-filing seats; their provisional filers are retained under "
        "filed_candidates_not_confirmed_on_ballot.")

    # recompute coverage counters exactly as check_data derives them
    positions = data["positions"]
    confirmed = [p for p in positions if p["ballot_status"] == "confirmed"]
    printed = [c for p in positions for c in (p.get("candidates") or [])]
    cov = data["coverage"]
    cov["confirmed_contests"] = len(confirmed)
    cov["confirmed_seats"] = sum(p["seats"] or 0 for p in confirmed)
    cov["unresolved_scheduled_contests"] = sum(p["ballot_status"] == "unverified" for p in positions)
    cov["printed_candidate_entries"] = len(printed)
    cov["confirmed_contests_missing_candidate_rosters"] = sum(p["candidate_list_status"] != "complete" for p in confirmed)
    cov["positions_with_ocd_division_id"] = sum("ocd_division_id" in p for p in positions)
    cov["positions_with_ballotpedia_url"] = sum("ballotpedia_url" in p for p in positions)
    cov["printed_candidates_with_ballotpedia_url"] = sum("ballotpedia_url" in c for c in printed)
    cov["printed_candidates_with_x_url"] = sum("x_url" in c for c in printed)
    cov["printed_candidates_with_secondary_x_url"] = sum("secondary_x_url" in c for c in printed)
    cov["printed_candidates_with_campaign_url"] = sum("campaign_url" in c for c in printed)
    cov["printed_candidates_with_gaza_evidence"] = sum(bool(c.get("gaza_evidence")) for c in printed)
    cov["printed_candidates_with_gaza_voting_records"] = sum(bool(c.get("gaza_voting_records")) for c in printed)
    cov["printed_candidates_with_uscpr_grade"] = sum(bool(c.get("uscpr_grade")) for c in printed)
    cov["printed_candidates_with_gaza_platform"] = sum(bool(c.get("gaza_platform")) for c in printed)
    cov["printed_candidates_with_platform_positions"] = sum(bool(c.get("platform_positions")) for c in printed)
    cov["printed_candidates_with_endorsement_images"] = sum(bool(c.get("endorsement_images")) for c in printed)
    cov["printed_candidates_with_endorsements"] = sum(bool(c.get("endorsements")) for c in printed)
    cov["printed_candidates_with_independent_expenditures"] = sum(
        (c.get("independent_expenditures") or {}).get("for_total", 0)
        + (c.get("independent_expenditures") or {}).get("against_total", 0) > 0 for c in printed)

    sys.path.insert(0, str(ROOT / 'scripts'))
    import build_recommendations as recommendations
    plan = json.loads(recommendations.PLAN.read_text())
    added_ids = [p['id'] for p in data['positions'] if p['id'] not in original_ids]
    expanded = recommendations.extend_county_plan(plan, data, added_ids)
    # All validation finishes before replacing either maintained input.
    old_data, old_plan = DATA_PATH.read_bytes(), recommendations.PLAN.read_bytes()
    try:
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
        recommendations.PLAN.write_text(json.dumps(expanded, ensure_ascii=False, indent=2) + '\n')
    except BaseException:
        DATA_PATH.write_bytes(old_data)
        recommendations.PLAN.write_bytes(old_plan)
        raise
    manifest = {'format':'county-expansion-manifest/v1', 'county':'Fresno',
                'base_positions':sorted(original_ids), 'added_positions':added_ids,
                'proof_contests':id_log}
    (PARSED.parent/'import-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print("new positions:", sum(len(v) for v in new_recs.values()))
    print("total positions:", len(data["positions"]))
    print("coverage:", {k: cov[k] for k in ("confirmed_contests", "confirmed_seats", "printed_candidate_entries")})
    print("id allocation sample:", dict(list(id_log.items())[:6]), "...", dict(list(id_log.items())[-3:]))


if __name__ == "__main__":
    main()
