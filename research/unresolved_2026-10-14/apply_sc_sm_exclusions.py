#!/usr/bin/env python3
"""Resolve the final six unresolved scheduled contests (Santa Clara x4, San Mateo x2) as excluded.

Evidence chain (see research/unresolved_2026-10-14/evidence-packet.md):
  Santa Clara: CFMR001 Contest/Candidate Proof List printed 8/7/2026 shows Num Cands 0 /
  Num Qualified 0 for contests 6042, 6043(*extension), 6080, 6103; the Final Qualified List of
  Local Eligible Candidates (9/28/2026, extraction verified complete at Grand Total 287) has no
  row for any of the four districts — not even an 'On Ballot: No' removal row; the Unofficial
  Write-In Candidate List (CFMR028 printed 9/24/2026, range 1030-6103) shows no write-in filings;
  ballot/CVIG materials were finalized 8/28/2026. ROV district pages now show holdover/appointed
  incumbents with a 2026 next election.
  San Mateo: Bayshore ESD short term and Colma Fire PD Director are scheduled in the county
  Candidate Guide but absent from all three prints (7/31, 8/4, 9/3/2026) of the exhaustive
  'All Contests / Qualified Candidates Only' Roster of Candidates — every other scheduled local
  office appears — and no later candidate list exists; Sample Ballot mailing began 9/25/2026.
Jev (TypeSafe System One, jev-1.13.0) adjudicated exclude_confirmed at p=0.98 / 0.79 / 0.78 and
seats_2 for CA2026-302 at p=0.87 (research/unresolved_2026-10-14/jev-adjudication-raw.json).

How each seat is filled is deliberately NOT asserted: no county published the underlying
cancellation/appointment resolution online. Idempotent; asserts state before writing. The dataset
is committed with one-space indentation — reproduce byte-exactly or the diff becomes churn.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "2026-11-03_Bay_Area_Elections.json"

SC_IDS = ["CA2026-225", "CA2026-226", "CA2026-227", "CA2026-228"]
SM_IDS = ["CA2026-302", "CA2026-308"]

NEW_SOURCES = {
    "S1091": {"url": "https://files.santaclaracounty.gov/exjcpb1296/2026-08/unofficial-list-of-local-candidates-8.03.2026-v2.pdf?VersionId=f6GLJP4yYdQ3y8b.XBktrwmxVeOfO9og",
              "title": "Santa Clara County ROV — Contest/Candidate Proof List (CFMR001 print date/time 8/7/2026 8:44:32PM; totals verified: Total Contests 133, Total Candidates Filed 283); contests 6042/6043/6080/6103 show Num Cands 0 / Num Qualified 0"},
    "S1092": {"url": "https://files.santaclaracounty.gov/exjcpb1296/2026-09/writeincandidates_09222026.pdf?VersionId=JaOEeCylOnErqYfJrEZ7T4w1FRV30ssO",
              "title": "Santa Clara County ROV — Unofficial List of Local Write-In Candidates (CFMR028 print date/time 9/24/2026; contests 1030-6103, Total Contests 100, Total Candidates Filed 0); no write-in filings for contests 6042/6043/6080/6103"},
    "S1093": {"url": "https://smcacre.gov/system/files/2026-07/52_candidateroster_0731.pdf",
              "title": "San Mateo County ACRE — Roster of Candidates, All Contests / Qualified Candidates Only (CFMR009 print date/time 7/31/2026); no Bayshore ESD Short Term or Colma Fire PD contest rows"},
    "S1094": {"url": "https://smcacre.gov/system/files/2026-08/52_candidateroster_0804.pdf",
              "title": "San Mateo County ACRE — Roster of Candidates, All Contests / Qualified Candidates Only (CFMR009 print date/time 8/4/2026); no Bayshore ESD Short Term or Colma Fire PD contest rows"},
    "S1095": {"url": "https://smcacre.gov/system/files/2026-08/List%20of%20Offices%20with%20Extended%20Candidate%20Filing%20Periodjatas8.12.pdf",
              "title": "San Mateo County ACRE — List of Offices with Extended Candidate Filing Period (updated 8/12/26); includes Bayshore ESD Full Term and Colma Fire PD, not Bayshore ESD Short Term"},
    "S1096": {"url": "https://vote.santaclaracounty.gov/lions-gate-community-service-district",
              "title": "Santa Clara County ROV — Lion's Gate Community Service District page (directors Sattler/Pashby/Stuart marked holdover/appointed, next election 2026)"},
    "S1097": {"url": "https://vote.santaclaracounty.gov/san-martin-county-water-district",
              "title": "Santa Clara County ROV — San Martin County Water District page (Norgard short-term + Vacant seat, next election 2026)"},
    "S1098": {"url": "https://vote.santaclaracounty.gov/silver-creek-valley-country-club-geologic-hazard-abatement-district",
              "title": "Santa Clara County ROV — Silver Creek Valley Country Club GHAD page (Katwan/Hansen/Roberts holdovers, next election 2026)"},
}

NEW_NOTES = {
    "N890": "Resolved October 14, 2026: the Registrar's Contest/Candidate Proof List (CFMR001, printed August 7, 2026) records zero candidates filed for this office, and the Final Qualified List of Local Eligible Candidates (posted September 28, 2026; extraction verified complete at 287 qualified candidates) contains no row for this district — not even an 'On Ballot: No' removal row — while the Unofficial Write-In Candidate List (printed September 24, 2026) shows no write-in filings. With ballot and County Voter Information Guide materials finalized August 28, 2026, this contest cannot appear on the November 3 ballot; the Registrar's own district page now lists its incumbents as holdovers or appointees with a 2026 next election. The underlying cancellation or appointment resolution is not published online, so how each seat is filled is not asserted.",
    "N891": "Resolved October 14, 2026: this office appears in the county Candidate Guide's scheduled-offices table but in none of the three prints (July 31, August 4 and September 3, 2026) of the county's exhaustive 'All Contests / Qualified Candidates Only' Roster of Candidates — every other scheduled local office appears — and no later candidate list has been published. With Sample Ballot & Voter Information Pamphlet mailing beginning September 25, 2026, a contest with zero qualified candidates cannot appear on mailed ballots. The underlying cancellation or appointment resolution is not published online, so how the seat is filled is not asserted.",
    "N892": "October 14, 2026: seats corrected from 1 to 2 per the county Candidate Guide's scheduled-offices table ('Bayshore Elementary School District, Governing Board (Short Term)' — Seats up: 2).",
}


def main() -> None:
    raw = DATASET.read_text(encoding="utf-8")
    data = json.loads(raw)

    pub = data["election"]["publication_version"]
    if pub == "2026-10-14.1":
        print("already applied (publication 2026-10-14.1); nothing to do")
        return
    assert pub == "2026-10-13.1", f"unexpected publication_version {pub!r}"

    positions = {p["id"]: p for p in data["positions"]}
    for pid in SC_IDS + SM_IDS:
        p = positions[pid]
        assert p["ballot_status"] == "unverified", f"{pid} not unverified"
        assert p.get("candidates") is None, f"{pid} unexpectedly has a candidate roster"

    cov = data["coverage"]
    assert cov["unresolved_scheduled_contests"] == 6, cov["unresolved_scheduled_contests"]
    for nid in ("N167", "N218", "N222"):
        assert nid in data["notes"], f"missing legacy note {nid}"
    for sid in NEW_SOURCES:
        assert sid not in data["sources"], f"{sid} already exists"
    for nid in NEW_NOTES:
        assert nid not in data["notes"], f"{nid} already exists"

    # --- flip the six contests --------------------------------------------
    for pid in SC_IDS:
        p = positions[pid]
        p["ballot_status"] = "excluded"
        p["source_ids"] = list(dict.fromkeys(p["source_ids"] + ["S1091", "S1092"]))
        page = {"CA2026-225": "S1096", "CA2026-226": "S1096",
                "CA2026-227": "S1097", "CA2026-228": "S1098"}[pid]
        p["source_ids"] = list(dict.fromkeys(p["source_ids"] + [page]))
        p["note_ids"] = [n for n in p["note_ids"] if n != "N167"] + ["N890"]

    for pid in SM_IDS:
        p = positions[pid]
        p["ballot_status"] = "excluded"
        p["source_ids"] = list(dict.fromkeys(p["source_ids"] + ["S1093", "S1094", "S1095"]))
        p["note_ids"] = [n for n in p["note_ids"] if n not in ("N218", "N222")] + ["N891"]

    bayshore = positions["CA2026-302"]
    assert bayshore["seats"] == 1, bayshore["seats"]
    bayshore["seats"] = 2
    bayshore["note_ids"] = list(dict.fromkeys(bayshore["note_ids"] + ["N892"]))

    # --- registry updates ---------------------------------------------------
    data["sources"].update(NEW_SOURCES)
    for nid in ("N167", "N218", "N222"):
        users = [p["id"] for p in data["positions"] if nid in (p.get("note_ids") or [])]
        assert users == [], f"{nid} still referenced by {users}"
        del data["notes"][nid]
    data["notes"].update(NEW_NOTES)

    cov["unresolved_scheduled_contests"] = 0
    old_lim = ("This is not yet a certified exhaustive ballot dataset: unresolved "
               "cancellation/appointment questions and unverified local OCD identifiers remain.")
    new_lim = ("This is not yet a certified exhaustive ballot dataset: unverified local OCD "
               "identifiers remain, and excluded contests record final ballot status only — how "
               "each excluded seat was filled (holdover or appointment in lieu) is not asserted.")
    assert old_lim in cov["limitations"], "coverage limitation text changed; update apply script"
    cov["limitations"] = [new_lim if l == old_lim else l for l in cov["limitations"]]

    data["election"]["publication_version"] = "2026-10-14.1"

    # --- byte-exact write (indent=1) ---------------------------------------
    out = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    DATASET.write_text(out, encoding="utf-8")

    check = json.loads(DATASET.read_text(encoding="utf-8"))
    assert check["election"]["publication_version"] == "2026-10-14.1"
    assert sum(1 for p in check["positions"] if p["ballot_status"] == "unverified") == 0
    assert sum(1 for p in check["positions"] if p["ballot_status"] == "excluded") == 76
    print("applied: 6 contests excluded (SC x4, SM x2); CA2026-302 seats 1->2; publication 2026-10-14.1")


if __name__ == "__main__":
    main()
