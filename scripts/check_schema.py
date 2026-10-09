"""Focused schema regression suite; reusable validation lives in schema_validation.py."""
import copy
import json
from schema_validation import HERE, SCHEMA, SEEN, ASSERTIONS, scan_schema, check

DATA = json.loads((HERE / "2026-11-03_Bay_Area_Elections.json").read_text())

def mutated(mutator):
    value = copy.deepcopy(DATA)
    mutator(value)
    return value


scan_schema(SCHEMA)
errors = check(DATA, SCHEMA)
assert not errors, "Current dataset schema errors:\n" + "\n".join(errors[:40])


def first(data, predicate):
    return next(p for p in data["positions"] if predicate(p))


def add_party_to_nonpartisan(data):
    first(data, lambda p: not p["partisan"] and p["candidates"])["candidates"][0]["party"] = "D"


def provisional_as_printed(data):
    p = first(data, lambda p: p["ballot_status"] == "unverified")
    p["candidates"] = [{"name": "Example provisional filer"}]
    p["candidate_list_status"] = "complete"


negative_cases = {
    "verbose_party_string": lambda d: d["positions"][0]["candidates"][0].update(party="Democratic Party"),
    "incumbent_false_serialized": lambda d: d["positions"][0]["candidates"][0].update(incumbent=False),
    "wrong_assembly_prefix": lambda d: first(d, lambda p: p["office_category"] == "State Assembly").update(district_or_seat="District 18"),
    "wrong_congressional_prefix": lambda d: first(d, lambda p: p["office_category"] == "U.S. House").update(district_or_seat="AD-10"),
    "wrong_senate_prefix": lambda d: first(d, lambda p: p["office_category"] == "State Senate").update(district_or_seat="District 10"),
    "unknown_candidate_field": lambda d: d["positions"][0]["candidates"][0].update(unexpected="test"),
    "unknown_root_field": lambda d: d.update(unexpected="test"),
    "complete_null_roster": lambda d: first(d, lambda p: p["candidate_list_status"] == "complete").update(candidates=None),
    "unverified_roster_with_printed_candidates": lambda d: first(d, lambda p: p["candidate_list_status"] == "complete").update(candidate_list_status="unverified"),
    "provisional_roster_mislabeled_printed": provisional_as_printed,
    "nonpartisan_party": add_party_to_nonpartisan,
    "ocd_id_without_valid_status": lambda d: d["positions"][0].update(ocd_id_status="unverified"),
    "retention_multiple_candidates": lambda d: first(d, lambda p: p["election_type"] == "retention")["candidates"].append({"name": "Example second judge"}),
    "null_url_instead_of_omission": lambda d: d["positions"][0].update(ballotpedia_url=None),
    "bad_source_reference_syntax": lambda d: d["positions"][0].update(source_ids=["123"]),
    "invalid_calendar_date": lambda d: d["election"].update(date="2026-02-30"),
    "bad_fec_candidate_id": lambda d: d['positions'][0]['candidates'][0]['fec'].update(id='C00462697'),
    "negative_fec_receipts": lambda d: d['positions'][0]['candidates'][0]['fec'].update(receipts=-1),
    "fec_amount_as_string": lambda d: d['positions'][0]['candidates'][0]['fec'].update(receipts='$100'),
    "fec_amount_missing_cutoff": lambda d: d['positions'][0]['candidates'][0]['fec'].pop('through'),
    "fec_unknown_with_coverage_dates": lambda d: d['positions'][0]['candidates'][0]['fec'].update(receipts=None),
    "fec_unavailable_without_note": lambda d: next(c for p in d['positions'] for c in p['candidates'] or [] if c.get('fec', {}).get('receipts', 1) is None)['fec'].pop('note_id'),
    "x_url_wrong_host": lambda d: d["positions"][0]["candidates"][0].update(x_url="https://twitter.com/someone"),
    "x_url_with_path_noise": lambda d: d["positions"][0]["candidates"][0].update(x_url="https://x.com/someone/home"),
    "x_url_invalid_characters": lambda d: d["positions"][0]["candidates"][0].update(x_url="https://x.com/not a handle"),
    "campaign_url_no_scheme": lambda d: d["positions"][0]["candidates"][0].update(campaign_url="example-campaign.com"),
    "campaign_url_javascript": lambda d: d["positions"][0]["candidates"][0].update(campaign_url="javascript:alert(1)"),
    "secondary_x_url_wrong_host": lambda d: d["positions"][0]["candidates"][0].update(secondary_x_url="https://twitter.com/someone"),
    "gaza_evidence_missing_checked_on": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9001","url":"https://example.com/a","summary":"Statement about the ceasefire vote.","dimension":"actions_votes"}]),
    "gaza_evidence_bad_dimension": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9002","date":"2025-06-01","url":"https://example.com/a","summary":"Statement about the ceasefire vote.","dimension":"grade_a","checked_on":"2026-10-08"}]),
    "gaza_evidence_bad_id": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"X-1","date":"2025-06-01","url":"https://example.com/a","summary":"Statement about the ceasefire vote.","dimension":"actions_votes","checked_on":"2026-10-08"}]),
    "gaza_evidence_missing_date": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9003","url":"https://example.com/a","summary":"Statement about the ceasefire vote.","dimension":"actions_votes","checked_on":"2026-10-08"}]),
    "gaza_evidence_bad_date_format": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9004","date":"June 2025","url":"https://example.com/a","summary":"Statement about the ceasefire vote.","dimension":"actions_votes","checked_on":"2026-10-08"}]),
    "gaza_evidence_year_zero": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9009","date":"0000","url":"https://example.com/a","summary":"Candidate supported a bilateral ceasefire.","dimension":"actions_votes","checked_on":"2026-10-08"}]),
    "gaza_evidence_impossible_month": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9005","date":"2026-13","url":"https://example.com/a","summary":"Statement about the ceasefire vote.","dimension":"actions_votes","checked_on":"2026-10-08"}]),
    "gaza_evidence_impossible_day": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9006","date":"2026-02-30","url":"https://example.com/a","summary":"Statement about the ceasefire vote.","dimension":"actions_votes","checked_on":"2026-10-08"}]),
    "gaza_evidence_impossible_checked_on": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9007","date":"2026-02-01","url":"https://example.com/a","summary":"Statement about the ceasefire vote.","dimension":"actions_votes","checked_on":"2026-02-30"}]),
    "endorsement_bad_relation": lambda d: d["positions"][0]["candidates"][0].update(endorsements=[{"endorser":"Example Party","relation":"will-endorse","phase":"general","url":"https://example.com/e","checked_on":"2026-10-09"}]),
    "endorsement_missing_url": lambda d: d["positions"][0]["candidates"][0].update(endorsements=[{"endorser":"Example Party","relation":"endorsed","phase":"general","checked_on":"2026-10-09"}]),
    "endorsement_rating_is_not_formal_endorsement": lambda d: d["positions"][0]["candidates"][0].update(endorsements=[{"endorser":"Example Group","relation":"endorsed","rating":"Support","phase":"general","url":"https://example.com/e","checked_on":"2026-10-09","note_id":"N286","verification":"endorser_statement"}]),
    "endorsement_secondary_report_needs_note": lambda d: d["positions"][0]["candidates"][0].update(endorsements=[{"endorser":"Example Group","relation":"endorsed","verification":"reported","phase":"general","url":"https://example.com/e","checked_on":"2026-10-09"}]),
    "endorsement_opposition_requires_provenance": lambda d: d["positions"][0]["candidates"][0].update(endorsements=[{"endorser":"Example Group","relation":"opposed","phase":"general","url":"https://example.com/e","checked_on":"2026-10-09"}]),
    "endorsement_shared_flag_must_be_true": lambda d: d["positions"][0]["candidates"][0].update(endorsements=[{"endorser":"Example Group","relation":"endorsed","shared":False,"phase":"general","url":"https://example.com/e","checked_on":"2026-10-09"}]),
    "endorsement_preferred_cannot_be_joint_endorsement": lambda d: d["positions"][0]["candidates"][0].update(endorsements=[{"endorser":"Example Group","relation":"preferred","shared":True,"verification":"endorser_statement","note_id":"N295","phase":"general","url":"https://example.com/e","checked_on":"2026-10-09"}]),
    "endorsement_unknown_provenance": lambda d: d["positions"][0]["candidates"][0].update(endorsements=[{"endorser":"Example Group","relation":"endorsed","verification":"probably","phase":"general","url":"https://example.com/e","checked_on":"2026-10-09"}]),
    "gaza_evidence_unknown_date_method": lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9008","date":"2026-02-01","url":"https://example.com/a","summary":"Statement about the ceasefire vote.","dimension":"actions_votes","checked_on":"2026-10-08","date_method":"google_guess"}]),
}
outcomes = []
for label, mutate in negative_cases.items():
    result = check(mutated(mutate), SCHEMA)
    assert result, f"Negative case was accepted: {label}"
    outcomes.append({"case": label, "rejected": True, "first_error": result[0]})

