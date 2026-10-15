#!/usr/bin/env python3
"""merge_subagent_evidence.py — append agent-produced evidence items into the ledger.

Usage: python3 merge_subagent_evidence.py items1.json [items2.json ...]
Input: JSON array of {name, party, date, url, summary, quote?, dimension}.
Dedupes by URL against each person's existing file (same rules as gaza_research).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gaza_research import add_evidence, load_state, save_state, log
from xhunt2 import norm_name

def main(paths):
    total_added = 0
    for p in paths:
        items = json.load(open(p))
        if isinstance(items, dict): items = items.get("items") or []
        by_person = {}
        for it in items:
            if not isinstance(it, dict) or not it.get("name"): continue
            k = norm_name(it["name"]) + "|" + str(it.get("party"))
            by_person.setdefault(k, []).append(it)
        for k, rows in by_person.items():
            conv = [{"person": r["name"], "date": (str(r.get("date") or "") or None),
                     "url": r.get("url", ""), "summary": r.get("summary", ""),
                     "quote": r.get("quote"), "dimension": r.get("dimension", "other"),
                     "source_kind": "agent"} for r in rows]
            added = add_evidence(k, conv)
            total_added += added
            log(f"  {k}: +{added} agent items ({len(rows)} offered)")
    print(json.dumps({"total_added": total_added}))

if __name__ == "__main__":
    main(sys.argv[1:])
