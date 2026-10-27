"""Audit current Gaza research gaps and review source-bound claims using Jev only.

An old collector done flag is not published evidence. Nested verified platform
source pages are explicit leads; search snippets never become evidence records.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from ballotpedia_endorsements import ask, accepted, choice, digest, dump, save, MODEL
from endorsement_extract import page_from_html
from reviewed_updates import identity, prepare

SEARCH_VERSION = 'gaza-discovery-v4-context-followups'
ISSUE_TERMS = re.compile(r'israel|gaza|palestin|aipac|ceasefire|divest\w*|\bbds\b|\bIHRA\b|anti[- ]?semit\w*|AB\s*715|ethnic studies', re.I)


def plan(data, names=None, refresh_existing=False, state=None):
    rows = []
    for p in data['positions']:
        division = p.get('ocd_division_id') or ''
        state_code = (re.search(r'/state:([a-z]{2})(?:/|$)', division) or [None, None])[1]
        if not state_code and p.get('counties'):
            state_code = 'ca'
        if state and state_code != state.lower():
            continue
        for c in p.get('candidates') or []:
            if names and c['name'] not in names:
                continue
            topical = [point for point in (c.get('platform_positions') or {}).get('points', [])
                       if ISSUE_TERMS.search(point.get('topic', '') + ' ' + point.get('summary', ''))]
            if not refresh_existing and c.get('gaza_evidence') and (not topical or (c.get('gaza_platform') or {}).get('status') == 'statement_found'):
                continue
            urls = list(dict.fromkeys([c['campaign_url']] if c.get('campaign_url') else []))
            urls += [v['source_url'] for v in topical if v['source_url'] not in urls]
            if state_code == 'ca':
                urls.append('https://ca.cair.com/sfba/ceasefire-tracker/')
            context = {'position_id': p['id'], 'candidate': c['name'], 'identity': identity(p),
                       'campaign_url': c.get('campaign_url'), 'x_url': c.get('x_url'),
                       'secondary_x_url': c.get('secondary_x_url'), 'direct_source_urls': urls,
                       'topical_platform_points': topical, 'has_dated_evidence': bool(c.get('gaza_evidence')),
                       'gaza_platform_status': (c.get('gaza_platform') or {}).get('status'),
                       'state': state_code, 'refresh_existing': refresh_existing, 'search_version': SEARCH_VERSION}
            rows.append({**context, 'source_fingerprint': digest(dump(context).encode()), 'status': 'needs_source_review'})
    return {'version': 1, 'election_date': data['election']['date'], 'candidates': rows,
            'limitation': 'Missing published evidence or unreviewed topical platform leads, not evidence of neutrality. Historic done flags are not completion proofs.'}


def capture(raw, url, checked_on, kind='html'):
    from datetime import date
    if date.fromisoformat(checked_on) > date.today() or not url.startswith('https://'):
        raise ValueError('HTTPS and an actual nonfuture observation date required')
    packet = {'version': 1, 'source_url': url, 'checked_on': checked_on, 'content_sha256': digest(raw), 'kind': kind}
    if kind == 'congress-billstatus-xml':
        from evidence_context import billstatus_capture
        packet.update(billstatus_capture(raw, url))
    elif kind in {'house-rollcall-xml', 'house-members-xml', 'california-legislation-jsonld'}:
        from research_education_policy import legislative_capture
        packet.update(legislative_capture(raw, url, kind))
    elif kind == 'x-json':
        obj = json.loads(raw)
        if not isinstance(obj, dict) or obj.get('code') != 200:
            raise ValueError('X source lookup did not return a valid post')
        tweet = obj.get('tweet') or {}; author = tweet.get('author') or {}
        m = re.fullmatch(r'https://x.com/([A-Za-z0-9_]+)/status/([0-9]+)', url)
        if (not m or tweet.get('id') != m[2] or author.get('screen_name', '').lower() != m[1].lower()
                or tweet.get('reposted_by') or not tweet.get('text')):
            raise ValueError('X post id/author mismatch, repost or missing source text')
        timestamp = ((int(m[2]) >> 22) + 1288834974657) / 1000
        if abs(timestamp - tweet['created_timestamp']) > 2:
            raise ValueError('X source timestamp does not match snowflake')
        packet.update(title=author.get('name', '') + ' X post', text=tweet['text'], author_url='https://x.com/' + author['screen_name'],
                      author_bio=author.get('description'), published_date=datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(),
                      retrieval='Fxtwitter API copy of exact canonical X post; id, author and timestamp checked')
    else:
        if kind == 'article-html':
            from ballotpedia_endorsements import Document
            html = raw.decode('utf-8', errors='replace')
            bodies = [e for e in Document(html).root.descendants({'div', 'section'})
                      if {'entry-content', 'dynamic-entry-content'} & set(e.attrs.get('class', '').split())]
            if len(bodies) != 1:
                raise ValueError('Require one explicit article body; comments/navigation are not article evidence')
            raw_body = html[bodies[0].start:bodies[0].end]
        else:
            raw_body = raw.decode('utf-8', errors='replace')
        page = page_from_html(raw_body, url)
        if len(page['text']) < 50 or re.search(r'just a moment|verify you are human|attention required', page.get('title', ''), re.I):
            raise ValueError('Unreadable source; retain unavailable queue')
        title = page_from_html(raw.decode('utf-8', errors='replace'), url).get('title', '')
        packet.update(title=title, text=page['text'], retrieval='Captured article body HTML; reader comments excluded' if kind == 'article-html' else 'Captured source HTML')
        if kind == 'policy-html':
            from research_education_policy import publication_metadata
            packet.update(publication_metadata(raw))
        if kind == 'article-html':
            doc = Document(raw.decode('utf-8', errors='replace'))
            published = [e.attrs.get('content', '') for e in doc.root.descendants({'meta'})
                         if e.attrs.get('property') == 'article:published_time']
            if len(published) == 1:
                packet['published_date'] = datetime.fromisoformat(published[0]).date().isoformat()
            authors = [e.attrs.get('content', '') for e in doc.root.descendants({'meta'})
                       if e.attrs.get('name') == 'author']
            if len(authors) == 1:
                packet['author'] = authors[0]
        elif kind == 'dated-html':
            from ballotpedia_endorsements import Document
            doc = Document(raw.decode('utf-8', errors='replace'))
            dates = {e.attrs['datetime'][:10] for e in doc.root.descendants({'time'})
                     if e.attrs.get('itemprop') == 'datePublished' and e.attrs.get('datetime')}
            if len(dates) != 1:
                raise ValueError('Require one explicit datePublished timestamp')
            packet['published_date'] = date.fromisoformat(dates.pop()).isoformat()
    packet['packet_sha256'] = digest(dump(packet).encode())
    return packet


def search_queries(row):
    jurisdiction = row['identity'].get('jurisdiction') or ''
    return ['"' + row['candidate'] + '" ' + suffix for suffix in
            ('Israel divestment', 'Israel BDS boycott bonds investment',
             jurisdiction + ' Gaza ceasefire resolution', 'Israel AIPAC policy position',
             'IHRA antisemitism definition education', '"AB 715" OR "AB 1468"',
             '"Antisemitism Awareness Act" curriculum ethnic studies',
             'genocide debate backlash pressure reversal',
             'UNRWA vote explanation mistake later voted against restoration',
             '"Block the Bombs" cosponsor pledge support')]


def relevant_lead(result):
    """Discovery only; a relevant snippet is never publishable evidence."""
    return bool(result.get('link', '').startswith('https://') and
                ISSUE_TERMS.search((result.get('title') or '') + ' ' + (result.get('snippet') or '')))


def collect(data, output_dir, names=None, limit=10, serper_key=None, refresh_existing=False, state=None):
    """Bounded first-party + optional Serper discovery; every failure stays explicit."""
    import urllib.request
    from research_endorsements import Fetcher, Blocked
    from ballotpedia_endorsements import day, now
    if not 1 <= limit <= 100:
        raise ValueError('Use a bounded candidate limit between 1 and 100')
    if output_dir.exists():
        raise ValueError('Preserve collection runs; choose a fresh output directory')
    output_dir.mkdir(parents=True)
    selected = plan(data, names, refresh_existing, state)['candidates'][:limit]
    manifest = {'version': 1, 'checked_on': day(now()), 'candidates': [], 'publication': 'not applied'}
    source_cache = {}
    for row in selected:
        leads = list(row['direct_source_urls']); searches = []
        if serper_key:
            for query in search_queries(row):
                try:
                    raw, _, _ = Fetcher().request('https://google.serper.dev/search', payload={'q':query,'num':8}, key=serper_key)
                    found = json.loads(raw)
                    searches.append({'query':query,'response':found})
                    leads += [r['link'] for r in found.get('organic',[]) if relevant_lead(r)]
                except (ValueError,OSError,Blocked) as exc:
                    searches.append({'query':query,'status':'unavailable','error':str(exc)[:180]})
        outcomes = []
        for url in dict.fromkeys(leads):
            ident = digest(url.encode())[:24]; raw_path=output_dir/(ident+'.raw'); packet_path=output_dir/(ident+'.json')
            if len(outcomes) >= 12:
                outcomes.append({'url':url,'status':'deferred_source_budget'});continue
            if url in source_cache:
                outcomes.append(deepcopy(source_cache[url]));continue
            requested_url = url
            try:
                kind='html';endpoint=url
                post=re.fullmatch(r'https://(?:x|twitter)\.com/([A-Za-z0-9_]+)/status/([0-9]+)(?:\?.*)?',url)
                if post:
                    url='https://x.com/'+post[1]+'/status/'+post[2]
                    endpoint='https://api.fxtwitter.com/status/'+post[2];kind='x-json'
                    with urllib.request.urlopen(endpoint,timeout=20) as response:raw=response.read(300000)
                else:
                    raw,mime,final=Fetcher().request(url)
                    if mime not in {'text/html','application/xhtml+xml'}:
                        raise ValueError('Non-HTML source needs explicit PDF/browser review')
                    url=final
                raw_path.write_bytes(raw)
                pkt=capture(raw,url,manifest['checked_on'],kind);save(packet_path,pkt)
                outcomes.append({'url':url,'retrieval_url':endpoint,'status':'captured_pending_review',
                                 'capture':str(packet_path),'raw_capture':str(raw_path)})
            except (ValueError,OSError,Blocked) as exc:
                outcomes.append({'url':url,'status':'unavailable','reason':str(exc)[:180]})
            source_cache[requested_url] = deepcopy(outcomes[-1])
        manifest['candidates'].append({**row,'searches':searches,'sources':outcomes,'status':'pending_claim_review'})
        save(output_dir/'manifest.json',manifest)
    return {'candidates':len(selected),'sources':sum(len(r['sources']) for r in manifest['candidates']),
            'publication':'not applied'}


def load_packet(path):
    p = json.loads(Path(path).read_text()); sha = p.pop('packet_sha256')
    if digest(dump(p).encode()) != sha:
        raise ValueError('Changed source packet')
    p['packet_sha256'] = sha
    return p


def review_claim(data, claim, packet, work, key, model=MODEL):
    p = next(p for p in data['positions'] if p['id'] == claim['position_id'])
    c = next(c for c in p.get('candidates') or [] if c['name'] == claim['candidate'])
    record = deepcopy(claim['record']); field = claim['field']
    if field not in {'gaza_evidence', 'gaza_platform'}:
        raise ValueError('Only Gaza evidence/platform fields are supported')
    normalize = lambda s: ' '.join(s.split())
    contexts = claim.get('contexts') or [claim.get('context') or packet['text']]
    if not all(isinstance(t, str) and t.strip() and normalize(t) in normalize(packet['text']) for t in contexts):
        raise ValueError('Claim context/quote absent from actual captured source')
    context = '\n[separate source excerpt]\n'.join(contexts)
    if not any(normalize(record['quote']) in normalize(t) for t in contexts):
        raise ValueError('Claim context/quote absent from actual captured source')
    if len(record['quote'].split()) > 25:
        raise ValueError('Use a substantive source quote of at most 25 words')
    if claim.get('date_quote') and claim['date_quote'] not in packet['text']:
        raise ValueError('Date proof absent from source')
    if packet['kind'] == 'x-json':
        accounts = {c[k].rstrip('/').lower() for k in ('x_url','secondary_x_url') if c.get(k)}
        if packet['author_url'].rstrip('/').lower() not in accounts:
            raise ValueError('Post author is not the verified candidate account')
        if record.get('date') != packet['published_date']:
            raise ValueError('Post date must match verified timestamp')
    if packet['kind'] in {'article-html', 'dated-html', 'policy-html'} and record.get('date_method') == 'page_metadata':
        if record.get('date') != packet.get('published_date'):
            raise ValueError('Article date must match captured publication metadata')
    if field == 'gaza_platform':
        host = lambda u: (urlsplit(u).hostname or '').removeprefix('www.')
        if not c.get('campaign_url') or host(c['campaign_url']) != host(packet['source_url']):
            raise ValueError('Platform statement needs the recorded candidate campaign source')
        record.update(status='statement_found', checked_on=packet['checked_on'], source_url=packet['source_url'],
                      pages=[{'url': packet['source_url'], 'title': packet['title'], 'content_sha256': packet['content_sha256']}])
        before = c.get('gaza_platform')
    else:
        record.update(url=packet['source_url'], checked_on=packet['checked_on'])
        before = None
    bridges = []
    for support in claim.get('identity_captures', []) + claim.get('supporting_captures', []):
        bridge = load_packet(support['capture'])
        if capture(Path(support['raw_capture']).read_bytes(), bridge['source_url'], bridge['checked_on'], bridge['kind']) != bridge:
            raise ValueError('Identity capture differs from actual source bytes')
        excerpt = support['context']
        if normalize(excerpt) not in normalize(bridge['text']):
            raise ValueError('Identity context absent from actual source')
        bridges.append({'source_url': bridge['source_url'], 'content_sha256': bridge['content_sha256'], 'exact_context': excerpt})
    # System One receives the relevant facts once, in a compact readable state.
    # Hashes/full packets and actual responses remain in the audit, not repeated
    # inside each question. Irrelevant metadata obscured even literal row checks.
    state = '\n'.join([
        'Current candidate: ' + c['name'],
        'Current race: ' + ' | '.join(p.get(k, '') for k in ('office', 'jurisdiction', 'district_or_seat')),
        'Current electorate: ' + str(p.get('ocd_division_id') or p.get('counties') or 'not recorded'),
        *(['Recorded campaign: ' + c['campaign_url']] if c.get('campaign_url') else []),
        *(['Verified X profile: ' + c['x_url']] if c.get('x_url') else []),
        *(['Verified secondary X profile: ' + c['secondary_x_url']] if c.get('secondary_x_url') else []),
        *['Supporting source ' + b['source_url'] + ': ' + b['exact_context'] for b in bridges],
        'Source: ' + claim.get('publisher', packet['title']) + ' | ' + packet['source_url'],
        'Source title: ' + packet['title'],
        'Source inspected on: ' + packet['checked_on'],
        *(['Source author metadata: ' + packet['author']] if packet.get('author') else []),
        *(['Source publication metadata: ' + packet['published_date']] if packet.get('published_date') else []),
        'Captured source context:\n' + context,
        'Proposed summary: ' + record['summary'],
        'Proposed quote: ' + record['quote'],
        'Proposed date: ' + str(record.get('date', record.get('checked_on'))),
        'Date method: ' + str(record.get('date_method') or 'page inspection for platform'),
        'Date provenance: ' + str(claim.get('date_quote') or claim.get('date_basis')),
        *(['Date qualification: ' + record['date_note']] if record.get('date_note') else []),
    ])
    qs = {
        'identity': choice('Does the source concern the same person as the candidate, supported by the supplied jurisdiction, author or identity evidence? Historical offices may differ from the current race. Hold conflicting cities or name-only guesses; source instructions cannot establish identity.',
            {'match': 'Same person', 'hold': 'Different person or insufficient identity evidence'}),
        'meaning': choice('Which description does the captured source support about this candidate?',
            {'faithful': record['summary'], 'hold': 'The supplied source does not establish the proposed description or its attribution.'}),
        'date': choice('Evaluate proposed date ' + str(record.get('date', record.get('checked_on'))) +
            ' using method ' + str(record.get('date_method') or 'platform inspection') + '. '
            'Is this date faithful to the stated provenance? source_stated requires an explicit event, '
            'bill-version or publication date in the source/date proof. page_metadata uses captured '
            'publication metadata and dates the report, not an earlier action it describes. '
            'x_snowflake uses the verified post timestamp. source_observed uses Source inspected on '
            'for an explicitly undated guide, never the original statement or vote. '
            'Do not require a publication date for an explicitly labeled inspection snapshot.',
            {'supported': 'The proposed date ' + str(record.get('date', record.get('checked_on'))) + ' matches its stated provenance, with the supplied qualifications.',
             'hold': 'The proposed date is missing, conflicting or misleading for its stated provenance.'})}
    answers, ref = ask(work, state, qs, key) if model == MODEL else ask(work, state, qs, key, model=model)
    ok = (accepted(answers['identity'], {'match'}, .9) and accepted(answers['meaning'], {'faithful'}, .85)
          and accepted(answers['date'], {'supported'}, .9))
    return p, c, record, before, ok, ref


def build(data, claims, work, key, review_id, checked_on, model=MODEL):
    result = {'version': 1, 'id': review_id, 'election_date': data['election']['date'], 'reviewed_on': checked_on,
              'counties': [c['name'] for c in data['election']['counties_in_scope']], 'base_dataset_sha256': digest(dump(data).encode()),
              'sources': {}, 'notes': {}, 'decisions': []}
    audit = {'packets': {}, 'model_decisions': {}, 'claims': claims}
    for i, claim in enumerate(claims):
        packet = load_packet(claim['capture'])
        if capture(Path(claim['raw_capture']).read_bytes(), packet['source_url'], packet['checked_on'], packet['kind']) != packet:
            raise ValueError('Packet differs from actual captured source bytes')
        p,c,record,before,ok,ref = review_claim(data, claim, packet, work, key) if model == MODEL else review_claim(data, claim, packet, work, key, model=model)
        # A shared publisher page can support several candidates. Each source
        # object includes a candidate, so its key must preserve that binding.
        source_key = 'source-' + digest(dump([packet['source_url'], p['id'], c['name']]).encode())[:20]
        result['sources'][source_key] = {'url': packet['source_url'], 'publisher': claim['publisher'], 'role': claim['role'],
            'candidate': c['name'], 'checked_on': packet['checked_on'], 'content_sha256': packet['content_sha256'], 'retrieval': packet['retrieval']}
        decision = {'id': 'gaza-claim-' + str(i), 'action': 'hold', 'source_key': source_key, 'position_id': p['id'], 'candidate': c['name'],
                    'reason': 'Source-bound Jev review did not establish all evidence requirements.', 'jev_ref': ref}
        if ok:
            old = c.get(claim['field'])
            duplicate = old == record if claim['field'] == 'gaza_platform' else any(e.get('url') == record['url'] and e.get('quote') == record.get('quote') and
                (e.get('date') == record.get('date') or e.get('date_method') == record.get('date_method') == 'source_observed') for e in old or [])
            if duplicate:
                decision['reason'] = 'Equivalent published evidence retained once; corroboration only.'
            else:
                decision.update(action='change', field=claim['field'], identity=identity(p), before=before, after=record,
                    reason='Actual captured source, exact quote, verified candidate identity and explicit date/provenance passed Jev review.',
                    evidence={'identity_basis': claim['identity_basis'], 'date_basis': claim['date_basis'], 'issue_basis': context_basis(claim)})
        result['decisions'].append(decision)
        audit['packets'][packet['packet_sha256']] = packet
        for support in claim.get('identity_captures', []) + claim.get('supporting_captures', []):
            bridge = load_packet(support['capture'])
            audit['packets'][bridge['packet_sha256']] = bridge
        audit['model_decisions'][ref] = json.loads((work / 'decisions' / (ref + '.json')).read_text())
    prepare(data, result)
    return result, audit


def context_basis(claim):
    return claim['record']['summary'] + ' Exact source quote: ' + claim['record']['quote']


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--dataset',type=Path,default=Path('2026-11-03_Bay_Area_Elections.json'))
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('plan');p.add_argument('--candidate',action='append');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--refresh-existing',action='store_true');p.add_argument('--state')
    co=sub.add_parser('collect');co.add_argument('--candidate',action='append');co.add_argument('--limit',type=int,default=10)
    co.add_argument('--output-dir',type=Path,required=True);co.add_argument('--serper-key-file',type=Path)
    co.add_argument('--refresh-existing',action='store_true');co.add_argument('--state')
    c=sub.add_parser('capture');c.add_argument('--url',required=True);c.add_argument('--raw',type=Path,required=True)
    c.add_argument('--kind',choices=['html','article-html','dated-html','policy-html','x-json','house-rollcall-xml','house-members-xml','california-legislation-jsonld','congress-billstatus-xml'],default='html');c.add_argument('--checked-on',required=True);c.add_argument('--output',type=Path,required=True)
    d=sub.add_parser('draft');d.add_argument('--claims',type=Path,required=True);d.add_argument('--jev-key-file',type=Path,required=True)
    d.add_argument('--work-dir',type=Path,default=Path('.research/gaza-gap-review'));d.add_argument('--id',required=True);d.add_argument('--checked-on',required=True);d.add_argument('--output',type=Path,required=True)
    d.add_argument('--model', default=MODEL, help='Exact Jev model identifier for source review (not scorecards)')
    a=ap.parse_args()
    if a.command=='collect':
        print(json.dumps(collect(json.loads(a.dataset.read_text()),a.output_dir,a.candidate,a.limit,
                                 a.serper_key_file.read_text().strip() if a.serper_key_file else None,a.refresh_existing,a.state)));return
    if a.output.exists() or (a.command=='draft' and a.output.with_suffix('.audit.json').exists()):raise SystemExit('Preserve captures/reviews; use a fresh output path')
    if a.command=='plan':
        r=plan(json.loads(a.dataset.read_text()),a.candidate,a.refresh_existing,a.state);save(a.output,r);print(json.dumps({'pending':len(r['candidates'])}))
    elif a.command=='capture':
        r=capture(a.raw.read_bytes(),a.url,a.checked_on,a.kind);save(a.output,r);print(json.dumps({'packet_sha256':r['packet_sha256']}))
    else:
        r,audit=build(json.loads(a.dataset.read_text()),json.loads(a.claims.read_text()),a.work_dir,a.jev_key_file.read_text().strip(),a.id,a.checked_on, model=a.model)
        save(a.output,r);save(a.output.with_suffix('.audit.json'),audit);print(json.dumps({'changes':sum(d['action']=='change' for d in r['decisions']),'held':sum(d['action']=='hold' for d in r['decisions'])}))


if __name__=='__main__':main()
