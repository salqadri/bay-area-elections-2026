#!/usr/bin/env python3
"""backfill_dates.py — fill missing dates on already-collected evidence items.

Deterministic only (see date_resolvers): X snowflake ids, page metadata, Wayback
metadata. Items that stay null genuinely have no machine-readable publication
date; they are reported so a human can date them from the source text.
Records `date_source` in the ledger for provenance (merge drops it — the dataset
schema has no such field). Resumable: items with a date are never touched.

Usage: python3 backfill_dates.py [--dry-run]
"""
import glob, json, os, sys, time
from date_resolvers import resolve_date

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")

def main(dry=False):
    stats = {"filled": 0, "still_null": 0, "already": 0}
    for f in sorted(glob.glob(os.path.join(LEDGER, "*.json"))):
        items = json.load(open(f))
        changed = False
        for it in items:
            if it.get("date"): stats["already"] += 1; continue
            date, how = resolve_date(it["url"])
            if date:
                it["date"] = date; it["date_source"] = how; changed = True
                stats["filled"] += 1
                print(f"  {it['id']} {it['person'][:24]:<24} -> {date} ({how})")
            else:
                stats["still_null"] += 1
                it["date_source"] = "unresolved"
                changed = True
                print(f"  {it['id']} {it['person'][:24]:<24} -> STILL NULL  {it['url'][:80]}")
            time.sleep(0.4)   # politeness spacing for metadata fetches
        if changed and not dry:
            tmp = f + ".tmp"; json.dump(items, open(tmp, "w"), indent=1); os.replace(tmp, f)
    print(json.dumps(stats))

if __name__ == "__main__":
    main("--dry-run" in sys.argv)
