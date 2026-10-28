"""Offline BAMC Action / activist source-fidelity, identity and state regressions."""
from copy import deepcopy
from collections import Counter
import json
from pathlib import Path
import unittest

import sync_bamc_action as bamc
import grade_gaza as grading
import serve_jev_playground as playground
from ballotpedia_endorsements import digest, dump

ROOT=Path(__file__).resolve().parent.parent
PACKET=ROOT/'research/endorsements/bamc-action-2026-10-27.json'
REVIEW=ROOT/'research/reviews/bamc-action-candidates-2026-10-27.json'


def fixture():
    official={'page':{'slug':'bamc-action','label':'BAMC Action','picks':{'race':['a'],'prop':['yes']},'avoids':{'race':['b']},'notes':{}}}
    board={'picks':{'race':['b']},'avoids':{'race':['a','c']},'notes':{'race/c':'Vote only for two.','race/a':'A community supporter.'}}
    samir={'slug':'samir','label':'Samir','picks':{'race':['b']},'avoids':{'race':['a']},'notes':{'race/b':'Support a challenger to pressure the incumbent.'}}
    catalog={'election':{'date':'2026-11-03'},'counties':[{'id':'test','name':'Test'}],
             'contests':[{'id':'race','title':'Council District 1','jurisdiction':'Example','countyIds':['test'],'kind':'multiple','category':'local','options':[{'id':v,'label':v.upper()} for v in 'abcd']},
                         {'id':'prop','title':'Proposition','jurisdiction':'CA','countyIds':['test'],'kind':'yes-no','category':'measure','options':[{'id':'yes','label':'Yes'}]}]}
    return official,board,catalog,samir


def captured(values):
    official,board,catalog,samir=values
    return bamc.capture(*(json.dumps(v).encode() for v in (official,board,catalog)),'2026-10-27',json.dumps(samir).encode())


class GuideChecks(unittest.TestCase):
    def test_source_polarities_and_comment_only_are_independent(self):
        result=captured(fixture());cards={(c['endorser'],c['option_id']):c for c in result['cards']}
        self.assertEqual(cards['BAMC Action','a']['relation'],'supported')
        self.assertEqual(cards['BAMC Action','b']['relation'],'opposed')
        self.assertEqual(cards['BAMC Action','c']['relation'],'comment')
        self.assertNotIn(('BAMC Action','d'),cards)
        self.assertEqual(cards['Samir Laymoun','a']['relation'],'opposed')
        self.assertEqual(cards['Samir Laymoun','b']['relation'],'supported')
        self.assertEqual(cards['BAMC Action','c']['comments'][0]['text'],'Vote only for two.')
        self.assertEqual(result['ignored_non_candidate_contests'],['prop'])
        self.assertTrue(all(c['contest_id']!='prop' for c in result['cards']))

    def test_fail_closed_on_conflicts_unknown_ids_and_cycle(self):
        for change in ('conflict','option','cycle','source'):
            values=fixture();official,board,catalog,samir=values
            if change=='conflict':official['page']['avoids']['race'].append('a')
            elif change=='option':samir['picks']['race']=['missing']
            elif change=='cycle':catalog['election']['date']='2024-11-05'
            else:official['page']['slug']='unrelated'
            with self.assertRaises(ValueError):captured(values)

    def test_all_real_source_rows_match_and_refresh_does_not_duplicate(self):
        packet=json.loads(PACKET.read_text());data=json.loads(bamc.DATASET.read_text())
        review,dispositions=bamc.draft(data,packet,'bamc-refresh-fixture')
        self.assertEqual(dispositions['counts'],{'matched':96})
        self.assertEqual(review['decisions'],[])
        totals=Counter((c['endorser'],c['relation']) for c in packet['cards'])
        self.assertEqual(totals,Counter({('BAMC Action','supported'):16,('BAMC Action','opposed'):2,('BAMC Action','comment'):2,('Samir Laymoun','supported'):38,('Samir Laymoun','opposed'):38}))
        self.assertEqual(sum(len(c['comments']) for c in packet['cards']),21)

    def test_wrong_district_is_held_even_when_name_is_exact(self):
        packet=json.loads(PACKET.read_text());packet['cards']=[deepcopy(next(c for c in packet['cards'] if c['name']=='AZIZ AKBARI'))]
        for key in ('title','jurisdiction'):packet['cards'][0][key]=packet['cards'][0][key].replace('#4','#9')
        review,dispositions=bamc.draft(json.loads(bamc.DATASET.read_text()),packet,'bamc-wrong-seat-fixture')
        self.assertEqual(review['decisions'],[]);self.assertEqual(dispositions['counts'],{'hold':1})

    def test_every_comment_and_position_reaches_new_states(self):
        data=json.loads(bamc.DATASET.read_text());review=json.loads(REVIEW.read_text())
        people={(p['id'],c['name']):(p,c) for p in data['positions'] for c in p.get('candidates') or []}
        for decision in review['decisions']:
            p,c=people[decision['position_id'],decision['candidate']];record=decision['after']
            self.assertIn(record,c['endorsements'])
            state=grading.build_state(p,c,data)
            observed=[e for e in state['focused_endorsement_observations'] if e['endorser']==record['endorser']]
            self.assertEqual(len(observed),1);self.assertEqual(observed[0]['relation'],record['relation'])
            self.assertEqual(observed[0].get('comments',[]),[q['text'] for q in record.get('comments',[])])
        self.assertEqual(grading.STATE_VERSION,'candidate-evidence-v17-bamc-action-comments')
        self.assertEqual(playground.STATE_VERSION,grading.STATE_VERSION+'-local-federal')

    def test_different_race_choices_and_ambiguous_comment_attachment_are_preserved(self):
        data=json.loads(bamc.DATASET.read_text());p=next(p for p in data['positions'] if p['id']=='CA2026-005')
        context=grading.community_guide_race_context(p)
        self.assertEqual({r['source']:r['supports'] for r in context['selections']},
                         {'BAMC Action':['Sam Liccardo'],'Samir Laymoun':['Peter Sundin Soulé']})
        activist=[r for r in context['comments'] if r['source']=='Samir Laymoun']
        self.assertEqual(activist[0]['listed_under'],'Peter Sundin Soulé')
        for candidate in p['candidates']:
            self.assertEqual(grading.build_state(p,candidate,data)['community_guide_race_context'],context)
        p=next(p for p in data['positions'] if p['id']=='CA2026-004')
        self.assertIsNone(grading.community_guide_race_context(p))

    def test_jev_review_is_bound_and_all_final_identities_are_supported(self):
        review=json.loads(REVIEW.read_text());path=ROOT/review['audit_path']
        self.assertEqual(digest(path.read_bytes()),review['audit_sha256'])
        audit=json.loads(path.read_text());final={}
        for batch in audit['batches']+audit.get('followups',[]):
            self.assertEqual(batch['request_sha256'],digest(dump(batch['request']).encode()))
            grading.validate_response(batch['request']['questions'],batch['response'])
            for qid,item in batch['item_ids'].items():final[item]=batch['response']['answers'][qid]['choice']
        self.assertEqual(set(final),{d['id'] for d in review['decisions']})
        self.assertTrue(all(value=='supported' for value in final.values()))


if __name__=='__main__':unittest.main()
