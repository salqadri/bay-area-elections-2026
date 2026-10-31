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
PACKET=ROOT/'research/endorsements/bamc-action-2026-10-28.json'
REVIEW=ROOT/'research/reviews/bamc-action-candidates-2026-10-27.json'


def fixture():
    official={'page':{'slug':'bamc-action','label':'BAMC Action','picks':{'race':['a'],'prop':['yes']},'avoids':{'race':['b']},'notes':{}}}
    board={'picks':{'race':['a']},'avoids':{'race':['c']},'notes':{'race/c':'Vote only for two.','race/a':'A community supporter.','race/d':'Comment without a recommendation.'}}
    samir={'slug':'samir','label':'Samir','picks':{'race':['b']},'avoids':{'race':['a']},'notes':{'race/b':'Support a challenger to pressure the incumbent.'}}
    catalog={'election':{'date':'2026-11-03'},'counties':[{'id':'test','name':'Test'}],
             'contests':[{'id':'race','title':'Council District 1','jurisdiction':'Example','countyIds':['test'],'kind':'multiple','category':'local','options':[{'id':v,'label':v.upper()} for v in 'abcde']},
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
        self.assertEqual(cards['BAMC Action','c']['relation'],'opposed')
        self.assertEqual(cards['BAMC Action','d']['relation'],'comment')
        self.assertNotIn(('BAMC Action','e'),cards)
        self.assertEqual(cards['Samir Laymoun','a']['relation'],'opposed')
        self.assertEqual(cards['Samir Laymoun','b']['relation'],'supported')
        self.assertEqual(cards['BAMC Action','c']['comments'][0]['text'],'Vote only for two.')
        self.assertEqual(result['ignored_non_candidate_contests'],['prop'])
        self.assertTrue(all(c['contest_id']!='prop' for c in result['cards']))

    def test_fail_closed_on_conflicts_unknown_ids_and_cycle(self):
        for change in ('conflict','board_conflict','option','cycle','source'):
            values=fixture();official,board,catalog,samir=values
            if change=='conflict':official['page']['avoids']['race'].append('a')
            elif change=='board_conflict':board['avoids']['race'].append('a')
            elif change=='option':samir['picks']['race']=['missing']
            elif change=='cycle':catalog['election']['date']='2024-11-05'
            else:official['page']['slug']='unrelated'
            with self.assertRaises(ValueError):captured(values)

    def test_all_real_source_rows_match_and_refresh_does_not_duplicate(self):
        packet=json.loads(PACKET.read_text());data=json.loads(bamc.DATASET.read_text())
        review,dispositions=bamc.draft(data,packet,'bamc-refresh-fixture')
        self.assertEqual(dispositions['counts'],{'matched':97})
        self.assertEqual(review['decisions'],[])
        totals=Counter((c['endorser'],c['relation']) for c in bamc.resolve_comment_subjects(packet))
        self.assertEqual(totals,Counter({('BAMC Action','supported'):16,('BAMC Action','opposed'):4,('Samir Laymoun','supported'):38,('Samir Laymoun','opposed'):38,('Samir Laymoun','comment'):1}))
        self.assertEqual(sum(len(c['comments']) for c in packet['cards']),21)

    def test_removed_comments_create_an_explicit_review_instead_of_stale_reuse(self):
        packet=json.loads(PACKET.read_text())
        card=next(c for c in packet['cards'] if c['name']=='Kevin Park' and c['endorser']=='BAMC Action')
        card['comments']=[]
        review,_=bamc.draft(json.loads(bamc.DATASET.read_text()),packet,'bamc-comment-removal-fixture')
        edit=next(d for d in review['decisions'] if d['candidate']=='Kevin Park')
        self.assertIn('comments',edit['before']);self.assertNotIn('comments',edit['after'])

    def test_wrong_district_is_held_even_when_name_is_exact(self):
        packet=json.loads(PACKET.read_text());packet['cards']=[deepcopy(next(c for c in packet['cards'] if c['name']=='AZIZ AKBARI'))]
        for key in ('title','jurisdiction'):packet['cards'][0][key]=packet['cards'][0][key].replace('#4','#9')
        review,dispositions=bamc.draft(json.loads(bamc.DATASET.read_text()),packet,'bamc-wrong-seat-fixture')
        self.assertEqual(review['decisions'],[]);self.assertEqual(dispositions['counts'],{'hold':1})

    def test_every_reviewed_comment_and_position_reaches_only_its_subject(self):
        data=json.loads(bamc.DATASET.read_text());packet=json.loads(PACKET.read_text())
        targets=[(p,c) for p in data['positions'] for c in p.get('candidates') or []]
        for card in bamc.resolve_comment_subjects(packet):
            p,c=next((p,c) for p,c in targets if bamc.norm(c['name'])==bamc.norm(card['name']))
            state=grading.build_state(p,c,data)
            observation=next(e for e in state['focused_endorsement_observations'] if e['endorser']==card['endorser'])
            self.assertEqual(observation['relation'],card['relation'])
            self.assertEqual(observation.get('comments',[]),[q['text'] for q in card['comments']])
            self.assertNotIn('community_guide_race_context',state)
        self.assertEqual(grading.STATE_VERSION,'candidate-evidence-v22-cjd-identity-only')
        self.assertEqual(playground.STATE_VERSION,grading.STATE_VERSION+'-local-federal')

    def test_opposition_and_protest_comments_have_correct_subjects(self):
        data=json.loads(bamc.DATASET.read_text())
        states={c['name']:grading.build_state(p,c,data) for p in data['positions'] for c in p.get('candidates') or []
                if c['name'] in {'Steve Raspe','Heidi Owens','Peter Sundin Soulé','Sam Liccardo'}}
        for name in ('Steve Raspe','Heidi Owens'):
            obs=next(e for e in states[name]['focused_endorsement_observations'] if e['endorser']=='BAMC Action')
            self.assertEqual(obs['relation'],'opposed')
        peter=states['Peter Sundin Soulé'];sam=states['Sam Liccardo']
        obs=next(e for e in peter['focused_endorsement_observations'] if e['endorser']=='Samir Laymoun')
        self.assertEqual(obs['relation'],'supported');self.assertEqual(obs['recommendation_context'],'Protest-vote recommendation.')
        self.assertNotIn('comments',obs);self.assertNotIn('BAMC Action',[e['endorser'] for e in peter['focused_endorsement_observations']])
        self.assertNotIn('Sam Liccardo',json.dumps(peter))
        obs=next(e for e in sam['focused_endorsement_observations'] if e['endorser']=='Samir Laymoun')
        self.assertEqual(obs['relation'],'comment');self.assertIn('Reduce his winning margin',obs['comments'][0])
        self.assertNotIn('Peter Sundin',json.dumps(sam))
        self.assertTrue(all('community_guide_race_context' not in state for state in states.values()))

    def test_changed_comments_cannot_reuse_an_old_subject_decision(self):
        packet=json.loads(PACKET.read_text())
        card=next(c for c in packet['cards'] if c['id']=='samir/ca-congress-16/peter-sundin-soule')
        card['comments'][0]['text']+=' Changed source.'
        with self.assertRaisesRegex(ValueError,'needs subject review'):bamc.resolve_comment_subjects(packet)
        review=json.loads((ROOT/'research/reviews/community-guide-cleanup-2026-10-28.json').read_text())
        self.assertEqual(review['comment_subject_review_sha256'],digest(bamc.COMMENT_SUBJECT_REVIEW.read_bytes()))
        audit=ROOT/review['audit_path'];self.assertEqual(review['audit_sha256'],digest(audit.read_bytes()))
        evidence=json.loads(audit.read_text());self.assertEqual(evidence['request_sha256'],digest(dump(evidence['request']).encode()))
        self.assertTrue(all(a['choice']=='supported' for a in evidence['response']['answers'].values()))

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
