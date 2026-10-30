#!/usr/bin/env python3
"""Sweep every candidate campaign site for policy/issues subpages that the
homepage-only scan missed (the Ritesh Tandon class of miss: stance text on a
sitemap-only subpage while the homepage carries no conflict keyword; plus the
legacy garbled-capture bug in xhunt2.http, fixed 2026-10-30).

Mechanical and LLM-free: for each campaign URL run campaign_policy_pages()
and diff any keyword-bearing page URLs against what is already in that
person's evidence ledger. Checkpointed; safe to resume. Output:
gap-review-2026-10-30/policy-page-sweep.json with the impacted candidates.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gaza_research as g
from validate_evidence import normalize_url

ROOT = g.ROOT
OUT_DIR = os.path.join(ROOT, "gap-review-2026-10-30")
OUT = os.path.join(OUT_DIR, "policy-page-sweep.json")
DONE = os.path.join(OUT_DIR, "sweep-progress.json")


def all_people():
    data = json.load(open(g.DATA))
    people = {}
    for p in data["positions"]:
        nationwide = not p.get("counties")
        if nationwide and not (p.get("office_category") in ("U.S. Senate", "U.S. House")
                               or p.get("office") == "Governor"):
            pass  # collector scope, but sweep every site regardless of office
        roster = list(p.get("candidates") or [])
        if nationwide:
            roster += p.get("filed_candidates_not_confirmed_on_ballot") or []
        for c in roster:
            u = c.get("campaign_url")
            if not u:
                continue
            k = g.norm_name(c["name"]) + "|" + str(c.get("party"))
            people.setdefault(k, {"name": c["name"], "party": c.get("party"), "url": u})
    return people


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    people = all_people()
    done = json.load(open(DONE)) if os.path.exists(DONE) else {}
    findings = json.load(open(OUT)) if os.path.exists(OUT) else {}
    print(f"{len(people)} unique campaign-site candidates; {len(done)} already swept", flush=True)
    for i, (k, ent) in enumerate(sorted(people.items()), 1):
        if k in done:
            continue
        try:
            pages = g.campaign_policy_pages(ent["url"])
        except Exception as e:
            pages = []
            print(f"  [err] {k}: {repr(e)[:80]}", flush=True)
        have = set()
        ev_p = g.ev_path(k)
        if os.path.exists(ev_p):
            have = {normalize_url(e["url"]) for e in json.load(open(ev_p))}
        new = [{"url": u, "kw_excerpt": t[:300]} for u, t in pages
               if normalize_url(u) not in have]
        done[k] = {"url": ent["url"], "pages_found": len(pages), "new_pages": len(new)}
        if new:
            findings[k] = {"name": ent["name"], "party": ent["party"], "url": ent["url"], "new_pages": new}
        if i % 10 == 0:
            json.dump(done, open(DONE, "w"), indent=1)
            json.dump(findings, open(OUT, "w"), indent=1)
            print(f"  [{i}/{len(people)}] {len(findings)} impacted so far", flush=True)
        time.sleep(0.15)
    json.dump(done, open(DONE, "w"), indent=1)
    json.dump(findings, open(OUT, "w"), indent=1)
    print(f"DONE: swept {len(done)}; {len(findings)} candidates have new KW-bearing policy pages", flush=True)


if __name__ == "__main__":
    main()
