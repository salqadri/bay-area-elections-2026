"""Check references, counts, stable IDs, and embedded downloads using Python's standard library."""
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = "2026-11-03_Bay_Area_Elections.json"
data = json.loads((ROOT / DATA_FILE).read_text(encoding="utf-8"))
schema = json.loads((ROOT / "elections.schema.json").read_text(encoding="utf-8"))
positions = data["positions"]
ids = [p["id"] for p in positions]
assert len(ids) == len(set(ids)), "Duplicate position IDs"
counties = [c["name"] for c in data["election"]["counties_in_scope"]]
assert len(counties) == len(set(counties)), "Duplicate counties in scope"


def walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("source_ids"):
                assert all(i in data["sources"] for i in item), (key, item)
            elif key.endswith("source_id"):
                assert item in data["sources"], (key, item)
            elif key.endswith("note_ids"):
                assert all(i in data["notes"] for i in item), (key, item)
            elif key.endswith("note_id"):
                assert item in data["notes"], (key, item)
            walk(item)
    elif isinstance(value, list):
        for item in value:
            walk(item)


walk(data)
for position in positions:
    assert len(position["counties"]) == len(set(position["counties"])), position["id"]
    assert set(position["counties"]) <= set(counties), position["id"]
    for roster in ("candidates", "filed_candidates_not_confirmed_on_ballot", "qualified_write_in_candidates"):
        for candidate in position.get(roster) or []:
            if "party" in candidate:
                assert candidate["party"] in data["codes"]["party"], candidate
            assert candidate.get("incumbent", True) is True, candidate

confirmed = [p for p in positions if p["ballot_status"] == "confirmed"]
printed = [candidate for p in positions for candidate in (p.get("candidates") or [])]
expected = {
    "confirmed_contests": len(confirmed),
    "confirmed_seats": sum(p["seats"] or 0 for p in confirmed),
    "unresolved_scheduled_contests": sum(p["ballot_status"] == "unverified" for p in positions),
    "printed_candidate_entries": len(printed),
    "confirmed_contests_missing_candidate_rosters": sum(p["candidate_list_status"] != "complete" for p in confirmed),
    "positions_with_ocd_division_id": sum("ocd_division_id" in p for p in positions),
    "positions_with_ballotpedia_url": sum("ballotpedia_url" in p for p in positions),
    "printed_candidates_with_ballotpedia_url": sum("ballotpedia_url" in c for c in printed),
}
for key, value in expected.items():
    assert data["coverage"][key] == value, (key, data["coverage"][key], value)


class EmbeddedJSON(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.values = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type") == "application/json":
            self.current = attrs["id"]
            self.values[self.current] = ""

    def handle_endtag(self, tag):
        if tag == "script":
            self.current = None

    def handle_data(self, value):
        if self.current:
            self.values[self.current] += value


html = EmbeddedJSON()
html.feed((ROOT / "index.html").read_text(encoding="utf-8"))
assert json.loads(html.values["election-data"]) == data, "Embedded dataset differs"
assert json.loads(html.values["election-schema"]) == schema, "Embedded schema differs"
print(json.dumps({"passed": True, "positions": len(positions), "coverage": expected}, indent=2))
