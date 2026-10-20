#!/usr/bin/env python3
"""Strict office-block verdicts: locate the OFFICE section for each contest's
capture and test whether every compiled-roster ballot name appears inside that
block (up to the next office heading). Loose anywhere-on-page matching produced
nav-chrome false positives; only office-block containment can support a flip.

Output: verdicts.json with per-contest {office_block_found, found[], missing[],
extra_candidates_in_block_hint, block_preview}. Review before applying anything.
"""
import json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from match_official import page_text, norm_tokens  # noqa: E402

DATASET = '/workspace/bay-area-elections-2026/2026-11-03_Bay_Area_Elections.json'

OFFICE_PATTERNS = {
    'U.S. Senate': r'\b(?:FOR\s+)?UNITED STATES SENATOR\b|\bU\.?S\.? SENATOR\b',
    'Governor': r'\b(?:FOR\s+)?GOVERNOR\b(?:\s+(?:AND|&)\s+LT\.?\s*GOVERNOR\b)?',
}

def block_windows(text, office):
    pat = OFFICE_PATTERNS[office]
    up = text.upper()
    wins = []
    for m in re.finditer(pat, up):
        # extend until the next DIFFERENT office heading or 6000 chars
        tail = up[m.end():m.end()+8000]
        nxt = None
        for om in re.finditer(r'\bUNITED STATES SENATOR\b|\bU\.?S\.? SENATOR\b|\bGOVERNOR\b|'
                              r'\bSECRETARY OF STATE\b|\bATTORNEY GENERAL\b|\bSTATE SENATE\b|'
                              r'\bREPRESENTATIVE IN CONGRESS\b|\bUNITED STATES REPRESENTATIVE\b', tail):
            if not re.match(pat, om.group(0)):
                nxt = om.start(); break
        wins.append(text[m.start():m.end() + (nxt if nxt else 6000)])
    return wins

def name_in_block(block, name):
    t = norm_tokens(name)
    if not t: return False
    up = re.sub(r'\s+', ' ', block.upper())
    last = t[-1]
    for m in re.finditer(re.escape(last), up):
        a, b = max(0, m.start()-60), min(len(up), m.end()+60)
        if t[0] in up[a:b]:
            return True
    return False

def main():
    caps = json.load(open(f'{HERE}/captures.json'))
    data = json.load(open(DATASET))
    pos = {p['id']: p for p in data['positions']}
    verdicts = {}
    only = set(sys.argv[1:])
    for pid, cap in sorted(caps.items()):
        if only and pid not in only: continue
        if not cap.get('sha'):
            verdicts[pid] = {'verdict': 'no_capture'}; continue
        p = pos[pid]
        office = 'U.S. Senate' if p.get('office_category') == 'U.S. Senate' else 'Governor'
        roster = (p.get('candidates') or []) + (p.get('filed_candidates_not_confirmed_on_ballot') or [])
        text = page_text(f"{HERE}/raw/{cap['path']}")
        wins = block_windows(text, office)
        best = {'found': [], 'block': ''}
        for w in wins:
            found = [c['name'] for c in roster if name_in_block(w, c['name'])]
            if len(found) > len(best['found']):
                best = {'found': found, 'block': w}
        missing = [c['name'] for c in roster if c['name'] not in best['found']]
        verdicts[pid] = {
            'state': cap['state'], 'office': office, 'source_url': cap.get('source_url'),
            'windows': len(wins), 'roster': [c['name'] for c in roster],
            'found': best['found'], 'missing': missing,
            'verdict': ('FULL' if wins and not missing else ('PARTIAL' if best['found'] else 'NO_BLOCK')),
            'block_preview': re.sub(r'\s+', ' ', best['block'])[:1200],
        }
    out = f'{HERE}/verdicts.json'
    json.dump(verdicts, open(out, 'w'), indent=1)
    for pid, v in verdicts.items():
        print(pid, v.get('state', ''), v['verdict'],
              (f"{len(v.get('found', []))}/{len(v.get('roster', []))} missing={v.get('missing')}"
               if v['verdict'] != 'no_capture' else ''))

if __name__ == '__main__':
    main()
