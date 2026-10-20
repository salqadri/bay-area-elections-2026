#!/usr/bin/env python3
"""Wave 2 doc-follow: for unverified contests whose capture is an HTML hub,
extract document links (pdf/xlsx/csv) that look like candidate lists, fetch the
top candidates, and test compiled-roster coverage. Records caps[pid]['docs'] =
[{url, sha, path, bytes, found, missing, title}] sorted by roster coverage."""
import hashlib, html as H, json, os, re, subprocess, sys, time, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from match_official import page_text, person_keys  # noqa: E402
RAW = f'{HERE}/raw'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36'
DOC_RE = re.compile(r'\.(pdf|xlsx?|csv)(?=["\'?\s])', re.I)
LISTY = re.compile(r'(candidat|ballot|qualified|nominee|official.*list|general.*election)', re.I)

def fetch(url):
    r = subprocess.run(['curl', '-sL', '-m', '75', '--compressed', '-A', UA, url], capture_output=True)
    body = r.stdout
    if len(body) < 800: return None
    sha = hashlib.sha256(body).hexdigest()[:16]
    ext = '.pdf' if body[:4] == b'%PDF' else ('.xlsx' if body[:2] == b'PK' else '.bin')
    path = f'{RAW}/{sha}{ext}'
    if not os.path.exists(path): open(path, 'wb').write(body)
    return sha, os.path.basename(path), len(body)

def coverage(text, roster):
    joined = re.sub(r'[^A-Z]', '', unicodedata.normalize('NFKD', text).upper())
    spaced = ' ' + re.sub(r'\s+', ' ', re.sub(r'[^A-Za-z ]', ' ', unicodedata.normalize('NFKD', text).upper())) + ' '
    found, missing = [], []
    for n in roster:
        k = person_keys(n)
        hit = k and (k['joined'] in joined or (' ' + k['first'] + ' ' in spaced and re.search(r'\b' + k['last'] + r'\b', spaced)))
        (found if hit else missing).append(n)
    return found, missing

def main():
    only = set(sys.argv[1:])
    caps = json.load(open(f'{HERE}/captures.json'))
    data = json.load(open('/workspace/bay-area-elections-2026/2026-11-03_Bay_Area_Elections.json'))
    pos = {p['id']: p for p in data['positions']}
    todo = [pid for pid, c in sorted(caps.items())
            if pos[pid]['ballot_status'] == 'unverified' and not c.get('docs')
            and (not only or pid in only)]
    print(f'{len(todo)} contests to follow docs for')
    for pid in todo:
        cap = caps[pid]
        path = f"{RAW}/{cap.get('path','')}"
        if not cap.get('path') or not os.path.exists(path) or path.endswith('.pdf'): continue
        raw = open(path, encoding='utf-8', errors='replace').read()
        base = re.sub(r'(https?://[^/]+).*', r'\1', cap.get('source_url', ''))
        roster = [c['name'] for c in (pos[pid].get('candidates') or []) + (pos[pid].get('filed_candidates_not_confirmed_on_ballot') or [])]
        links = []
        # loose: any href to a doc; score from URL and whatever anchor text follows
        for m in re.finditer(r'href="([^"]*\.(?:pdf|xlsx?|csv)(?:[?"\'#][^"]*)?)"', raw, re.I):
            u = m.group(1)
            label = H.unescape(re.sub(r'<[^>]+>', ' ', raw[m.end():m.end()+200]))[:90]
            hay = (u + ' ' + label).lower()
            if re.search(r'primary|sample.?ballot|calendar|guide|manual|ethics|finance|disclosure|map|deadline', hay): score = 1
            elif LISTY.search(hay) and '2026' in hay: score = 4
            elif LISTY.search(hay): score = 3
            elif re.search(r'(general|2026)', hay): score = 2
            else: score = 0
            if score == 0: continue
            full = u if u.startswith('http') else (base + (u if u.startswith('/') else '/' + u))
            links.append((score, full, label.strip()[:70]))
        seen, picked, results = set(), 0, []
        for score, url, label in sorted(links, key=lambda x: -x[0]):
            if url in seen or picked >= 5: continue
            seen.add(url)
            got = fetch(url)
            if not got: continue
            sha, name, size = got
            try: text = page_text(f'{RAW}/{name}')
            except Exception: continue
            found, missing = coverage(text, roster)
            results.append({'url': url, 'sha': sha, 'path': name, 'bytes': size, 'title': label,
                            'text_chars': len(text), 'found': found, 'missing': missing})
            picked += 1
            if not missing: break
        cap['docs'] = sorted(results, key=lambda r: (-len(r['found']), r['bytes']))[:6]
        caps[pid] = cap
        json.dump(caps, open(f'{HERE}/captures.json', 'w'), indent=1)
        best = cap['docs'][0] if cap['docs'] else None
        print(pid, cap['state'], pos[pid]['office'][:12], '| docs:', len(cap['docs']),
              '| best found', len(best['found']) if best else 0, '/', len(roster),
              '|', (best or {}).get('title', '')[:45])

if __name__ == '__main__':
    main()
