#!/usr/bin/env python3
"""Historical scaffold discovery runner (not the current inventory refresh).

For missing X profiles across all current offices, use scripts/research_x_profiles.py;
this old runner reads draft_positions.json and skips already-seen ledger entries.

Discover official campaign websites and X accounts for the nationwide 2026
Senate/governor candidacies via Serper, with mechanical verification gates.

Gates (mirroring how the existing x_url/campaign_url layer was verified):
- website: HTTPS organic result on a non-aggregator domain whose fetched page
  text contains the candidate's full name AND an office/state context token;
  recorded as 'verified' only when both hold, else 'probable' with evidence.
- X account: handle taken from an x.com/twitter.com search hit or from a link
  on the verified campaign site; existence confirmed via the Twitter syndication
  endpoint (account name similarity) — never guessed from a bare name alone.
Output: links.json ledger keyed by candidacy id; nothing is written to the
dataset here — attachment happens in a separate reviewed step.
"""
import json, re, subprocess, sys, time, html as htmllib, unicodedata, urllib.parse

SERPER_KEY = open('/root/.cfg/serper_key').read().strip()
AGGREGATORS = {'wikipedia.org','ballotpedia.org','votesmart.org','source.us','linkedin.com',
 'facebook.com','instagram.com','youtube.com','x.com','twitter.com','truthsocial.com',
 'reddit.com','qcc.voting','wisvoterinfo.com','mikebloomberg.com'}
NEWS = re.compile(r'(nytimes|washingtonpost|cnn\.com|foxnews|nbc|cbs|abc|pbs|npr|politico|thehill|axios|reuters|ap\.org|nypost|usatoday|wsj|bloomberg|guardian|buzzfeed|dailybeast|time\.com|newsweek|occupy|breitbart|rasmussen|realclear|538|cookpolitical|savestudents|govtrack|legiscan|followthemoney|opensecrets|fec\.gov|maplight|commoncause|ballotpedia|ourcampaigns|jarrett|vote\.smart|votesmart|wikipedia)')

def serper(q, engine='search'):
    body = json.dumps({'q': q, 'num': 8 if engine=='search' else 5})
    for attempt in range(4):
        r = subprocess.run(['curl','-s','-m','25','-X','POST',f'https://google.serper.dev/{engine}',
            '-H',f'X-API-KEY: {SERPER_KEY}','-H','Content-Type: application/json','-d',body],
            capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
            if 'error' not in str(d)[:120].lower() or attempt == 3: return d
        except Exception: pass
        time.sleep(2 ** attempt)
    return {}

def fetch(url):
    r = subprocess.run(['curl','-sL','-m','25','--compressed',
        '-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36',
        url], capture_output=True, text=True)
    return r.stdout or ''

def strip_html(s):
    s = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', s, flags=re.S|re.I)
    return htmllib.unescape(re.sub(r'<[^>]+>', ' ', s))

def norm(s):
    s = unicodedata.normalize('NFKD', s); s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z ]',' ', s.lower()).split()

def name_in(text_tokens, name):
    t = norm(name); 
    if ' '.join(text_tokens).find(' '.join(t)) >= 0: return True
    # allow middle-initial/middle-name variance
    for i in range(len(text_tokens)-len(t)+1):
        w = text_tokens[i:i+len(t)]
        if w[0]==t[0] and w[-1]==t[-1]: return True
    return False

def syndication_check(handle):
    """Confirm an X handle exists; return (account_name, confirmed_handle) or (None, None)."""
    for url in (f'https://api.fxtwitter.com/{handle}',
                f'https://cdn.syndication.twimg.com/widgets/followbutton/info.json?screen_names={handle}'):
        try:
            r = subprocess.run(['curl','-s','-m','15',url], capture_output=True, text=True)
            d = json.loads(r.stdout) if r.stdout.strip() else None
            if isinstance(d, dict):  # {"code":200,"user":{"screen_name","name",...}}
                u = d.get('user') or {}
                if u.get('screen_name'): return u.get('name'), u['screen_name']
            elif isinstance(d, list) and d:
                return d[0].get('name'), d[0].get('screen_name')
        except Exception: pass
    return None, None

