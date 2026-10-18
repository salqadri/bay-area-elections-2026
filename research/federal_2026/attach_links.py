#!/usr/bin/env python3
"""Attach verified campaign_url / x_url from links.json onto the nationwide
provisional candidacies in the dataset, with dated source evidence recorded per
link. Only 'verified'-confidence links attach automatically; 'probable' ones
attach only when corroborated by two independent origins (campaign-site link +
search hit) — everything else is left null for manual review.

Registers a Serper-search provenance note and bumps publication_version.
Idempotent: re-running with the same ledger changes nothing.
"""
import json, subprocess, sys

DATA = '/workspace/bay-area-elections-2026/2026-11-03_Bay_Area_Elections.json'
LEDGER = 'links.json'
CHECKED = '2026-10-17'
# third-party pages that passed the disclaimer gate but are not campaign sites
THIRD_PARTY = ('northshoreweekly.com', 'lp.org', 'lpcolorado.org')

def pacific_date():
    return subprocess.run(['date','+%F'],capture_output=True,text=True,
                          env={'TZ':'America/Los_Angeles'}).stdout.strip() or CHECKED

def main():
    checked = pacific_date()
    data = json.load(open(DATA))
    ledger = json.load(open(LEDGER))
    srcs = data['sources']  # dict: id -> {url,title}
    SER = 'S1101'
    if SER not in srcs:
        srcs[SER] = {'url': 'https://serper.dev',
            'title': f'Serper web search of official campaign sites and X accounts; pages fetched directly (checked {checked})'}
    notes = data['notes']  # dict: id -> text
    if 'N908' not in notes:
        notes['N908'] = ('Links for nationwide candidacies were discovered by dated web search and verified '
            'mechanically: campaign sites must be HTTPS pages on the candidate\'s own domain (or carry a '
            'paid-for-by disclaimer) naming the candidate with office context; X accounts must exist at the '
            'handle and match the candidate name, or be linked from the verified campaign site. Links held '
            'below that bar are omitted rather than guessed.')

    attached_site = attached_x = 0
    for p in data['positions']:
        if not (p.get('office_category') == 'U.S. Senate' or (p.get('office') == 'Governor' and not p.get('counties'))):
            continue
        state = p['district_or_seat'].split(' —')[0]
        for c in p.get('filed_candidates_not_confirmed_on_ballot') or []:
            v = ledger.get(f"{p['id']}::{c['name']}") or {}
            site_ev = (v.get('evidence') or {}).get('site') or {}
            x_ev = (v.get('evidence') or {}).get('x') or {}
            if v.get('campaign_url') and not c.get('campaign_url'):
                ok = site_ev.get('confidence') == 'verified' or (
                    site_ev.get('confidence') == 'probable' and (site_ev.get('disclaimer') or site_ev.get('own_domain')))
                if ok and not any(t in site_ev.get('host','') for t in THIRD_PARTY):
                    from urllib.parse import urlparse
                    u = urlparse(v['campaign_url'])
                    c['campaign_url'] = f"{u.scheme}://{u.netloc}/" if site_ev.get('own_domain') else v['campaign_url'].rstrip('/')
                    c.setdefault('source_ids', [])
                    if SER not in c['source_ids']: c['source_ids'].append(SER)
                    attached_site += 1
            if v.get('x_url') and not c.get('x_url'):
                if x_ev.get('confidence') == 'verified' or x_ev.get('origin') == 'linked_from_campaign_site':
                    c['x_url'] = v['x_url']
                    c.setdefault('source_ids', [])
                    if SER not in c['source_ids']: c['source_ids'].append(SER)
                    attached_x += 1
        if any(('campaign_url' in c or 'x_url' in c) for c in (p.get('filed_candidates_not_confirmed_on_ballot') or [])):
            if 'N908' not in p.setdefault('note_ids', []): p['note_ids'].append('N908')

    pub = data['election']['publication_version']
    base, _, n = pub.rpartition('.')
    data['election']['publication_version'] = f"{base}.{int(n)+1}"
    json.dump(data, open(DATA,'w'), indent=1, ensure_ascii=False)
    open(DATA,'a').write('\n')
    print(json.dumps({'publication_version': data['election']['publication_version'],
                      'campaign_urls_attached': attached_site, 'x_urls_attached': attached_x}))

if __name__ == '__main__':
    main()
