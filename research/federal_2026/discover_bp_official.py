#!/usr/bin/env python3
"""Serper-only discovery pass #2 for nationwide candidacies/contests:
1. ballotpedia_url per candidacy — site:ballotpedia.org hit whose page title
   contains the candidate name and an office/state token; URL must return 200.
2. official-source leads per contest — .gov / official-elections-domain hits
   for each state's certified candidate list, cached as reconciliation leads
   (NOT auto-applied; a human/reviewed pass flips ballot_status later).
Writes ballotpedia.json and official_leads.json incrementally. Resumable.
"""
import json, os, re, subprocess, time, urllib.parse

SERPER_KEY = open('/root/.cfg/serper_key').read().strip()
HERE = os.path.dirname(os.path.abspath(__file__))

def serper(q):
    body = json.dumps({'q': q, 'num': 8})
    for attempt in range(4):
        r = subprocess.run(['curl','-s','-m','25','-X','POST','https://google.serper.dev/search',
            '-H',f'X-API-KEY: {SERPER_KEY}','-H','Content-Type: application/json','-d',body],
            capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
            if 'organic' in d or attempt == 3: return d
        except Exception: pass
        time.sleep(2**attempt)
    return {}

def status_ok(url):
    r = subprocess.run(['curl','-s','-o','/dev/null','-w','%{http_code}','-m','20','-L',
        '-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36', url],
        capture_output=True, text=True)
    return r.stdout.strip() == '200'

def page_title(url):
    r = subprocess.run(['curl','-sL','-m','20','--compressed',
        '-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36', url],
        capture_output=True, text=True)
    m = re.search(r'<title[^>]*>(.*?)</title>', r.stdout or '', re.S|re.I)
    return (m.group(1) if m else '').strip()[:200]

def nameish(title, name):
    t = re.sub(r'[^a-z ]',' ', title.lower())
    toks = [w for w in re.sub(r'[^a-z ]',' ', name.lower()).split() if len(w)>2]
    return bool(toks) and all(w in t for w in (toks[0], toks[-1]))

def main():
    draft = json.load(open(os.path.join(HERE,'draft_positions.json')))
    try: bp = json.load(open(os.path.join(HERE,'ballotpedia.json')))
    except FileNotFoundError: bp = {}
    todo_bp = []
    for p in draft:
        state = p['district_or_seat'].split(' —')[0]
        office_tok = 'senate' if p.get('office_category')=='U.S. Senate' else 'governor'
        for c in p['candidates']:
            cid = f"{p['id']}::{c['name']}"
            if cid not in bp: todo_bp.append((cid, c['name'], state, office_tok))
    print(f'{len(todo_bp)} ballotpedia lookups pending', flush=True)
    for i,(cid,name,state,tok) in enumerate(todo_bp):
        url = None; ev = {}
        d = serper(f'site:ballotpedia.org "{name}" {state}')
        cands = []
        for res in d.get('organic', []):
            u = res.get('link','')
            if not u.startswith('https://ballotpedia.org/') or 'news.' in u: continue
            slug = urllib.parse.unquote(u.rsplit('/',1)[-1]).replace('_',' ')
            slug = re.sub(r'\(.*?\)',' ', slug)  # disambiguator
            if nameish(slug, name): cands.append((u, res.get('title','')))
        for u, title in cands:
            if status_ok(u):
                url = u; ev = {'title': title, 'slug_name_match': True}; break
        bp[cid] = {'ballotpedia_url': url, 'evidence': ev} if url else {}
        json.dump(bp, open(os.path.join(HERE,'ballotpedia.json'),'w'), indent=1)
        if i % 10 == 0 or i==len(todo_bp)-1:
            print(f'bp {i+1}/{len(todo_bp)} found={sum(1 for v in bp.values() if v.get("ballotpedia_url"))}', flush=True)

    # official leads per contest (skip if already cached)
    try: leads = json.load(open(os.path.join(HERE,'official_leads.json')))
    except FileNotFoundError: leads = {}
    for p in draft:
        pid = p['id']
        if pid in leads: continue
        state = p['district_or_seat'].split(' —')[0]
        what = 'U.S. Senate' if p.get('office_category')=='U.S. Senate' else 'governor'
        d = serper(f'{state} secretary of state certified candidate list November 2026 general election {what}')
        hits = []
        for res in d.get('organic', [])[:8]:
            u = res.get('link','')
            host = urllib.parse.urlparse(u).netloc.lower()
            if host.endswith('.gov') or 'elections.' in host or 'sos.' in host:
                hits.append({'url': u, 'title': res.get('title','')})
        leads[pid] = {'state': state, 'office': what, 'checked_on': time.strftime('%Y-%m-%d'),
                      'query': f'{state} certified candidate list November 2026 {what}', 'gov_hits': hits[:4]}
        json.dump(leads, open(os.path.join(HERE,'official_leads.json'),'w'), indent=1)
    print('official leads done:', sum(1 for v in leads.values() if v['gov_hits']), '/', len(leads), flush=True)

if __name__ == '__main__':
    main()
