"""Capture BAMC Action candidate positions and supplementary board-guide comments.

Official and owner-authorized board-guide picks/avoids establish BAMC recommendations. Missing selections and
comments never imply opposition. Measures, propositions and retention yes/no
questions are excluded. Exact names plus county/office/seat bind candidacies;
unresolved identities are held. Apply through reviewed_updates, never directly.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import urllib.request

from ballotpedia_endorsements import digest, dump
from endorsement_extract import norm, office_matches
from publication_reviews import ROOT
from reviewed_updates import identity

OFFICIAL_URL = 'https://bamcaction.org/myvote/bamc-action'
OFFICIAL_API = 'https://bamcaction.org/api/myvote/organization/bamc-action'
COMMENT_URL = 'https://bamcaction.org/myvote/razim'
COMMENT_API = 'https://bamcaction.org/api/myvote/shared/razim'
SAMIR_URL = 'https://bamcaction.org/myvote/samir'
SAMIR_API = 'https://bamcaction.org/api/myvote/shared/samir'
CATALOG_API = 'https://bamcaction.org/api/myvote/catalog'
COMMENT_SUBJECT_REVIEW = ROOT / 'research/endorsements/comment-subjects-2026-10-28.json'
DATASET = ROOT / '2026-11-03_Bay_Area_Elections.json'


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0', 'Accept':'application/json', 'Referer':OFFICIAL_URL})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


def candidate_contest(contest):
    return contest.get('kind') != 'yes-no' and contest.get('category') not in {'measure','proposition'}


def capture(official_raw, comments_raw, catalog_raw, checked_on, samir_raw=None):
    official = json.loads(official_raw)['page']; board = json.loads(comments_raw); catalog = json.loads(catalog_raw)
    if official.get('slug') != 'bamc-action' or official.get('label') != 'BAMC Action':
        raise ValueError('Not the official BAMC Action organization page')
    if catalog['election']['date'] != '2026-11-03' or date.fromisoformat(checked_on) > date.today():
        raise ValueError('Wrong election cycle or future observation')
    contests = {c['id']:c for c in catalog['contests']}
    if len(contests) != len(catalog['contests']):
        raise ValueError('Duplicate catalog contest')
    sources = {
        'official': {'url':OFFICIAL_URL, 'api_url':OFFICIAL_API, 'publisher':'BAMC Action', 'role':'endorser',
                     'checked_on':checked_on, 'content_sha256':digest(official_raw),
                     'retrieval':'Public organization API backing the linked official guide; explicit picks/avoids only.'},
        'board-comments': {'url':COMMENT_URL, 'api_url':COMMENT_API, 'publisher':'BAMC Action', 'role':'endorser',
                          'checked_on':checked_on, 'content_sha256':digest(comments_raw),
                          'retrieval':'Public shared-guide API; candidate comments accepted as organization commentary at explicit owner direction. Explicit board-guide picks/avoids are accepted as BAMC positions at owner direction; conflicting guides are held.'},
        'catalog': {'url':CATALOG_API, 'publisher':'BAMC Action', 'role':'aggregator', 'checked_on':checked_on,
                    'content_sha256':digest(catalog_raw), 'retrieval':'Public candidate/contest catalog used for exact labels, offices, seats and election date.'}}
    # Notes are keyed contest/option, not nested dictionaries. Capture all candidate
    # comments, including comments about candidates with no official position.
    note_keys = set(official.get('notes',{})) | set(board.get('notes',{}))
    relevant = set(official.get('picks',{})) | set(official.get('avoids',{})) | set(board.get('picks',{})) | set(board.get('avoids',{}))
    for key in note_keys:
        if '/' not in key: raise ValueError('Unknown comment key format')
        relevant.add(key.rsplit('/',1)[0])
    cards = []; skipped = []
    for cid in sorted(relevant):
        if cid not in contests: raise ValueError('Unknown source contest: '+cid)
        contest = contests[cid]
        if not candidate_contest(contest):
            skipped.append(cid); continue
        options = {o['id']:o for o in contest['options']}
        if len(options) != len(contest['options']): raise ValueError('Duplicate candidate option')
        picks = official.get('picks',{}).get(cid,[]); avoids = official.get('avoids',{}).get(cid,[])
        board_picks = board.get('picks',{}).get(cid,[]); board_avoids = board.get('avoids',{}).get(cid,[])
        if set(picks) & set(avoids): raise ValueError('Official support/opposition conflict')
        if set(board_picks) & set(board_avoids): raise ValueError('Board support/opposition conflict')
        if set(picks) & set(board_avoids) or set(avoids) & set(board_picks):
            raise ValueError('BAMC guides explicitly conflict; review before choosing a position')
        ids = set(picks) | set(avoids) | set(board_picks) | set(board_avoids) | {key.rsplit('/',1)[1] for key in note_keys if key.rsplit('/',1)[0] == cid}
        if not ids <= options.keys(): raise ValueError('Unknown source candidate option')
        for oid in sorted(ids):
            comments = []
            for owner, url in ((official,OFFICIAL_URL),(board,COMMENT_URL)):
                text = owner.get('notes',{}).get(cid+'/'+oid)
                if text is not None and not isinstance(text,str): raise ValueError('Non-text candidate comment')
                if text and text.strip() and text not in {c['text'] for c in comments}:
                    comments.append({'text':text, 'url':url})
            relation = 'supported' if oid in picks or oid in board_picks else 'opposed' if oid in avoids or oid in board_avoids else 'comment'
            position_source = 'official' if oid in picks or oid in avoids else 'board-comments'
            if relation == 'comment' and not comments: continue
            cards.append({'id':'bamc/'+cid+'/'+oid, 'endorser':'BAMC Action', 'contest_id':cid, 'option_id':oid, 'name':options[oid]['label'],
                          'title':contest['title'], 'jurisdiction':contest['jurisdiction'],
                          'county_ids':contest['countyIds'], 'kind':contest['kind'],
                          'relation':relation, 'position_source':position_source, **({'rank':picks.index(oid)+1} if contest['kind']=='ranked' and oid in picks else {}),
                          'comments':comments})
    if samir_raw is not None:
        activist = json.loads(samir_raw)
        if activist.get('slug') != 'samir' or activist.get('label') != 'Samir':
            raise ValueError('Not the owner-identified activist guide')
        sources['activist'] = {'url':SAMIR_URL, 'api_url':SAMIR_API, 'publisher':'Samir Laymoun', 'role':'endorser',
                              'checked_on':checked_on, 'content_sha256':digest(samir_raw),
                              'retrieval':'Public activist shared-guide API; full author name supplied by owner. Personal picks/avoids and comments are distinct from BAMC Action positions.'}
        relevant = set(activist.get('picks',{})) | set(activist.get('avoids',{}))
        relevant |= {key.rsplit('/',1)[0] for key in activist.get('notes',{})}
        for cid in sorted(relevant):
            if cid not in contests: raise ValueError('Unknown activist contest: '+cid)
            contest = contests[cid]
            if not candidate_contest(contest):
                skipped.append(cid); continue
            options = {o['id']:o for o in contest['options']}
            picks = activist.get('picks',{}).get(cid,[]); avoids = activist.get('avoids',{}).get(cid,[])
            if set(picks) & set(avoids): raise ValueError('Activist support/opposition conflict')
            ids = set(picks) | set(avoids) | {key.rsplit('/',1)[1] for key in activist.get('notes',{}) if key.rsplit('/',1)[0] == cid}
            if not ids <= options.keys(): raise ValueError('Unknown activist candidate option')
            for oid in sorted(ids):
                text = activist.get('notes',{}).get(cid+'/'+oid)
                if text is not None and not isinstance(text,str): raise ValueError('Non-text activist comment')
                comments = [{'text':text,'url':SAMIR_URL}] if text and text.strip() else []
                relation = 'supported' if oid in picks else 'opposed' if oid in avoids else 'comment'
                cards.append({'id':'samir/'+cid+'/'+oid, 'endorser':'Samir Laymoun', 'contest_id':cid, 'option_id':oid,
                              'name':options[oid]['label'], 'title':contest['title'], 'jurisdiction':contest['jurisdiction'],
                              'county_ids':contest['countyIds'], 'kind':contest['kind'], 'relation':relation,
                              **({'rank':picks.index(oid)+1} if contest['kind']=='ranked' and oid in picks else {}), 'comments':comments})
    if not cards: raise ValueError('No candidate recommendations/comments; inspect source layout')
    return {'version':3, 'policy':'bamc-action-candidates-v3', 'election_date':catalog['election']['date'],
            'checked_on':checked_on, 'official_updated_at':official.get('updatedAt'),
            'comment_updated_at':board.get('updatedAt'), 'sources':sources,
            'source_counties':{c['id']:c['name'] for c in catalog['counties']},
            'ignored_non_candidate_contests':sorted(set(skipped)),
            'candidate_options':{cid:{o['id']:o['label'] for o in contests[cid]['options']} for cid in sorted({card['contest_id'] for card in cards})}, 'cards':cards}


def resolve_comment_subjects(packet, review=None):
    """Apply exact, reviewed comment subjects; never infer a subject from a pronoun."""
    from copy import deepcopy
    review = json.loads(COMMENT_SUBJECT_REVIEW.read_text()) if review is None else review
    rules = {(r['source_card_id'],r['url'],r['text_sha256']):r for r in review['comments']}
    if len(rules) != len(review['comments']): raise ValueError('Duplicate comment-subject rule')
    cards = {r['id']:deepcopy(r) for r in packet['cards']}
    if len(cards) != len(packet['cards']): raise ValueError('Duplicate source card')
    moved = []
    for source in packet['cards']:
        current = cards[source['id']]
        current['comments'] = []
        for comment in source['comments']:
            ref = digest(comment['text'].encode())
            rule = rules.get((source['id'],comment['url'],ref))
            if rule is None: raise ValueError('Comment needs subject review before publication: '+source['id'])
            target = rule['subject_option_id']; options = packet['candidate_options'][source['contest_id']]
            if target not in options: raise ValueError('Reviewed comment subject outside source contest')
            target_id = source['id'].rsplit('/',1)[0]+'/'+target
            if target_id == source['id']:
                current['comments'].append(deepcopy(comment));continue
            if target_id not in cards:
                row = deepcopy(source);row.update(id=target_id,option_id=target,name=options[target],relation='comment',comments=[])
                row.pop('rank',None);cards[target_id]=row
            # Incoming comments must survive regardless of source iteration order.
            moved.append((target_id,deepcopy(comment)))
            if rule.get('recommendation_context'):
                current['recommendation_context']=rule['recommendation_context']
    for target_id,comment in moved:
        if comment not in cards[target_id]['comments']:cards[target_id]['comments'].append(comment)
    return sorted(cards.values(),key=lambda c:c['id'])


def office_context(card):
    text = card['title']+' '+card['jurisdiction']
    text = re.sub(r'United States Representative', 'Congress', text, flags=re.I)
    text = re.sub(r'State Senator', 'State Senate', text, flags=re.I)
    text = re.sub(r'(?<!State )Board of Equalization Member', 'California State Board of Equalization Member', text, flags=re.I)
    return re.sub(r'#\s*(\d+)', r'District \1', text)


def matches_office(position, card, county_names):
    if not set(position.get('counties',[])) & set(county_names): return False
    return office_matches({'seat':position.get('district_or_seat',''), 'office':position['office'],
                           'jurisdiction':position['jurisdiction'], 'term':position.get('term')}, office_context(card))


def draft(data, packet, review_id):
    if data['election']['date'] != packet['election_date']: raise ValueError('Election mismatch')
    targets = [(p,c) for p in data['positions'] if p.get('ballot_status') != 'excluded' for c in p.get('candidates') or []]
    note_id = 'N'+str(max(int(k[1:]) for k in data['notes'])+1)
    decisions = []; dispositions = []; seen = set()
    for card in resolve_comment_subjects(packet):
        counties = [packet['source_counties'][c] for c in card['county_ids']]
        matches = [(p,c) for p,c in targets if norm(c['name']) == norm(card['name']) and matches_office(p,card,counties)]
        if len(matches) != 1:
            dispositions.append({**card,'action':'hold','reason':'No unique exact name/county/office/seat binding.'});continue
        p,c = matches[0]; key = p['id'],c['name'],card['endorser']
        if key in seen: raise ValueError('Multiple source cards bind one candidacy')
        seen.add(key)
        prior = [e for e in c.get('endorsements',[]) if e['endorser']==card['endorser'] and e['phase']=='general' and not e.get('historical')]
        if len(prior)>1: raise ValueError('Ambiguous prior BAMC Action records')
        source_key = 'activist' if card['endorser']=='Samir Laymoun' else card.get('position_source','board-comments' if card['relation']=='comment' else 'official')
        record = {'endorser':card['endorser'],'kind':'person' if card['endorser']=='Samir Laymoun' else 'organization','relation':card['relation'],'phase':'general',
                  'url':packet['sources'][source_key]['url'],'checked_on':packet['checked_on'],
                  'verification':'endorser_statement','note_id':note_id}
        if card['comments']: record['comments'] = card['comments']
        if card.get('rank'):record['recommendation_rank']=card['rank']
        if card.get('recommendation_context'):record['recommendation_context']=card['recommendation_context']
        dispositions.append({'source_id':card['id'],'candidate':c['name'],'position_id':p['id'],'endorser':card['endorser'],'relation':card['relation'],'comments':len(card['comments']),'action':'matched'})
        if prior and {k:v for k,v in prior[0].items() if k not in {'checked_on','note_id'}} == {k:v for k,v in record.items() if k not in {'checked_on','note_id'}}:continue
        decisions.append({'id':card['id'],'action':'change','source_key':source_key,'position_id':p['id'],'candidate':c['name'],
                          'identity':identity(p),'field':'endorsements','before':prior[0] if prior else None,'after':record,
                          'reason':'Copy the identified source explicit support/opposition, or preserve commentary without inferring a recommendation. Retain complete candidate comments.',
                          'evidence':{'identity_basis':'Exact normalized name, county, office/jurisdiction and district/seat from publisher catalog.',
                                      'date_basis':'Publisher catalog explicitly identifies the November 3, 2026 election; check date is retrieval, not endorsement date.',
                                      'relationship_basis':'Official picks mean support; official avoids mean opposition. Comment-only records assert neither support nor opposition. Board-guide explicit picks/avoids are owner-authorized as BAMC Action positions; a conflicting official guide requires review. Activist records copy only the activist selections and comments.'}})
    review = {'version':1,'id':review_id,'election_date':packet['election_date'],'reviewed_on':packet['checked_on'],
              'counties':[c['name'] if isinstance(c,dict) else c for c in data['election']['counties_in_scope']],'base_dataset_sha256':digest(dump(data).encode()),
              'sources':packet['sources'],'notes':{note_id:'BAMC Action is the owner-designated trusted Bay Area Muslim Council recommendation source. Support/opposition is copied from its official organization guide and owner-authorized board guide. Supplementary board-guide candidate comments are included at owner direction; they may concern local suitability or tactical voting and do not independently establish a Palestine position. Comment-only entries are not endorsements, neutrality ratings or opposition. Samir Laymoun is a separately attributed activist opinion source, not an official BAMC Action position. Comments are assigned to their reviewed candidate subjects, not automatically to the candidate under whose ballot option they were posted. Protest-vote support is marked as tactical. Propositions and ballot measures are excluded.'},'decisions':decisions}
    return review, {'version':1,'counts':dict(Counter(r['action'] for r in dispositions)),'cards':dispositions}


def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    c=sub.add_parser('capture');c.add_argument('--checked-on',default=date.today().isoformat());c.add_argument('--output',type=Path,required=True)
    r=sub.add_parser('review');r.add_argument('--capture',type=Path,required=True);r.add_argument('--id',required=True);r.add_argument('--output',type=Path,required=True);r.add_argument('--dispositions',type=Path,required=True)
    args=ap.parse_args();paths=[args.output] if args.command=='capture' else [args.output,args.dispositions]
    if any(p.exists() for p in paths):raise ValueError('Preserve dated captures/reviews; use unused output paths')
    if args.command=='capture':values=[capture(fetch(OFFICIAL_API),fetch(COMMENT_API),fetch(CATALOG_API),args.checked_on,fetch(SAMIR_API))]
    else:values=list(draft(json.loads(DATASET.read_text()),json.loads(args.capture.read_text()),args.id))
    for path,value in zip(paths,values):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=1)+'\n')
    print(json.dumps({'written':[str(p) for p in paths]}))


if __name__=='__main__':main()
