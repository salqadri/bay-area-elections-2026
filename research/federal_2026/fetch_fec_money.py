#!/usr/bin/env python3
"""Fetch FEC 2026-cycle candidate-level totals + authorized committees for every
FEC-matched Senate candidacy in draft_positions.json. Cached to fec_money_cache.json
(keyed by candidate ID) so integration is offline and rerunnable."""
import json, subprocess, sys, time

K = open('/root/.cfg/fec_key').read().strip()
draft = json.load(open('draft_positions.json'))
ids = sorted({c['_fec_id'] for p in draft if p['office_category'] == 'U.S. Senate'
              for c in p['candidates'] if '_fec_id' in c})
try:
    cache = json.load(open('fec_money_cache.json'))
except FileNotFoundError:
    cache = {}

def get(url):
    r = subprocess.run(['curl', '-s', '-m', '45', url], capture_output=True, text=True)
    return json.loads(r.stdout) if r.stdout.strip() else None

for i, cid in enumerate(ids):
    if cid in cache and 'totals' in cache[cid] and 'committees' in cache[cid]:
        continue
    t = get(f'https://api.open.fec.gov/v1/candidate/{cid}/totals/?cycle=2026&api_key={K}')
    time.sleep(0.2)
    c = get(f'https://api.open.fec.gov/v1/candidate/{cid}/committees/?cycle=2026&per_page=100&api_key={K}')
    time.sleep(0.2)
    cache[cid] = {
        'totals': (t or {}).get('results') or [],
        'committees': sorted({r['committee_id'] for r in ((c or {}).get('results') or [])
                              if r.get('designation') in {'P', 'A'} and r.get('committee_id')}),
    }
    json.dump(cache, open('fec_money_cache.json', 'w'), indent=1)
    print(f"{i+1}/{len(ids)} {cid}", flush=True)
print('done; cached', len(cache))
