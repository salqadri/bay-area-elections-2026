#!/usr/bin/env python3
"""date_content_first_seen.py — date static pages by when their CLAIMED CONTENT
first appears in Wayback captures (binary search over CDX capture list).

The first capture of a URL only bounds the page's existence; content can be
edited in later. We binary-search for the earliest capture whose text contains
the claim keywords, and record that capture's YYYY-MM as an upper bound on the
statement date (date_source: wayback_content_first_seen). Never invents a day.

Usage: python3 date_content_first_seen.py <eid> <url> "<kw1 kw2 ...>" [--apply]
"""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "raw", "firstcap")

def get(u, t=60):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 research"})
    return urllib.request.urlopen(req, timeout=t).read(1200000).decode("utf-8", "ignore")

def cdx_all(url):
    q = urllib.parse.quote(url, safe="")
    r = f"http://web.archive.org/cdx/search/cdx?url={q}&output=json&fl=timestamp,statuscode&filter=statuscode:200"
    for attempt in range(5):
        try: return [row[0] for row in json.loads(get(r))[1:]]
        except Exception as e: time.sleep(20 * (attempt + 1))
    raise RuntimeError("cdx failed")

def capture_has(url, ts, kws):
    for attempt in range(3):
        try:
            h = get(f"http://web.archive.org/web/{ts}/{url}")
            t = re.sub(r"<[^>]+>", " ", h).lower()
            return all(k.lower() in t for k in kws)
        except Exception: time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"snapshot {ts} unfetchable")

def main():
    eid, url, kwstr = sys.argv[1], sys.argv[2], sys.argv[3]
    apply = "--apply" in sys.argv
    kws = kwstr.split()
    caps = cdx_all(url)
    print(eid, f"{len(caps)} captures", caps[0], "->", caps[-1])
    if not caps: return
    if capture_has(url, caps[0], kws):          # earliest already has it
        hit = caps[0]
    elif not capture_has(url, caps[-1], kws):   # even latest lacks it -> unresolved
        print(eid, "content never archived with keywords"); return
    else:                                        # binary search first True
        lo, hi = 0, len(caps) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            time.sleep(5)
            if capture_has(url, caps[mid], kws): hi = mid
            else: lo = mid + 1
        hit = caps[lo]
    ym = f"{hit[:4]}-{hit[4:6]}"
    print(eid, "content first seen in capture", hit, "-> date", ym)
    if apply:
        led = os.path.join(ROOT, "evidence")
        for f in os.listdir(led):
            if not f.endswith(".json"): continue
            items = json.load(open(os.path.join(led, f)))
            if any(i["id"] == eid for i in items):
                for i in items:
                    if i["id"] == eid:
                        i["date"] = ym; i["date_source"] = "wayback_content_first_seen@" + hit
                json.dump(items, open(os.path.join(led, f), "w"), indent=1)
                print(eid, "APPLIED to", f)

if __name__ == "__main__":
    main()
