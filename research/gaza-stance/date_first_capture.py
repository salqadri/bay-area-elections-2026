#!/usr/bin/env python3
"""date_first_capture.py — last-resort dating via Wayback FIRST capture (CDX).

For evidence items where no publication date exists on the page itself (static
position pages, voter guides, JS-only posts): the first archive of a URL is an
UPPER bound on when that content existed. We record it as 'YYYY' or 'YYYY-MM'
(never a false-precision day) with date_source 'wayback_first_capture'.

Writes raw/<eid>.json per item and a summary at ledger/date_backfill_report.json.
Resumable: existing result files are skipped. Usage: python3 date_first_capture.py
"""
import json, os, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "raw", "firstcap")
LEDGER = os.path.join(ROOT, "evidence")

def get(u, t=60):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 research"})
    return urllib.request.urlopen(req, timeout=t).read().decode("utf-8", "ignore")

def undated():
    for f in sorted(os.listdir(LEDGER)):
        if not f.endswith(".json"): continue
        for it in json.load(open(os.path.join(LEDGER, f))):
            if not it.get("date"): yield it["id"], it["person"], it["url"]

def first_capture(url):
    q = urllib.parse.quote(url, safe="")
    cdx = (f"http://web.archive.org/cdx/search/cdx?url={q}"
           "&output=json&limit=1&fl=timestamp&filter=statuscode:200")
    last = None
    for attempt in range(5):
        try:
            j = json.loads(get(cdx))
            return j[1][0] if len(j) > 1 else ""      # empty string = no captures
        except Exception as e:
            last = repr(e)[:80]; time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"CDX failed after retries: {last}")

def main():
    os.makedirs(OUT, exist_ok=True)
    report = {}
    for eid, person, url in undated():
        path = os.path.join(OUT, eid + ".json")
        if os.path.exists(path):
            print(eid, "cached"); continue
        try:
            ts = first_capture(url)
        except Exception as e:
            ts = None; print(eid, "ERROR", str(e)[:80])
        json.dump({"eid": eid, "person": person, "url": url, "first_capture": ts},
                  open(path, "w"), indent=1)
        print(eid, "->", ts or "NO CAPTURE / ERROR")
        time.sleep(6)   # CDX politeness
    for f in sorted(os.listdir(OUT)):
        d = json.load(open(os.path.join(OUT, f)))
        report[d["eid"]] = d.get("first_capture")
    os.makedirs(os.path.join(ROOT, "ledger"), exist_ok=True)
    json.dump(report, open(os.path.join(ROOT, "ledger", "date_backfill_report.json"), "w"), indent=1)
    print("DONE", sum(1 for v in report.values() if v), "/", len(report), "have captures")

if __name__ == "__main__":
    main()
