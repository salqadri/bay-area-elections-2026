#!/usr/bin/env python3
"""Extract per-candidate evidence context from official captures for review.

For each contest in the match report (or a subset on the command line), print:
page title + first heading/date lines, then ±N chars around every roster-name
occurrence (first two hits). This is what a reviewer reads to confirm the list
is (a) this office/race, (b) November 3 2026 general election, (c) official.
"""
import html, json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from match_official import page_text, person_keys, norm_tokens  # noqa: E402

def contexts(text, name, width=170, max_hits=2):
    out = []
    t = norm_tokens(name)
    if not t: return out
    first, last = t[0], t[-1]
    up = re.sub(r'\s+', ' ', text.upper())
    for m in re.finditer(r'\b' + re.escape(last) + r'\b', up):
        a, b = max(0, m.start()-width), min(len(up), m.end()+width)
        seg = up[a:b]
        if first in seg[:width+40] or first in seg[width:]:
            out.append(re.sub(r'\s+', ' ', text[a:b]))
        if len(out) >= max_hits: break
    return out

def main():
    caps = json.load(open(f'{HERE}/captures.json'))
    rep = json.load(open(f'{HERE}/match_report.json'))
    wanted = set(sys.argv[1:]) or {k for k, v in rep.items() if v['status'] == 'checked' and v.get('found')}
    for pid in sorted(wanted):
        cap, r = caps.get(pid), rep.get(pid)
        if not cap or not cap.get('sha'): continue
        text = page_text(f"{HERE}/raw/{cap['path']}")
        up = re.sub(r'\s+', ' ', text.upper())
        title_m = re.search(r'<title[^>]*>(.*?)</title>', text, re.S | re.I)
        head = (title_m.group(1).strip() if title_m else '')[:160]
        date_line = next((up[m.start():m.start()+90] for m in re.finditer(r'NOVEMBER\s*3?,?\s*2026|GENERAL ELECTION', up)), '')
        print(f"\n===== {pid} {r['state']} {r['office']} | {cap.get('source_url','')[:100]}")
        print(f"TITLE: {head}")
        print(f"ELECTION MENTION: {date_line.strip()[:120]}")
        for name in r['found']:
            cs = contexts(text, name)
            print(f"  FOUND {name}: " + (cs[0][:230] if cs else 'CONTEXT LOST'))
        for name in r.get('missing', []):
            print(f"  MISSING {name}")

if __name__ == '__main__':
    main()
