#!/usr/bin/env python3
"""merge_gaza_evidence.py — copy ledger evidence into the election dataset (schema 1.9).

Matches each evidence person key (norm_name|party) to printed/provisional/write-in
candidates across ALL counties in the dataset (statewide candidates appear once per
person; research is keyed by person, not county). Existing gaza_evidence on a
candidate is replaced wholesale from the ledger (ledger is source of truth), deduped
by URL. Recomputes coverage.printed_candidates_with_gaza_evidence.

Usage: python3 merge_gaza_evidence.py [--dry-run]
"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xhunt2 import norm_name

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "2026-11-03_Bay_Area_Elections.json")
DATE_RE = re.compile(r"^\d{4}(-\d{2})?(-\d{2})?$")

def load_ledger():
    people = {}
    for f in glob.glob(os.path.join(LEDGER, "*.json")):
        for e in json.load(open(f)):
            k = norm_name(e["person"]) + "|"  # party unknown from ledger file name; match by name only
            people.setdefault(norm_name(e["person"]), []).append(e)
    return people

def clean_item(e):
    # date is mandatory (schema 1.10): an undated item could misplace a stance in time
    if not (e.get("date") and DATE_RE.match(str(e["date"]))):
        print(f"SKIP {e['id']} ({e['person']}): no valid date — resolve in the ledger first"); return None
    it = {"id": e["id"], "url": e["url"], "summary": e["summary"][:240], "date": str(e["date"]),
          "dimension": e.get("dimension", "other"), "checked_on": e["checked_on"]}
    if e.get("quote"): it["quote"] = e["quote"][:300]
    if e.get("source_kind"): it["source_kind"] = e["source_kind"][:40]
    if e.get("date_method") in ("source_stated","page_metadata","x_snowflake","wayback_first_capture","event_recorded"):
        it["date_method"] = e["date_method"]
    if e.get("date_note"): it["date_note"] = str(e["date_note"])[:240]
    return it

def main(dry=False):
    ledger = load_ledger()
    data = json.load(open(DATA))
    applied_people, applied_entries = set(), 0
    for p in data["positions"]:
        rosters = [p.get("candidates") or [],
                   p.get("filed_candidates_not_confirmed_on_ballot") or [],
                   p.get("write_in_candidates") or []]
        for roster in rosters:
            for c in roster:
                rows = ledger.get(norm_name(c["name"]))
                if not rows:
                    # ledger is the source of truth: an item removed/quarantined there
                    # must disappear from the dataset on the next merge too.
                    c.pop("gaza_evidence", None)
                    continue
                seen, items = set(), []
                for e in sorted(rows, key=lambda x: (x.get("date") or "0000", x["id"])):
                    if e["url"] in seen: continue
                    seen.add(e["url"])
                    item = clean_item(e)
                    if item: items.append(item)
                if not items: continue
                c["gaza_evidence"] = items
                applied_people.add(norm_name(c["name"])); applied_entries += 1
    printed = [c for p in data["positions"] for c in (p.get("candidates") or [])]
    n_ev = sum(bool(c.get("gaza_evidence")) for c in printed)
    data["coverage"]["printed_candidates_with_gaza_evidence"] = n_ev
    if dry:
        print(json.dumps({"people_matched": len(applied_people), "entries": applied_entries,
                          "printed_with_evidence": n_ev}, indent=2)); return
    json.dump(data, open(DATA, "w"), indent=2, ensure_ascii=False)
    open(DATA, "a").write("\n")
    print(json.dumps({"people_matched": len(applied_people), "entries_updated": applied_entries,
                      "printed_with_gaza_evidence": n_ev}, indent=2))

if __name__ == "__main__":
    main("--dry-run" in sys.argv)
