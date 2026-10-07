"""Focused schema-keyword checks, not a certified general JSON Schema validator.

The runtime has no Draft 2020-12 validator package. This local checker implements
every assertion keyword actually used in elections.schema.json, checks the
current data, and exercises malformed examples. A downstream consumer should
also validate with a standard Draft 2020-12 implementation.
"""
import copy
import datetime
import json
import re
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((HERE / "elections.schema.json").read_text())
DATA = json.loads((HERE / "2026-11-03_Bay_Area_Elections.json").read_text())
ANNOTATIONS = {"$schema", "$comment", "title", "description", "$defs"}
ASSERTIONS = {"$ref", "type", "additionalProperties", "properties", "required", "minLength", "minItems", "maxItems", "uniqueItems", "items", "oneOf", "anyOf", "allOf", "not", "if", "then", "else", "const", "enum", "minimum", "pattern", "patternProperties", "propertyNames", "minProperties", "dependentRequired", "format"}
SEEN = set()


def scan_schema(node):
    if isinstance(node, bool):
        return
    unknown = set(node) - ANNOTATIONS - ASSERTIONS
    assert not unknown, f"Unsupported schema keywords: {unknown}"
    SEEN.update(node)
    for key in ["$defs", "properties", "patternProperties"]:
        for value in node.get(key, {}).values():
            scan_schema(value)
    for key in ["items", "propertyNames", "if", "then", "else", "not", "additionalProperties"]:
        if isinstance(node.get(key), (dict, bool)):
            scan_schema(node[key])
    for key in ["anyOf", "oneOf", "allOf"]:
        for value in node.get(key, []):
            scan_schema(value)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def istype(value, typename):
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }[typename]


def check(value, schema, path="$", root=SCHEMA):
    if isinstance(schema, bool):
        return [] if schema else [f"{path}: false schema"]
    errors = []
    if "$ref" in schema:
        target = root
        assert schema["$ref"].startswith("#/"), "Only internal refs are supported"
        for part in schema["$ref"][2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        errors.extend(check(value, target, path, root))
    for sub in schema.get("allOf", []):
        errors.extend(check(value, sub, path, root))
    for name in ["anyOf", "oneOf"]:
        if name in schema:
            valid = sum(not check(value, sub, path, root) for sub in schema[name])
            if (name == "anyOf" and valid == 0) or (name == "oneOf" and valid != 1):
                errors.append(f"{path}: {name} matched {valid} branches")
    if "not" in schema and not check(value, schema["not"], path, root):
        errors.append(f"{path}: matched prohibited schema")
    if "if" in schema:
        branch = "then" if not check(value, schema["if"], path, root) else "else"
        if branch in schema:
            errors.extend(check(value, schema[branch], path, root))
    if "const" in schema and canonical(value) != canonical(schema["const"]):
        errors.append(f"{path}: incorrect const")
    if "enum" in schema and canonical(value) not in {canonical(v) for v in schema["enum"]}:
        errors.append(f"{path}: value not in enum")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(istype(value, t) for t in types):
            errors.append(f"{path}: wrong type {type(value).__name__}, expected {types}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required {key}")
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path}: too few properties")
        properties = schema.get("properties", {})
        patterns = schema.get("patternProperties", {})
        for key, item in value.items():
            known = False
            if "propertyNames" in schema:
                errors.extend(check(key, schema["propertyNames"], path + "(key)", root))
            if key in properties:
                known = True
                errors.extend(check(item, properties[key], path + "." + key, root))
            for pattern, sub in patterns.items():
                if re.search(pattern, key):
                    known = True
                    errors.extend(check(item, sub, path + "." + key, root))
            if not known and "additionalProperties" in schema:
                errors.extend(check(item, schema["additionalProperties"], path + "." + key, root))
        for key, dependencies in schema.get("dependentRequired", {}).items():
            if key in value:
                for dependency in dependencies:
                    if dependency not in value:
                        errors.append(f"{path}: {key} requires {dependency}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: too many items")
        if schema.get("uniqueItems") and len(value) != len({canonical(v) for v in value}):
            errors.append(f"{path}: duplicate items")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(check(item, schema["items"], f"{path}[{index}]", root))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string too short")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: pattern mismatch")
        if schema.get("format") == "date":
            try:
                datetime.date.fromisoformat(value)
            except ValueError:
                errors.append(f"{path}: invalid calendar date")
        if schema.get("format") == "uri":
            # The schema restricts URI fields to HTTP(S); this validates the
            # applicable subset rather than the full RFC 3986 URI grammar.
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or re.search(r"\s", value):
                errors.append(f"{path}: invalid HTTP(S) URI")
    if istype(value, "number") and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: value below minimum")
    return errors


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

report = {
    "method": "Focused local checker implementing every assertion keyword used in the supplied schema, with HTTP(S) URI-subset checks. Not a standard or certified Draft 2020-12 validator.",
    "standard_validator_available": False,
    "dataset_schema_errors": 0,
    "positions_checked": len(DATA["positions"]),
    "schema_assertion_keywords_checked": sorted(SEEN & ASSERTIONS),
    "negative_cases": outcomes,
    "positive_cases": ["current dataset", "additional registered party", "additional researched county", "empty filtered view", "confirmed ballot with unverified roster", "retention ballot with unverified roster", "reported zero FEC receipts", "candidate x_url profile link", "candidate campaign_url website link"],
    "additional_validation_required": ["source/note/party reference targets", "unique position IDs and county names", "county registry membership", "coverage summary arithmetic", "standard Draft 2020-12 validator verification when available"],
}

print(json.dumps({"schema_errors": 0, "negative_cases_rejected": len(outcomes), "positive_cases_accepted": len(report["positive_cases"]), "assertion_keywords_checked": len(SEEN & ASSERTIONS), "positions": len(DATA["positions"])}, indent=2))
