"""Check references, counts, stable IDs, and embedded downloads using Python's standard library."""
import json
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from check_evidence import check_evidence
from check_published_endorsements import check_endorsements
from check_gaza_records import check_gaza_records

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = "2026-11-03_Bay_Area_Elections.json"
data = json.loads((ROOT / DATA_FILE).read_text(encoding="utf-8"))
schema = json.loads((ROOT / "elections.schema.json").read_text(encoding="utf-8"))
positions = data["positions"]
evidence_errors = check_evidence(data)
assert not evidence_errors, '\n'.join(evidence_errors)
endorsement_errors = check_endorsements(data)
assert not endorsement_errors, '\n'.join(endorsement_errors)
gaza_record_errors = check_gaza_records(data)
assert not gaza_record_errors, '\n'.join(gaza_record_errors)
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

federal_candidates = [c for p in positions if p['government_level'] == 'Federal'
                      for c in (p.get('candidates') or []) + (p.get('filed_candidates_not_confirmed_on_ballot') or [])]
# Nationwide federal candidacies added October 17, 2026 include minor-party candidates with no FEC filing;
# absence of an FEC record is recorded via a contest note (N907), never as zero fundraising.
for position in positions:
    if position['government_level'] != 'Federal':
        continue
    roster = (position.get('candidates') or []) + (position.get('filed_candidates_not_confirmed_on_ballot') or [])
    if any('fec' not in c for c in roster):
        assert 'N907' in (position.get('note_ids') or []), ('federal roster without FEC filings needs N907', position['id'])
fec_ids = []
for candidate in [c for c in federal_candidates if 'fec' in c]:
    f = candidate['fec']
    fec_ids.append(f['id'])
    assert data['sources'][f['source_id']]['url'].startswith('https://www.fec.gov/data/'), candidate['name']
    if f['receipts'] is None:
        assert 'from' not in f and 'through' not in f and f.get('note_id'), candidate['name']
    else:
        amount = Decimal(str(f['receipts']))
        assert amount >= 0 and amount == amount.quantize(Decimal('0.01')), candidate['name']
        assert date.fromisoformat(f['from']) <= date.fromisoformat(f['through']) <= date.fromisoformat(data['finance']['checked_on']), candidate['name']
        if int(f['from'][:4]) < data['finance']['cycle'] - 1:
            assert f.get('note_id'), 'Coverage outside the nominal cycle requires an explanatory note'
assert len(fec_ids) == len(set(fec_ids)), 'Unexpected duplicate FEC candidate ID'

# Independent expenditures: arithmetic, registry resolution and cycle conventions.
ie_cfg = data.get('ie_finance')
if ie_cfg is not None:
    assert ie_cfg['provider'] == 'FEC' and ie_cfg['metric'] == 'independent_expenditures'
    assert data['sources'][ie_cfg['source_id']]['url'].startswith('https://api.open.fec.gov/'), 'IE source must be the FEC API'
    registered = data.get('ie_spenders', {})
    for candidate in federal_candidates:
        ie = candidate.get('independent_expenditures')
        if ie is None:
            continue
        assert set(ie) <= {'browse_url', 'for_total', 'against_total', 'items'}, candidate['name']
        if ie.get('browse_url'):
            assert ie['browse_url'].startswith('https://www.fec.gov/data/independent-expenditures/'), candidate['name']
        for direction in ('for_total', 'against_total'):
            amount = Decimal(str(ie[direction]))
            assert amount >= 0 and amount == amount.quantize(Decimal('0.01')), (candidate['name'], direction)
        spenders = {}
        for item in ie['items']:
            assert item['amount'] > 0, candidate['name']
            assert item['direction'] in ('for', 'against'), candidate['name']
            assert item['spender_id'] in registered, (candidate['name'], item['spender_id'])
            key = (item['spender_id'], item['direction'])
            assert key not in spenders, 'Duplicate spender-direction row: ' + str(key)
            spenders[key] = Decimal(str(item['amount']))
        for direction, total_key in (('for', 'for_total'), ('against', 'against_total')):
            summed = sum((a for (s, d), a in spenders.items() if d == direction), Decimal('0'))
            assert Decimal(str(ie[total_key])) == summed.quantize(Decimal('0.01')), (candidate['name'], total_key)
        # A candidate with no activity carries an empty itemization and zero totals.
        if not ie['items']:
            assert ie['for_total'] == 0 and ie['against_total'] == 0, candidate['name']
    for spender_id, meta in registered.items():
        assert meta.get('name'), spender_id
        assert meta['source_url'].startswith('https://www.fec.gov/data/'), (spender_id, meta.get('source_url'))
state_categories = [p['office_category'] for p in positions if p['government_level'] == 'State']
assert state_categories[0] == 'State Senate'
assert max(i for i, c in enumerate(state_categories) if c == 'State Senate') < min(i for i, c in enumerate(state_categories) if c == 'State Assembly')
assert max(i for i, c in enumerate(state_categories) if c == 'State Assembly') < min(i for i, c in enumerate(state_categories) if c not in {'State Senate', 'State Assembly'})

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
    "printed_candidates_with_x_url": sum("x_url" in c for c in printed),
    "printed_candidates_with_secondary_x_url": sum("secondary_x_url" in c for c in printed),
    "printed_candidates_with_gaza_evidence": sum(bool(c.get("gaza_evidence")) for c in printed),
    "printed_candidates_with_gaza_voting_records": sum(bool(c.get("gaza_voting_records")) for c in printed),
    "printed_candidates_with_uscpr_grade": sum(bool(c.get("uscpr_grade")) for c in printed),
    "printed_candidates_with_gaza_platform": sum(bool(c.get("gaza_platform")) for c in printed),
    "printed_candidates_with_platform_positions": sum(bool(c.get("platform_positions")) for c in printed),
    "printed_candidates_with_endorsements": sum(bool(c.get("endorsements")) for c in printed),
    "printed_candidates_with_campaign_url": sum("campaign_url" in c for c in printed),
    "printed_candidates_with_independent_expenditures": sum(
        (c.get("independent_expenditures") or {}).get("for_total", 0)
        + (c.get("independent_expenditures") or {}).get("against_total", 0) > 0 for c in printed),
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
print(json.dumps({"passed": True, "positions": len(positions), "coverage": expected, "federal_candidates_with_fec": len(federal_candidates), "reported_fec_totals": sum(c['fec']['receipts'] is not None for c in federal_candidates)}, indent=2))
