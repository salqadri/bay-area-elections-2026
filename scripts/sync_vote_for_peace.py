"""Capture Vote for Peace's first-party cards and draft exact, scoped review updates.

No search, model decisions, fuzzy identity matching, or automatic deletion on
source absence. Review/applied changes use the existing publication review gate.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

from endorsement_extract import norm, office_matches
from publication_reviews import ROOT
from reviewed_updates import identity

URL = 'https://voteforpeace.info/candidates'
LABELS = {'vote': ('Ally', 'supported'), 'reject': ('Opposed', 'opposed'), 'neutral': ('Neutral', 'neutral')}
OLD_GUIDE = ROOT / 'research/endorsements/peace-guides-2026-10-09.json'


class FlightParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.inside = False; self.scripts = []; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag == 'script': self.inside = True; self.parts = []
    def handle_data(self, text):
        if self.inside: self.parts.append(text)
    def handle_endtag(self, tag):
        if tag == 'script' and self.inside:
            self.scripts.append(''.join(self.parts)); self.inside = False


def source_cards(html):
    parser = FlightParser(); parser.feed(html)
    chunks = []
    for script in parser.scripts:
        match = re.fullmatch(r'self\.__next_f\.push\((.*)\)', script, re.S)
        if match:
            value = json.loads(match[1])
            if len(value) > 1 and isinstance(value[1], str): chunks.append(value[1])
    text = ''.join(chunks); decoder = json.JSONDecoder(); rows = {}
    for match in re.finditer(r'\{\s*"id"\s*:\s*"[^"]+"\s*,\s*"name"\s*:', text):
        value, _ = decoder.raw_decode(text[match.start():])
        if 'our_rating' not in value: continue
        for key in ('id','name','slug','office_title','our_rating'):
            if not isinstance(value.get(key), str) or not value[key]: raise ValueError('Incomplete source card: '+key)
        if value['our_rating'] not in LABELS: raise ValueError('Unknown Vote for Peace rating: '+value['our_rating'])
        card = {k:value.get(k) for k in ('id','name','slug','state_abbr','office_title','district','jurisdiction',
                                        'level','our_rating','election_stage','election_date','election_result')}
        if card['id'] in rows and rows[card['id']] != card: raise ValueError('Conflicting source ID: '+card['id'])
        rows[card['id']] = card
    if not rows: raise ValueError('No candidate cards; source layout may have changed')
    return sorted(rows.values(), key=lambda r:(r['state_abbr'] or '',r['slug'],r['id']))


def state_of(position):
    match = re.search(r'state:(\w\w)', position.get('ocd_division_id') or '')
    return match[1].upper() if match else ('CA' if position.get('counties') else '')


def same_office(position, card):
    title = norm(card['office_title']); seat = position.get('district_or_seat') or ''
    if position['office_category'] == 'U.S. Senate': return title in {'u s senator','u s senate'}
    if position['office_category'] == 'U.S. House':
        return title in {'u s representative','u s house'} and str(card.get('district')) == seat.removeprefix('CD-')
    if position['office_category'] == 'State Assembly':
        return title == 'state assembly member' and str(card.get('district')) == seat.removeprefix('AD-')
    if not position.get('counties'):
        return norm(position['office']) == title
    context = card['office_title']+' '+str(card.get('jurisdiction') or '')
    if card.get('district'): context += ' District '+str(card['district'])
    return office_matches({'seat':seat,'office':position['office'],'jurisdiction':position['jurisdiction'],
                           'term':position.get('term')}, context)


def name_key(name):
    return re.sub(r'^(?:dr|rep|senator|representative) ', '', norm(name))


def draft(data, capture, review_id):
    checked = capture['checked_on']; aliases = {}
    for old in json.loads(OLD_GUIDE.read_text())['vote_for_peace_cards']:
        if old.get('position_id') and old.get('candidate') and old['action'] in {'publish','neutral_no_recommendation'}:
            aliases.setdefault(name_key(old['source_name']),set()).add((old['position_id'],old['candidate']))
    targets = []
    for p in data['positions']:
        if p.get('ballot_status') == 'excluded': continue
        for roster in ('candidates','filed_candidates_not_confirmed_on_ballot','qualified_write_in_candidates'):
            for c in p.get(roster) or []: targets.append((p,c,roster))
    sources = {}; decisions = []; dispositions = []; bound = set()
    note_id = 'N'+str(max(int(k[1:]) for k in data['notes'])+1)
    for card in capture['cards']:
        key = name_key(card['name']); proposals = [(p,c,r) for p,c,r in targets
            if state_of(p) == card['state_abbr'] and (name_key(c['name']) == key or
                (p['id'],c['name']) in aliases.get(key,set()))]
        matches = [(p,c,r) for p,c,r in proposals if same_office(p,card)]
        label, relation = LABELS[card['our_rating']]
        base = {'source_id':card['id'],'source_name':card['name'],'state':card['state_abbr'],
                'office':card['office_title'],'district':card.get('district'),'label':label,
                'phase':card['election_stage'],'election_date':card['election_date']}
        if not re.search(r'\b'+data['election']['date'][:4]+r'\b',card['election_date'] or '') or card['election_stage'] not in {'general','primary'}:
            dispositions.append({**base,'action':'hold','reason':'Election year/phase is outside this cycle or unsupported.'}); continue
        if len(matches) != 1:
            dispositions.append({**base,'action':'hold','reason':'No unique exact name/state/office/seat binding in the active roster.',
                                 'proposed_ids':[p['id'] for p,c,r in proposals]}); continue
        p,c,roster = matches[0]; binding = (p['id'],c['name'],card['election_stage'])
        if binding in bound: raise ValueError('Multiple source cards target the same candidacy/phase')
        bound.add(binding)
        source_key = 'vfp-'+card['id']
        # Listing is the captured first-party source. The profile slug is retained
        # in the normalized capture; the review never claims a profile was fetched.
        sources[source_key] = {'url':URL,'publisher':'Vote for Peace','role':'endorser','checked_on':checked,
                              'content_sha256':capture['content_sha256'],
                              'retrieval':'Captured first-party candidates HTML; decoded Next.js source card '+card['id']}
        prior = [r for r in c.get('endorsements') or [] if r['endorser']=='Vote for Peace'
                 and r['phase']==card['election_stage'] and not r.get('historical')]
        if len(prior)>1: raise ValueError('Ambiguous prior Vote for Peace records: '+c['name'])
        record = {'endorser':'Vote for Peace','kind':'organization','relation':relation,'phase':card['election_stage'],
                  'url':URL,'checked_on':checked,'quote':label,'verification':'endorser_statement','note_id':note_id}
        if label=='Ally': record['rating']='Ally'
        dispositions.append({**base,'action':'matched','position_id':p['id'],'candidate':c['name'],'roster':roster})
        decisions.append({'id':source_key,'action':'change','source_key':source_key,'position_id':p['id'],'candidate':c['name'],
            'identity':identity(p),'field':'endorsements','before':prior[0] if prior else None,'after':record,
            'reason':'Refresh exact first-party rating with matching state, office and seat; preserve election phase.',
            'evidence':{'identity_basis':'Exact normalized ballot/source name (or prior reviewed alias), state, office and district/seat.',
                        'date_basis':'Source explicitly identifies '+card['election_stage']+' election '+card['election_date']+'; check date is observation only.',
                        'relationship_basis':'First-party our_rating '+card['our_rating']+' renders as '+label+'; copied without interpreting other organizations listed on the card.'}})
    review = {'version':1,'id':review_id,'election_date':data['election']['date'],'reviewed_on':checked,
              'counties':[c['name'] if isinstance(c,dict) else c for c in data['election']['counties_in_scope']],'base_dataset_sha256':hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
              'sources':sources,'notes':{note_id:'Vote for Peace first-party guide observed '+checked+'. Ally is a support classification, not a formal endorsement; Neutral is not support. Election phase is retained. Organizations listed by this aggregator are not imported as their own endorsements.'},'decisions':decisions}
    return review, {'source_url':URL,'checked_on':checked,'capture_sha256':capture['content_sha256'],
                    'counts':dict(Counter(d['action'] for d in dispositions)),'cards':dispositions}


def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    c=sub.add_parser('capture');c.add_argument('--html',type=Path);c.add_argument('--checked-on',default=date.today().isoformat());c.add_argument('--output',type=Path,required=True)
    r=sub.add_parser('review');r.add_argument('--capture',type=Path,required=True);r.add_argument('--dataset',type=Path,default=ROOT/'2026-11-03_Bay_Area_Elections.json');r.add_argument('--id',required=True);r.add_argument('--output',type=Path,required=True);r.add_argument('--dispositions',type=Path,required=True)
    args=ap.parse_args()
    outputs=[args.output] if args.command=='capture' else [args.output,args.dispositions]
    if any(p.exists() for p in outputs): raise ValueError('Preserve dated captures/reviews; choose unused output paths')
    if args.command=='capture':
        if date.fromisoformat(args.checked_on)>date.today(): raise ValueError('Future check date')
        raw=args.html.read_bytes() if args.html else urllib.request.urlopen(URL,timeout=90).read()
        result={'version':1,'source_url':URL,'checked_on':args.checked_on,'content_sha256':hashlib.sha256(raw).hexdigest(),'cards':source_cards(raw.decode())}
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n')
        print(json.dumps({'captured':len(result['cards'])}))
    else:
        review,dispositions=draft(json.loads(args.dataset.read_text()),json.loads(args.capture.read_text()),args.id)
        for p,value in [(args.output,review),(args.dispositions,dispositions)]:
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=1)+'\n')
        print(json.dumps(dispositions['counts']))


if __name__=='__main__':main()
