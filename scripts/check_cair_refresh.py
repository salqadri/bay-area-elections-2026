"""CAIR state-guide parsing, polarity, identity gating and additive refresh regressions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import refresh_cair_guide as cair
from ballotpedia_endorsements import dump, digest, save, MODEL
from reviewed_updates import prepare

ROOT=Path(__file__).resolve().parent.parent
PACKET=ROOT/'research/endorsements/cair-california-2026-10-23.json'
REVIEW=ROOT/'research/reviews/cair-california-general-2026-10-23.json'


class ParserChecks(unittest.TestCase):
    def page(self,level='PREFERRED',missing=False):
        words=[]
        def word(text,x,y,size,bold=True):
            words.append({'text':text,'x0':x,'x1':x+20,'top':y,'bottom':y+size,'fontname':'Font-Bold'if bold else'Font','size':size})
        word('MAYOR',30,45,14);word('Kevin',85,86,10);word('Park',85,97,10)
        word('Mayor, Santa Clara',85,109,8,False);word(level,85,127,6.375)
        page=MagicMock();page.width=612;page.height=792
        page.extract_text.return_value='2026 California General GENERAL ELECTION: 11/3/26'
        page.extract_words.return_value=words
        page.rects=[{'x0':23,'x1':588,'top':40,'bottom':65,'width':565,'height':25,'non_stroking_color':(.3,.5,.7)}]
        if not missing:page.rects.append({'x0':23,'x1':205,'top':75,'bottom':145,'width':182,'height':70,'non_stroking_color':(1.,1.,1.)})
        return page
    def parse(self,page):
        pdf=MagicMock();pdf.pages=[page]
        with patch('pdfplumber.open')as open_:open_.return_value.__enter__.return_value=pdf;return cair.capture_pdf(b'%PDF-fixture','2026-10-23')
    def test_multiline_name_and_column_bounded_label(self):
        packet=self.parse(self.page());self.assertEqual(packet['cards'][0]['name'],'Kevin Park')
        self.assertEqual(packet['cards'][0]['office'],'Mayor, Santa Clara');self.assertEqual(packet['cards'][0]['level'],'Preferred')
        self.assertEqual(packet['phase'],'general');self.assertEqual(packet['election_date'],'2026-11-03')
    def test_unknown_label_missing_card_and_wrong_election_fail_closed(self):
        for page in (self.page('MAYBE'),self.page(missing=True)):
            with self.assertRaises(ValueError):self.parse(page)
        page=self.page();page.extract_text.return_value='California Primary 2026'
        with self.assertRaises(ValueError):self.parse(page)
        with self.assertRaises(ValueError):cair.capture_pdf(b'<html>not PDF</html>','2026-10-23')


class RefreshChecks(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(cair.DATA.read_text());self.packet=json.loads(PACKET.read_text())
        self.card=next(c for c in self.packet['cards']if c['name']=='Kevin Park')
        self.packet.update(cards=[self.card],card_count=1,level_counts={'Preferred':1})
        self.p,self.c=next((p,c)for p in self.data['positions']for c in p.get('candidates')or[]if c['name']=='Kevin Park')
        self.c['endorsements']=[r for r in self.c.get('endorsements',[])if r['endorser']!='CAIR Action']
    def build(self,choice=None,probability=1):
        def ask(work,state,questions,key):
            context=json.loads(state);selected=choice if choice is not None else next(k for k,c in context['candidates'].items()if c['name']=='Kevin Park')
            probs={k:probability if k==selected else 0 for k in questions['identity']['criteria']}
            response={'model':MODEL,'answers':{'identity':{'type':'choice','choice':selected,'probabilities':probs}}}
            request={'model':MODEL,'state':state,'questions':questions};ref=digest(dump(request).encode());save(work/'decisions'/(ref+'.json'),{'request':request,'response':response})
            return response['answers'],ref
        with tempfile.TemporaryDirectory()as temp,patch.object(cair,'ask',ask),patch.object(cair,'prepare'):
            return cair.build(self.data,self.packet,Path(temp),'FIXTURE','fixture-cair-refresh',workers=1)[0]
    def test_missing_preference_added_without_changing_other_publishers(self):
        before=deepcopy(self.data);review=self.build();decision=review['decisions'][0]
        self.assertIsNone(decision['before']);self.assertEqual(decision['after']['relation'],'preferred')
        self.assertEqual(decision['after']['phase'],'general');self.assertEqual(self.data,before)
        proposed,_=prepare(self.data,review,[],validate=False)
        others=lambda data:[r for p in data['positions']for c in p.get('candidates')or[]if c['name']=='Kevin Park'for r in c.get('endorsements',[])if r['endorser']!='CAIR Action']
        self.assertEqual(others(proposed),others(before))
    def test_existing_old_tier_replaced_once_and_identical_refresh_is_unchanged(self):
        original={'endorser':'CAIR Action','kind':'organization','relation':'endorsed','phase':'unspecified',
                  'url':'https://cairactionguide.org/explore','checked_on':'2026-10-09','verification':'endorser_statement','note_id':'N295'}
        self.c.setdefault('endorsements',[]).append(original)
        review=self.build();self.assertEqual(review['decisions'][0]['before'],original)
        self.data,_=prepare(self.data,review,[],validate=False)
        repeated=self.build();self.assertTrue(all(d['action']=='hold'for d in repeated['decisions']))
        again,_=prepare(self.data,repeated,[],validate=False);self.assertEqual(again,self.data)
    def test_model_mismatch_or_ambiguous_identity_never_publishes(self):
        self.assertFalse(self.build(choice='none')['decisions'])
        self.assertFalse(self.build(probability=.5)['decisions'])
    def test_joint_and_opposed_retain_distinct_polarity(self):
        for level,raw,relation,shared in [('Joint Endorsement','JOINT ENDORSEMENT','endorsed',True),('Opposed','OPPOSE','opposed',False)]:
            self.packet['cards'][0].update(level=level,source_label=raw);self.packet['level_counts']={level:1}
            record=self.build()['decisions'][0]['after'];self.assertEqual(record['relation'],relation);self.assertEqual(bool(record.get('shared')),shared)
    def test_conflicting_duplicate_source_cards_are_held(self):
        other={**self.card,'id':'second','level':'Endorsed','source_label':'ENDORSED'}
        self.packet.update(cards=[self.card,other],card_count=2,level_counts={'Preferred':1,'Endorsed':1})
        review=self.build();self.assertFalse(review['decisions']);self.assertTrue(all(d['status']=='conflicting_source_levels'for d in review['card_dispositions']))
    def test_california_only_even_with_misleading_county_field(self):
        wrong={**self.p,'id':'TX-test','counties':['Alameda'],'ocd_division_id':'ocd-division/country:us/state:tx'}
        self.assertNotIn('TX-test',{p['id']for p in cair.california_positions({'positions':[wrong,self.p]})})


class PublishedChecks(unittest.TestCase):
    def test_all_cards_disposed_and_actual_model_requests_bind_published_changes(self):
        packet=json.loads(PACKET.read_text());review=json.loads(REVIEW.read_text());audit=json.loads(REVIEW.with_suffix('.audit.json').read_text())
        self.assertEqual(packet['card_count'],242);self.assertEqual(packet['level_counts'],{'Joint Endorsement':5,'Preferred':76,'Endorsed':160,'Opposed':1})
        self.assertEqual({c['id']for c in packet['cards']},{c['card_id']for c in review['card_dispositions']})
        self.assertEqual(packet['excluded_measure_pages'],list(range(28,35)))
        for decision in review['decisions']:
            saved=audit['decisions'][decision['jev_ref']];self.assertEqual(digest(dump(saved['request']).encode()),decision['jev_ref'])
            answer=saved['response']['answers']['identity'];self.assertTrue(cair.accepted(answer,{answer['choice']},.9))
            context=json.loads(saved['request']['state']);target=context['candidates'][answer['choice']]
            self.assertEqual((target['position_id'],target['name']),(decision['position_id'],decision['candidate']))
            self.assertEqual(decision['after']['relation'],cair.LEVELS[context['card']['level']])
    def test_kevin_preferred_opposition_and_unresolved_office_are_protected(self):
        data=json.loads(cair.DATA.read_text());records={c['name']:[r for r in c.get('endorsements',[])if r['endorser']=='CAIR Action']for p in data['positions']for c in p.get('candidates')or[]}
        self.assertEqual(len(records['Kevin Park']),1);self.assertEqual(records['Kevin Park'][0]['relation'],'preferred')
        self.assertEqual(records['Marc Cooper'][0]['relation'],'opposed');self.assertEqual(records['Tomara Hall'],[])
        self.assertEqual(records['Scott Sakakihara'][0]['relation'],'preferred');self.assertEqual(records['Mer Curry Nuñez'][0]['relation'],'preferred')

if __name__=='__main__':unittest.main()
