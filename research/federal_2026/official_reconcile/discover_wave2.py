#!/usr/bin/env python3
"""Wave 2 lead discovery: serper.dev searches for official November-2026
candidate-list sources for contests whose wave-1 lead was missing or useless
(fec.gov hub). Appends/refreshes entries in ../official_leads.json under a
'wave2_hits' key; capture step is separate (capture_wave2.py)."""
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open('/root/.cfg/serper_key').read().strip()
LEADS = f'{HERE}/../official_leads.json'

# pid -> (state, office, query)
TARGETS = {
 'US2026-007': ('GA', 'U.S. Senate', 'Georgia secretary of state certified candidate list November 3 2026 general election'),
 'US2026-043': ('GA', 'Governor', 'Georgia secretary of state candidate list November 2026 governor race site:ga.gov OR site:sos.ga.gov'),
 'US2026-015': ('MA', 'U.S. Senate', 'Massachusetts elections certified candidates November 3 2026 US Senate site:mass.gov'),
 'US2026-051': ('MA', 'Governor', 'Massachusetts secretary of the commonwealth candidate list November 2026 governor site:mass.gov'),
 'US2026-019': ('MT', 'U.S. Senate', 'Montana secretary of state candidate listing November 2026 US Senate site:mt.gov'),
 'US2026-028': ('RI', 'U.S. Senate', 'Rhode Island board of elections certified candidates November 3 2026 US Senate site:ri.gov'),
 'US2026-063': ('RI', 'Governor', 'Rhode Island board of elections candidate list November 2026 governor site:ri.gov'),
 'US2026-037': ('AK', 'Governor', 'Alaska division of elections candidate list November 3 2026 general election site:alaska.gov'),
 'US2026-002': ('AK', 'U.S. Senate', 'Alaska division of elections certified candidate list November 2026 US Senate site:alaska.gov'),
 'US2026-038': ('AZ', 'Governor', 'Arizona secretary of state candidate list November 3 2026 governor site:azsos.gov'),
 'US2026-048': ('KS', 'Governor', 'Kansas secretary of state candidate nomination list November 2026 governor site:ksos.gov OR site:ks.gov'),
 'US2026-011': ('KS', 'U.S. Senate', 'Kansas secretary of state 2026 general election candidate list US Senate site:ksos.gov OR site:ks.gov'),
 'US2026-055': ('NV', 'Governor', 'Nevada secretary of state qualified candidates November 3 2026 governor site:nvsos.gov'),
 'US2026-069': ('WI', 'Governor', 'Wisconsin GAB candidate list November 3 2026 nonpartisan election governor site:wisconsin.gov'),
}

def serper(q):
    body = json.dumps({'q': q, 'num': 10}).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request('https://google.serper.dev/search', data=body,
                headers={'X-API-KEY': KEY, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 4: raise
            time.sleep(2 ** attempt)

def main():
    leads = json.load(open(LEADS))
    only = set(sys.argv[1:])
    for pid, (st, office, q) in sorted(TARGETS.items()):
        if only and pid not in only: continue
        e = leads.setdefault(pid, {'state': st, 'office': office})
        if e.get('wave2_hits'): print(pid, 'already discovered'); continue
        d = serper(q)
        hits = [{'url': h['link'], 'title': h.get('title', '')} for h in d.get('organic', [])]
        gov = [h for h in hits if '.gov' in h['url']]
        e['wave2_query'] = q; e['wave2_checked_on'] = time.strftime('%Y-%m-%d')
        e['wave2_hits'] = gov[:6] or hits[:4]
        json.dump(leads, open(LEADS, 'w'), indent=1)
        print(pid, st, office, '->', len(e['wave2_hits']), 'gov hits |', (e['wave2_hits'][0]['url'] if e['wave2_hits'] else 'NONE')[:75])

if __name__ == '__main__':
    main()