def discover(cand):
    name, state, office = cand['name'], cand['state'], cand['office']
    out = {'campaign_url': None, 'x_url': None, 'evidence': {}}
    ctx = 'senator' if office == 'United States Senator' else 'governor'
    d = serper(f'"{name}" for {ctx} {state} 2026 official website campaign')
    organic = d.get('organic', [])
    out['evidence']['site_query'] = f'"{name}" for {ctx} {state} 2026 official website campaign'
    name_toks = set(norm(name)) - {'for','jr','sr','ii','iii'}
    fallback = None
    for res in organic:
        u = res.get('link','')
        p = urllib.parse.urlparse(u)
        if p.scheme != 'https': continue
        host = p.netloc.lower().removeprefix('www.')
        reg_label = '.'.join(host.split('.')[-2:]) if not host.endswith('.gov') else host
        if any(a in host for a in AGGREGATORS) or NEWS.search(reg_label): continue
        title = res.get('title','').lower()
        page = strip_html(fetch(u))[:20000]
        toks = norm(page)
        if not name_in(toks, name):
            time.sleep(0.15); continue
        office_ok = bool(re.search(ctx + r'|united states senate|state senate|governor', ' '.join(toks)))
        host_path = (host + p.path).lower()
        surname = norm(name)[-1]
        own_domain = surname in re.sub(r'[^a-z0-9]+',' ',host) or bool(re.search(r'\bfor\b|\bvote\b|elect', host_path)) and surname in re.sub(r'[^a-z0-9]+',' ',host)
        disclaimer = re.search(r'paid for by|campaign treasurer|my campaign committee', ' '.join(toks)[:6000])
        cand_site = own_domain or (disclaimer and office_ok)
        entry = {'url': u, 'title': res.get('title',''), 'host': host, 'name_on_page': True,
                 'office_context': office_ok, 'own_domain': bool(own_domain), 'disclaimer': bool(disclaimer)}
        if own_domain and office_ok:
            entry['confidence'] = 'verified'
            out['campaign_url'] = u.rstrip('/'); out['evidence']['site'] = entry; break
        if cand_site and not fallback:
            entry['confidence'] = 'probable'; fallback = entry
        time.sleep(0.15)
    if not out['campaign_url'] and fallback:
        out['campaign_url'] = fallback['url'].rstrip('/'); out['evidence']['site'] = fallback
    # X: prefer handles linked from the verified campaign page, then search hits
    handles = []
    if out['campaign_url']:
        page = fetch(out['campaign_url'])
        for m in re.finditer(r'https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{2,15})', page):
            h = m.group(1)
            if h.lower() not in ('home','search','hashtag','intent','share','status','profile'):
                handles.append((h, 'linked_from_campaign_site', ''))
    d2 = serper(f'site:x.com "{name}" {state}')
    for res in d2.get('organic', []):
        m = re.search(r'(?:x|twitter)\.com/([A-Za-z0-9_]{2,15})(?:/|$|\?)', res.get('link',''))
        if m and m.group(1).lower() not in ('home','search','hashtag','intent','share','status'):
            handles.append((m.group(1), 'serper_x_search', res.get('title','')))
    seen=set(); best=None
    for handle, origin, title in handles:
        if handle in seen: continue
        seen.add(handle)
        acct_name, confirmed = syndication_check(handle)
        time.sleep(0.2)
        if not confirmed: continue
        nt = norm(acct_name or '')
        wt = norm(name)
        match = bool(nt) and ((wt[0] in nt and wt[-1] in nt) or name_in(nt, name))
        handle_match = re.sub(r'[^a-z0-9]','',name.lower()) in handle.lower().replace('_','')
        if not (match or handle_match): continue
        entry = {'handle': confirmed, 'account_name': acct_name, 'origin': origin, 'title': title,
                 'confidence': 'verified' if match else 'probable'}
        if origin == 'linked_from_campaign_site' and match:
            best = entry; break
        if not best: best = entry
    if best:
        out['x_url'] = f"https://x.com/{best['handle']}"; out['evidence']['x'] = best
    return out

def main():
    draft = json.load(open('draft_positions.json'))
    try:
        ledger = json.load(open('links.json'))
    except FileNotFoundError:
        ledger = {}
    todo = []
    for p in draft:
        if p['office_category'] != 'U.S. Senate' and p['office'] != 'Governor': continue
        state = p['district_or_seat'].split(' —')[0]
        for c in p['candidates']:
            cid = f"{p['id']}::{c['name']}"
            if cid not in ledger: todo.append((cid, {'name': c['name'], 'state': state, 'office': p['office']}))
    print(f'{len(todo)} candidacies to discover', flush=True)
    for i, (cid, cand) in enumerate(todo):
        try:
            ledger[cid] = discover(cand)
        except Exception as e:
            ledger[cid] = {'error': str(e)[:200]}
        json.dump(ledger, open('links.json','w'), indent=1)
        if i % 5 == 0 or i == len(todo)-1:
            found_site = sum(1 for v in ledger.values() if v.get('campaign_url'))
            found_x = sum(1 for v in ledger.values() if v.get('x_url'))
            print(f'{i+1}/{len(todo)} sites={found_site} x={found_x}', flush=True)

if __name__ == '__main__':
    main()