future_party = mutated(lambda d: (d["codes"]["party"].update(L="Libertarian Party"), d["positions"][0]["candidates"][0].update(party="L")))
assert not check(future_party, SCHEMA), "Future registered party code must remain valid"
future_county = mutated(lambda d: (d["election"]["counties_in_scope"].append({"name": "Marin", "ocd_division_id": "ocd-division/country:us/state:ca/county:marin"}), d["positions"][0]["counties"].append("Marin")))
assert not check(future_county, SCHEMA), "Additional researched county must remain valid"
empty_filter = mutated(lambda d: d.update(positions=[]))
assert not check(empty_filter, SCHEMA), "Empty filtered view is structurally valid; counts are checked separately"
confirmed_unverified_roster = mutated(lambda d: first(d, lambda p: p["ballot_status"] == "confirmed" and p["election_type"] != "retention").update(candidate_list_status="unverified", candidates=None))
assert not check(confirmed_unverified_roster, SCHEMA), "Confirmed ballot appearance must permit an explicitly unverified candidate roster"
retention_unverified_roster = mutated(lambda d: first(d, lambda p: p["election_type"] == "retention").update(candidate_list_status="unverified", candidates=None))
assert not check(retention_unverified_roster, SCHEMA), "A retention contest may also have an explicitly unverified roster"
reported_zero = mutated(lambda d: d['positions'][0]['candidates'][0]['fec'].update(receipts=0))
assert not check(reported_zero, SCHEMA), 'A reported zero is valid and distinct from unavailable receipts'
verified_x_url = mutated(lambda d: d["positions"][0]["candidates"][0].update(x_url="https://x.com/Example_Cand"))
assert not check(verified_x_url, SCHEMA), "A verified x.com profile URL must be a valid candidate field"
verified_campaign_url = mutated(lambda d: d["positions"][0]["candidates"][0].update(campaign_url="https://example-campaign.com/2026"))
assert not check(verified_campaign_url, SCHEMA), "A verified campaign website URL must be a valid candidate field"
secondary_x = mutated(lambda d: d["positions"][0]["candidates"][0].update(x_url="https://x.com/RepExample", secondary_x_url="https://x.com/ExamplePerson"))
assert not check(secondary_x, SCHEMA), "A verified second X account must be a valid candidate field"
gaza_ev = mutated(lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9100","date":"2025-06-01","url":"https://example.com/statement","summary":"Candidate called for an immediate ceasefire in a public statement.","quote":"we need a ceasefire now","dimension":"actions_votes","source_kind":"news","checked_on":"2026-10-08"}]))
assert not check(gaza_ev, SCHEMA), "A dated Gaza evidence item must be a valid candidate field"
endorsement_ok = mutated(lambda d: d["positions"][0]["candidates"][0].update(endorsements=[{"endorser":"Example County Democratic Party","kind":"party","relation":"endorsed","phase":"general","url":"https://example.com/endorsements","checked_on":"2026-10-09","quote":"Jane Doe"}]))
assert not check(endorsement_ok, SCHEMA), "A cited current-cycle endorsement record must be a valid candidate field"
support_ok = mutated(lambda d: d['positions'][0]['candidates'][0].update(endorsements=[{'endorser':'Example Group','relation':'supported','rating':'Strong Support','phase':'unspecified','url':'https://example.com/e','checked_on':'2026-10-09','verification':'endorser_statement','note_id':'N292'}]))
assert not check(support_ok, SCHEMA), 'A source support rating must remain distinct from an endorsement'
for relation in ['preferred', 'opposed']:
    recommendation_ok = mutated(lambda d: d['positions'][0]['candidates'][0].update(endorsements=[{'endorser':'Example Group','relation':relation,'phase':'unspecified','url':'https://example.com/e','checked_on':'2026-10-09','verification':'endorser_statement','note_id':'N295'}]))
    assert not check(recommendation_ok, SCHEMA), 'Preference and opposition must retain distinct relations'

gaza_ev_dated = mutated(lambda d: d["positions"][0]["candidates"][0].update(gaza_evidence=[{"id":"GE-9101","date":"2025-06","url":"https://example.com/statement","summary":"Candidate called for an immediate ceasefire in a public statement.","dimension":"actions_votes","checked_on":"2026-10-08","date_method":"wayback_first_capture","date_note":"Earliest Wayback capture containing the claim; month is an upper bound."}]))
assert not check(gaza_ev_dated, SCHEMA), "Partial dates with explicit dating method and note must remain valid"


# Guide snapshots are intentionally different from dated historical statements.
guide = next(r for p in DATA['positions'] for c in p.get('candidates') or [] for r in c.get('gaza_evidence', []) if r.get('date_method') == 'source_observed')
assert not check(guide, SCHEMA['$defs']['stanceEvidence'])
for key in ['date_note', 'source_kind']:
    bad = {k: v for k, v in guide.items() if k != key}
    assert check(bad, SCHEMA['$defs']['stanceEvidence'])
    outcomes.append({'case': 'guide_observation_missing_' + key, 'rejected': True})
assert check({**guide, 'date': '2026-10'}, SCHEMA['$defs']['stanceEvidence'])
outcomes.append({'case': 'guide_observation_partial_date', 'rejected': True})
ally = next(r for p in DATA['positions'] for c in p.get('candidates') or [] for r in c.get('endorsements', []) if r.get('rating') == 'Ally')
assert not check(ally, SCHEMA['$defs']['endorsementRecord'])
assert check({**ally, 'relation': 'endorsed'}, SCHEMA['$defs']['endorsementRecord'])
outcomes.append({'case': 'ally_promoted_to_formal_endorsement', 'rejected': True})

report = {
    "method": "Focused local checker implementing every assertion keyword used in the supplied schema, with HTTP(S) URI-subset checks. Not a standard or certified Draft 2020-12 validator.",
    "standard_validator_available": False,
    "dataset_schema_errors": 0,
    "positions_checked": len(DATA["positions"]),
    "schema_assertion_keywords_checked": sorted(SEEN & ASSERTIONS),
    "negative_cases": outcomes,
    "positive_cases": ["current dataset", "additional registered party", "additional researched county", "empty filtered view", "confirmed ballot with unverified roster", "retention ballot with unverified roster", "reported zero FEC receipts", "candidate x_url profile link", "candidate campaign_url website link", "candidate secondary_x_url second account", "candidate gaza_evidence dated item", "gaza evidence partial date with dating method and note", "candidate endorsement record with source page", "source support rating with provenance and note", "source preference", "source opposition", "source Ally classification", "dated guide observation"],
    "additional_validation_required": ["source/note/party reference targets", "unique position IDs and county names", "county registry membership", "coverage summary arithmetic", "standard Draft 2020-12 validator verification when available"],
}

print(json.dumps({"schema_errors": 0, "negative_cases_rejected": len(outcomes), "positive_cases_accepted": len(report["positive_cases"]), "assertion_keywords_checked": len(SEEN & ASSERTIONS), "positions": len(DATA["positions"])}, indent=2))
