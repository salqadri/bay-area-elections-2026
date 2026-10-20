#!/usr/bin/env python3
"""Wave 1 matching: for each contest, test how many compiled-roster names appear
in its captured official page text. High coverage = the capture is a real
candidate list; partial/zero = index page or wrong office -> needs deeper crawl.

Name normalization is deliberately loose (middle initials/particles dropped,
hyphens/spaces stripped); a match here is only a LEAD — final confirmation reads
the actual context line for each candidate before any status flip.
"""
import html, json, os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = '/workspace/bay-area-elections-2026/2026-11-03_Bay_Area_Elections.json'
SUFFIXES = {'JR','SR','II','III','IV','V','DR','MD'}

def norm_tokens(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return [t for t in re.sub(r'[^A-Za-z ]', ' ', s).upper().split() if len(t) > 1 and t not in SUFFIXES]

def person_keys(name):
    """(first, last) plus full-name-without-spaces; middle tokens ignored."""
    t = norm_tokens(name)
    if not t: return None
    return {'first': t[0], 'last': t[-1], 'joined': ''.join(t)}

def page_text(path):
    raw = open(path, 'rb').read()
    if raw[:4] == b'%PDF':
        from pypdf import PdfReader
        import io
        r = PdfReader(io.BytesIO(raw))
        return '\n'.join((pg.extract_text() or '') for pg in r.pages)
    txt = raw.decode('utf-8', 'replace')
    txt = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', txt, flags=re.S | re.I)
    txt = html.unescape(re.sub(r'<[^>]+>', ' ', txt))
    return txt

def main():
    caps = json.load(open(f'{HERE}/captures.json'))
    data = json.load(open(DATASET))
    pos = {p['id']: p for p in data['positions']}
    report = {}
    for pid, cap in sorted(caps.items()):
        p = pos[pid]
        roster = (p.get('candidates') or []) + (p.get('filed_candidates_not_confirmed_on_ballot') or [])
        rec = {'state': cap['state'], 'office': cap['office'], 'source_url': cap.get('source_url')}
        if not cap.get('sha'):
            rec['status'] = 'no_capture'
            report[pid] = rec
            continue
        text = page_text(f"{HERE}/raw/{cap['path']}")
        joined_page = re.sub(r'[^A-Z]', '', unicodedata.normalize('NFKD', text).upper())
        spaced = ' ' + re.sub(r'\s+', ' ', re.sub(r'[^A-Za-z ]', ' ', unicodedata.normalize('NFKD', text).upper())) + ' '
        found, missing = [], []
        for c in roster:
            k = person_keys(c['name'])
            hit = k and (k['joined'] in joined_page or
                         (' ' + k['first'] + ' ' in spaced and re.search(r'\b' + k['last'] + r'\b', spaced)))
            (found if hit else missing).append(c['name'])
        rec.update({'status': 'checked', 'text_chars': len(text),
                    'roster': len(roster), 'found': found, 'missing': missing})
        report[pid] = rec
    json.dump(report, open(f'{HERE}/match_report.json', 'w'), indent=1)
    full = [pid for pid, r in report.items() if r['status'] == 'checked' and r['roster'] and not r['missing']]
    part = [pid for pid, r in report.items() if r['status'] == 'checked' and r['missing'] and r['found']]
    zero = [pid for pid, r in report.items() if r['status'] == 'checked' and not r['found']]
    print(f"FULL match ({len(full)}):", full)
    print(f"\nPARTIAL ({len(part)}):")
    for pid in part:
        r = report[pid]
        print(f"  {pid} {r['state']} {r['office']}: {len(r['found'])}/{r['roster']} missing={r['missing']}")
    print(f"\nZERO ({len(zero)}):", [(pid, report[pid]['state'], report[pid]['text_chars']) for pid in zero])

if __name__ == '__main__':
    main()
