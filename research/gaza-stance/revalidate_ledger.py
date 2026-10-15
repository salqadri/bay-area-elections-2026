#!/usr/bin/env python3
"""revalidate_ledger.py — run acceptance rules over ALL existing evidence items.

Quarantines hard failures (with reason) into ledger/undated_quarantine.json and
writes soft findings to ledger/review_flags.json without removing the item.
Idempotent: re-running only re-flags what is still in the ledger.

Usage: python3 revalidate_ledger.py [--dry-run]
"""
import glob, hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_evidence import check as ev_check, person_contexts

def cached_page_text(url):
    """Raw page text captured by the pipeline (raw/pages/<sha1[:16]>.txt)."""
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    f = os.path.join(ROOT, "raw", "pages", h + ".txt")
    try: return open(f).read() or None
    except Exception: return None

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "2026-11-03_Bay_Area_Elections.json")
TODAY = time.strftime("%Y-%m-%d")

def main(dry=False):
    ctx = person_contexts(json.load(open(DATA)))
    qpath = os.path.join(ROOT, "ledger", "undated_quarantine.json")
    rpath = os.path.join(ROOT, "ledger", "review_flags.json")
    quar = json.load(open(qpath)) if os.path.exists(qpath) else []
    rev = json.load(open(rpath)) if os.path.exists(rpath) else []
    flagged_urls = {(r["person"], r["url"]) for r in rev}
    removed, soft_n, kept = 0, 0, 0
    for f in glob.glob(os.path.join(ROOT, "evidence", "*.json")):
        items = json.load(open(f)); keep = []
        for e in items:
            ok, hard, soft = ev_check(e, ctx.get(e["person"]), context_text=cached_page_text(e["url"]))
            if not ok:
                quar.append({"person": e["person"], "url": e["url"],
                             "summary": (e.get("summary") or "")[:240], "skipped_on": TODAY,
                             "reason": "revalidation: " + "; ".join(hard)})
                removed += 1
                print(f"QUARANTINE {e['id']} ({e['person']}): {'; '.join(hard)}")
            else:
                keep.append(e); kept += 1
                for s in soft:
                    if (e["person"], e["url"]) not in flagged_urls:
                        rev.append({"person": e["person"], "url": e["url"], "date": e.get("date"),
                                    "flag": s, "summary": (e.get("summary") or "")[:200], "on": TODAY})
                        flagged_urls.add((e["person"], e["url"])); soft_n += 1
        if not dry and len(keep) != len(items):
            json.dump(keep, open(f, "w"), indent=1)
    print(f"\nkept {kept}, quarantined {removed}, new review flags {soft_n}")
    if not dry:
        json.dump(quar, open(qpath, "w"), indent=1)
        json.dump(rev, open(rpath, "w"), indent=1)
        print(f"quarantine total {len(quar)}; review queue total {len(rev)}")

if __name__ == "__main__":
    main("--dry-run" in sys.argv)
