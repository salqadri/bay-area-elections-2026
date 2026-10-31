"""Offline editorial-source regressions; never call a model."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

import build_recommendations as recommendations
import generate_grade_explanations as generator
from summary_source_policy import policy_for_state, policy_for_candidate, prose_errors, SAMIR

ROOT = Path(__file__).resolve().parent.parent


class SummarySourceChecks(unittest.TestCase):
    def test_retired_grade_is_excluded_from_explanation_context_without_mutating_history(self):
        row = {'id': 'fixture', 'candidate': 'Fixture', 'request_sha256': '0' * 64,
               'request': {'state': {}, 'questions': {
                   'pro_palestine_score': {'type': 'score', 'criteria': list('012345')},
                   'gaza_grade': {'type': 'choice', 'criteria': {'A': 'Historical'}}}},
               'response': {'answers': {'pro_palestine_score': {'type': 'score', 'score': 1},
                                        'gaza_grade': {'type': 'choice', 'choice': 'A'}}}}
        before = deepcopy(row)
        payload = json.loads(generator.build_input(row, 'E', 'Prompt').split('\n\nSUPPLIED RECORD\n', 1)[1])
        self.assertNotIn('gaza_grade', payload['scoring_questions'])
        self.assertNotIn('gaza_grade', payload['recorded_response']['answers'])
        self.assertEqual(payload['recorded_response']['answers']['pro_palestine_score']['score'], 1)
        self.assertEqual(payload['displayed_grade'], 'E')
        self.assertEqual(row, before)

    def fixture(self):
        return {'candidate':'Fixture Candidate','focused_endorsement_observations':[
            {'endorser':'Samir Laymoun','relation':'supported'}]}

    def test_only_evidence_and_kamal_exceptions(self):
        state = self.fixture()
        self.assertTrue(policy_for_state(state)['samir_allowed'])
        state['spenders_supporting']=[{'amount_usd':500,'relevance':'unestablished'}]
        self.assertTrue(policy_for_state(state)['samir_allowed'])
        state['spenders_supporting'][0]['organization_context']='United Democracy Project'
        self.assertFalse(policy_for_state(state)['samir_allowed'])
        state['focused_endorsement_observations'].append({'endorser':'CAIR Action','relation':'preferred'})
        self.assertFalse(policy_for_state(state)['samir_allowed'])
        self.assertTrue(policy_for_state(state,'CA2026-174')['samir_allowed'])
        self.assertFalse(prose_errors('Samir Laymoun supports this candidate.',{'samir_allowed':True}))
        self.assertTrue(prose_errors('Samir Laymoun supports this candidate.',{'samir_allowed':False}))
        self.assertTrue(prose_errors('Samir Laymoun is an individual opinion source rather than an organizational endorsement.',{'samir_allowed':True}))

    def test_current_actions_community_and_neutral_observations(self):
        state = self.fixture();state['gaza_evidence']=['The candidate called for a Gaza ceasefire.']
        self.assertFalse(policy_for_state(state)['samir_allowed'])
        state = self.fixture();state['part_of_muslim_community']=True
        self.assertFalse(policy_for_state(state)['samir_allowed'])
        state['part_of_muslim_community']=False
        state['campaign_platform_points']=['Improve local school facilities.']
        state['gaza_evidence']=['No tracked pro-Israel PAC contributions.']
        state['congressional_gaza_actions']=[{'response':'Not elected'}]
        state['focused_endorsement_observations'].append({'endorser':'Vote for Peace','relation':'supported','rating':'Neutral'})
        self.assertTrue(policy_for_state(state)['samir_allowed'])

    def test_prompt_is_versioned_and_new_research_reaches_the_writer(self):
        policy=json.loads((ROOT/'research/gaza-grading/summary-policy-v4.json').read_text())
        self.assertEqual(hashlib.sha256(generator.PROMPT_PATH.read_bytes()).hexdigest(),policy['prompt_sha256'])
        state=self.fixture();row={'id':'fixture','position_id':'fixture','candidate':'Fixture Candidate',
            'request_sha256':'0'*64,'request':{'state':state,'questions':{}},'response':{}}
        current=deepcopy(state);current['gaza_evidence']=['The candidate opposed a ceasefire.']
        text=generator.build_input(row,'E',generator.PROMPT_PATH.read_text(),current)
        payload=json.loads(text.split('\n\nSUPPLIED RECORD\n',1)[1])
        self.assertFalse(payload['summary_source_policy']['samir_allowed'])
        self.assertEqual(payload['supplemental_reference']['current_research_additions']['gaza_evidence'],current['gaza_evidence'])
        self.assertIn('supplemental_reference.current_research_additions.gaza_evidence',payload['evidence_inventory'])
        self.assertEqual(payload['candidate_record'],state) # Archived scoring input remains exact.
        result={'candidate_id':'fixture','request_sha256':'0'*64,
            'summary':'The candidate opposed a Gaza ceasefire.',
            'evidence_audit':[{'id':key} for key in payload['evidence_inventory']]}
        self.assertIsNone(generator.validate(result,row,'E',payload['summary_source_policy'],payload['evidence_inventory']))
        result['evidence_audit'].pop()
        self.assertIn('complete archived and supplemental inventory',generator.validate(result,row,'E',payload['summary_source_policy'],payload['evidence_inventory']))

    def test_published_prose_has_only_the_requested_remaining_reference(self):
        data=json.loads((ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())
        remaining=[]
        for p in data['positions']:
            for roster in ('candidates','filed_candidates_not_confirmed_on_ballot','qualified_write_in_candidates'):
                for c in p.get(roster) or []:
                    text=c.get('pro_palestine_explanation',{}).get('summary','')
                    if SAMIR.search(text):remaining.append((p['id'],c['name']))
                    self.assertEqual(prose_errors(text,policy_for_candidate(p,c)),[],c['name'])
        self.assertEqual(remaining,[('CA2026-174','Kamal Yassin')])
        review=json.loads((ROOT/'research/gaza-grading/summary-editorial-review-2026-10-29-samir.json').read_text())
        self.assertEqual(len(review['entries']),19)
        self.assertTrue(all(e['previous_grade']==e['grade'] for e in review['entries']))

    def test_race_prompt_and_validator_share_the_same_policy(self):
        data=json.loads((ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())
        positions={p['id']:p for p in data['positions']}
        plan=json.loads(recommendations.PLAN.read_text())
        for race in plan['races']:
            text=(race.get('summary') or {}).get('text','')
            if text:self.assertEqual(prose_errors(text,{'samir_allowed':race['position_id']=='CA2026-174'}),[])
        race=next(r for r in plan['races'] if r['position_id']=='CA2026-004')
        self.assertIn('Samir Laymoun source policy:',recommendations.reason_prompt(race,positions))
        self.assertTrue(recommendations.out_of_policy_endorsers(race,positions,'Samir Laymoun opposes Tandon.'))
        position=positions['CA2026-174'];candidate=next(c for c in position['candidates'] if c['name']=='Kamal Yassin')
        self.assertIn(('Samir Laymoun','supported'),recommendations.relevant_endorsements(candidate,position)[0])


if __name__=='__main__':
    unittest.main()
