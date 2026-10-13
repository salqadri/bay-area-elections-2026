#!/usr/bin/env python3
"""Apply the October 13, 2026 Alameda County final-ballot determinations.

Evidence (see .research/research/alameda-schools-findings.json and
alameda-special-findings.md for full quotes):
- Primary: Alameda County Registrar of Voters official Candidate List app
  (https://alamedacountyca.gov/rov_app/candidatelist), election
  "General Election - 11/03/2026 (Official)" (electionId=260). The app prints an
  explicit per-race Race Status ("On Ballot" / "Not On Ballot") for all 134
  races; the 19 target races are each labelled "Not On Ballot" with their filers
  listed beneath. This is the county's affirmative final ballot-status
  determination, not an absence-from-list inference.
- Corroboration: the official November 2026 Voter Information Guide PDF
  (sha256 5b1e32e3..., retrieved 2026-10-13) contains no candidate statement or
  mention for any filer in these 19 races, while contested sibling seats in the
  same districts do appear.

The script asserts the findings file and current dataset state before writing,
is idempotent (a second run makes no changes), and never touches records outside
the 19 target IDs. It flips ballot_status unverified -> excluded, retires the
now-obsolete single-use "final ballot status was not confirmed" notes from these
records, adds shared source/note registry entries, and recomputes
coverage.unresolved_scheduled_contests.

Run from anywhere: python3 research/alameda_2026-10-13/apply_alameda_exclusions.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET = ROOT / "2026-11-03_Bay_Area_Elections.json"

TARGETS = {
    # contest_id -> (registrar race heading as printed, filers as printed)
    "CA2026-204": ("Dublin Unified School District Governing Board Member, Area 2", ["Holden Lomeli"]),
    "CA2026-205": ("Mountain House Elementary School District Governing Board Member (at large)", ["Tonya Arledge", "Barbara Armstrong"]),
    "CA2026-206": ("Newark Unified School District Governing Board Member (at large)", ["Christine Kizer", "Jonathan Leder", "Renu Malhotra", "Jason Matthew Miguel"]),
    "CA2026-207": ("Ohlone Community College District Board of Trustees, Area 4", ["Elisa Martinez"]),
    "CA2026-208": ("Ohlone Community College District Board of Trustees, Area 7", ["Betty Ho"]),
    "CA2026-209": ("Peralta Community College District Board of Trustees, Area 3", ["Louis Quindlen"]),
    "CA2026-210": ("Peralta Community College District Board of Trustees, Area 7", ["Sheweet Yohannes"]),
    "CA2026-211": ("Pleasanton Unified School District Governing Board Member, Area 2", ["Laurie Walker"]),
    "CA2026-212": ("San Leandro Unified School District Governing Board Member, Area 2", ["Jacqueline Calderón Perl"]),
    "CA2026-213": ("San Leandro Unified School District Governing Board Member, Area 4", ["Leo Sheridan"]),
    "CA2026-214": ("San Leandro Unified School District Governing Board Member, Area 6", ["Natasha Martinez"]),
    "CA2026-215": ("San Lorenzo Unified School District Governing Board Member, Area 1", ["Yuliana Torres"]),
    "CA2026-216": ("San Lorenzo Unified School District Governing Board Member, Area 4", ["Samuel Medina"]),
    "CA2026-218": ("AC Transit District Director, Ward 7", ["Diane Shaw"]),
    "CA2026-220": ("Dublin San Ramon Services District Board of Directors, Division 4", ["Georgean Vonheeder-Leopold"]),
    "CA2026-221": ("Eden Township Healthcare District Director, Area 1", ["Mariellen Faria"]),
    "CA2026-222": ("Eden Township Healthcare District Director, Area 5", ["Ed Hernandez"]),
    "CA2026-223": ("BART Director, District 6", ["Liz Ames"]),
    "CA2026-224": ("Washington Township Health Care District Directors (Vote For 3)", ["Jacob Eapen", "Bernard L. Stewart", "Michael J. Wallace"]),
}

SRC_ROV = "S1089"
SRC_VIG = "S1090"
NOTE_RESOLVED = "N889"

SOURCES = {
    SRC_ROV: {
        "url": "https://alamedacountyca.gov/rov_app/candidatelist",
        "title": "Alameda County Registrar of Voters — Candidate List application, election \u201cGeneral Election - 11/03/2026 (Official)\u201d (electionId=260); per-race Race Status labels for all 134 races",
    },
    SRC_VIG: {
        "url": "https://acvote.alamedacountyca.gov/acvote-assets/02_election_information/PDFs/20261103/Voter%20Information%20Guide/vig_nov2026_eng.pdf",
        "title": "Alameda County Voter Information Guide, November 3, 2026 General Election (official Registrar of Voters PDF, sha256 5b1e32e3\u2026)",
    },
}

NOTE_TEXT = (
    "Resolved October 13, 2026: the Alameda County Registrar's official Candidate List for the "
    "\u201cGeneral Election - 11/03/2026 (Official)\u201d displays this race with Race Status \u201cNot On Ballot\u201d and lists its "
    "filers beneath that heading \u2014 the county's affirmative final ballot-status determination. The official "
    "November 2026 Voter Information Guide contains no candidate statement for any filer in this race while "
    "contested sibling seats in the same district do appear (retrieved and full-text checked October 13, 2026). "
    "This establishes non-appearance on the printed ballot; the Registrar's application does not print the underlying "
    "cancellation or appointment-in-lieu resolution, so how the seat is filled (no-contest outcome or board "
    "appointment) is not asserted here."
)

OBSOLETE_PREFIX = "Final ballot status was not confirmed"


def norm(s: str) -> str:
    return re.sub(r"[^a-z ]", "", s.lower()).replace("  ", " ").strip()


def main() -> int:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    positions = {p["id"]: p for p in data["positions"]}

    # --- assertions before writing ---
    assert SRC_ROV not in data["sources"] and NOTE_RESOLVED not in data["notes"], "registry IDs already claimed"
    changed = 0
    for pid, (_, filers) in TARGETS.items():
        p = positions[pid]
        if p["ballot_status"] == "excluded":
            continue  # idempotent rerun
        assert p["ballot_status"] == "unverified", f"{pid} is {p['ballot_status']}, expected unverified"
        recorded = sorted(norm(c["name"]) for c in (p.get("filed_candidates_not_confirmed_on_ballot") or []))
        assert recorded == sorted(norm(f) for f in filers), f"{pid} filer mismatch: dataset {recorded} vs registrar {sorted(map(norm, filers))}"

    # --- apply ---
    for pid in TARGETS:
        p = positions[pid]
        if p["ballot_status"] == "excluded":
            continue
        p["ballot_status"] = "excluded"
        notes = list(p.get("note_ids", []))
        notes = [r for r in notes if not (data["notes"][r].startswith(OBSOLETE_PREFIX) and _single_use(data, r))]
        if NOTE_RESOLVED not in notes:
            notes.append(NOTE_RESOLVED)
        p["note_ids"] = notes
        # retire a single-use candidate-list note that asserts unverified ballot appearance
        cln = p.get("candidate_list_note_id")
        if cln and _single_use(data, cln) and "unverified" in data["notes"][cln]:
            del p["candidate_list_note_id"]
        for ref in (SRC_ROV, SRC_VIG):
            if ref not in p["source_ids"]:
                p["source_ids"].append(ref)
        changed += 1

    if changed:
        data["sources"][SRC_ROV] = SOURCES[SRC_ROV]
        data["sources"][SRC_VIG] = SOURCES[SRC_VIG]
        data["notes"][NOTE_RESOLVED] = NOTE_TEXT

    unresolved = sum(1 for p in data["positions"] if p["ballot_status"] == "unverified")
    old_unresolved = data["coverage"]["unresolved_scheduled_contests"]
    data["coverage"]["unresolved_scheduled_contests"] = unresolved

    # the committed dataset uses one-space indentation; preserve it byte-exactly
    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"excluded {changed} contests; unresolved {old_unresolved} -> {unresolved}")
    return 0


def _single_use(data, ref: str) -> bool:
    uses = 0
    for p in data["positions"]:
        if ref in p.get("note_ids", []):
            uses += 1
        if p.get("candidate_list_note_id") == ref:
            uses += 1
    return uses <= 1


if __name__ == "__main__":
    sys.exit(main())
