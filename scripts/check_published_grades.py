"""Verify public grades against immutable Jev inputs, outputs and exact candidacies."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from ballotpedia_endorsements import digest
from publish_jev_grades import ROOT, DATASET, FIELDS, ROSTERS, attach, projection


def check(data):
    cfg=data['pro_palestine_grading'];path=(ROOT/cfg['archive_path']).resolve()
    if not path.is_relative_to(ROOT/'research/gaza-grading'):
        raise ValueError('Archive path outside the grading registry')
    if digest(path.read_bytes()) != cfg['archive_sha256']:
        raise ValueError('Changed published archive')
    archive=json.loads(path.read_text())
    expected=attach(data,archive,cfg['archive_path'],cfg['archive_sha256'])
    if data != expected:
        raise ValueError('Published projection differs from exact saved evaluation')
    preferred=json.loads((ROOT/cfg['preferred_criteria_path']).read_text())
    if preferred != archive['preferred_criteria']:
        raise ValueError('Preferred rubric differs from publication snapshot')
    return archive


class PublicationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATASET.read_text());cls.archive=check(cls.data)

    def test_exact_projection_and_idempotence(self):
        cfg=self.data['pro_palestine_grading']
        self.assertEqual(attach(self.data,self.archive,cfg['archive_path'],cfg['archive_sha256']),self.data)
        self.assertEqual(len(self.archive['rows']),1296)

    def test_identity_only_candidates_never_receive_a_political_grade(self):
        identity={'candidate','office','state','party','election_date','jurisdiction',
                  'candidate_roster','incumbent','part_of_muslim_community','election_type',
                  'office_category','government_level','district_or_seat','counties','partisan'}
        rows=[r for r in self.archive['rows'] if set(r['request']['state'])<=identity
              and r['request']['state'].get('part_of_muslim_community') is not True]
        self.assertTrue(rows)
        self.assertTrue(any(r['candidate']=='Charles A. Smiley' for r in rows))
        for row in rows:
            with self.subTest(candidate=row['candidate']):
                self.assertEqual(projection(row,self.archive['score_grade_mapping'],self.archive['id'])['pro_palestine_score_grade'],'N/A')

    def test_unrelated_local_platform_is_not_issue_evidence(self):
        from score_grade import has_issue_observation, row_grade
        names = {'Shruti Kumar', 'Arielle Fleisher', 'Boris Lipkin', 'Rebecca Lewington'}
        for row in self.archive['rows']:
            if row['candidate'] in names:
                self.assertFalse(has_issue_observation(row['request']['state']))
                self.assertEqual(row_grade(row, self.archive['score_grade_mapping']), 'N/A')
        # The old, unguarded publication did display D for these four. Keep that
        # historical regression independent of later owner reruns/raw answers.
        historical_archive = json.loads((ROOT/'research/gaza-grading/published-2026-10-27-evidence022.json').read_text())
        for row in historical_archive['rows']:
            if row['candidate'] in names:
                self.assertEqual(row_grade(row, historical_archive['score_grade_mapping']), 'D')
        for key, value in [('focused_endorsement_observations', [{'endorser':'CAIR Action','relation':'preferred'}]),
                           ('gaza_evidence', ['Supported a ceasefire.']),
                           ('campaign_platform_points', ['Oppose arms transfers to Israel.']),
                           ('part_of_muslim_community', True)]:
            self.assertTrue(has_issue_observation({'candidate':'Fixture', key:value}))
        self.assertFalse(has_issue_observation({'candidate':'Fixture','part_of_muslim_community':False,'campaign_platform_points':['Fund schools and parks.']}))

    def test_latest_fiona_and_smiley_scores_remain_exact(self):
        people={c['name']:c for p in self.data['positions'] for c in p.get('candidates') or []}
        for name in ['Fiona Ma','Charles A. Smiley']:
            row=next(r for r in self.archive['rows'] if r['candidate']==name)
            self.assertEqual(people[name]['pro_palestine_score'],row['response']['answers']['pro_palestine_score']['score'])
            self.assertEqual(people[name]['pro_palestine_score_grade'],projection(row,self.archive['score_grade_mapping'],self.archive['id'])['pro_palestine_score_grade'])

    def test_changed_grade_score_or_confidence_is_rejected(self):
        for field,value in [('pro_palestine_score',5.001),('pro_palestine_score_grade','invalid')]:
            d=deepcopy(self.data);c=next(c for p in d['positions'] for c in p.get('candidates') or [] if c['name']=='Fiona Ma');c[field]=value
            with self.assertRaises(ValueError):check(d)

    def test_wrong_person_roster_or_changed_request_never_attaches(self):
        cfg=self.data['pro_palestine_grading']
        for change in ('candidate','roster','request'):
            a=deepcopy(self.archive);r=a['rows'][0]
            if change=='candidate':r['candidate']='Someone else'
            elif change=='roster':r['roster']='qualified_write_in_candidates'
            else:r['request']['state']['candidate']='Someone else'
            with self.assertRaises(ValueError):attach(self.data,a,cfg['archive_path'],cfg['archive_sha256'])

    def test_one_exact_rubric_and_raw_provider_responses_are_not_edited(self):
        before=deepcopy(self.archive);mapping=self.archive['score_grade_mapping'];variants=set()
        for r in self.archive['rows']:
            p=projection(r,mapping,self.archive['id']);variants.add(p['pro_palestine_evaluation']['questions_sha256'])
            self.assertNotIn('pro_palestine_score_grade',r['response']['answers'])
        self.assertEqual(len(variants),1);self.assertEqual(before,self.archive)

    def test_mixed_prompt_is_rejected_before_publication(self):
        a=deepcopy(self.archive);a['rows'][0]['request']['questions']['evidence_score']['instructions']='Other rubric'
        cfg=self.data['pro_palestine_grading']
        with self.assertRaisesRegex(ValueError,'exact preferred'):
            attach(self.data,a,cfg['archive_path'],cfg['archive_sha256'])

    def test_publication_never_becomes_an_input_for_future_grading(self):
        from serve_jev_playground import playground_state
        p=next(p for p in self.data['positions'] if any(c['name']=='Fiona Ma' for c in p.get('candidates') or []))
        c=next(c for c in p['candidates'] if c['name']=='Fiona Ma');unpublished=deepcopy(c)
        for key in FIELDS:unpublished.pop(key)
        self.assertEqual(playground_state(p,c,self.data),playground_state(p,unpublished,self.data))

    def test_recommendations_cannot_be_omitted_or_discounted_to_na(self):
        from ballotpedia_endorsements import dump
        cfg=self.data['pro_palestine_grading']
        for mode in ('missing','insufficient'):
            a=deepcopy(self.archive);r=next(r for r in a['rows'] if r['candidate']=='Fiona Ma')
            if mode=='missing':
                r['request']['state']['focused_endorsement_observations']=[]
                r['request_sha256']=digest(dump(r['request']).encode())
            else:
                r['response']['answers']['evidence_score'].update(score=.05,probabilities={'0':.95,'1':.05})
            with self.assertRaisesRegex(ValueError,'recommendation'):
                attach(self.data,a,cfg['archive_path'],cfg['archive_sha256'])

    def test_recommendation_signals_include_opposition_without_conflating_neutral(self):
        from publish_jev_grades import recommendation_signal,validate_recommendation_evidence
        for name in ['CAIR Action','VoteForPeace','Vote for Peace']:
            for relation in ['endorsed','preferred','opposed','supported']:
                obs={'endorser':name,'relation':relation,'phase':'primary'}
                self.assertTrue(recommendation_signal(obs))
                row={'candidate':'Fixture','request':{'state':{'focused_endorsement_observations':[obs]}}}
                with self.assertRaisesRegex(ValueError,'N/A despite'):
                    validate_recommendation_evidence({'endorsements':[obs]},row,'N/A')
        self.assertFalse(recommendation_signal({'endorser':'Vote for Peace','relation':'supported','rating':'Neutral'}))
        self.assertFalse(recommendation_signal({'endorser':'CAIR Action','relation':'endorsed','historical':True}))

    def test_configurable_publication_evidence_threshold_is_exact(self):
        cfg=self.data['pro_palestine_grading'];archive=deepcopy(self.archive)
        archive['evidence_threshold']=.1 if archive['evidence_threshold']!=.1 else .2
        with self.assertRaisesRegex(ValueError,'threshold differs'):
            attach(self.data,archive,cfg['archive_path'],cfg['archive_sha256'])
        self.assertEqual(self.archive['evidence_threshold'],self.archive['score_grade_mapping'].get('minimum_evidence_score',.1))

    def test_duplicate_and_removed_scores_fail(self):
        cfg=self.data['pro_palestine_grading'];a=deepcopy(self.archive);a['rows'].append(a['rows'][0])
        with self.assertRaises(ValueError):attach(self.data,a,cfg['archive_path'],cfg['archive_sha256'])
        d=deepcopy(self.data);c=next(c for p in d['positions'] for c in p.get('candidates') or [] if 'pro_palestine_score' in c);c.pop('pro_palestine_score')
        with self.assertRaises(ValueError):check(d)

    def test_exact_replay_preserves_explanations_and_new_archive_clears_them(self):
        data=deepcopy(self.data);cfg=data['pro_palestine_grading']
        cfg['explanations']={'publication_id':self.archive['id'],'archive_path':'fixture.json'}
        candidate=next(c for p in data['positions'] for c in p.get('candidates') or [] if c.get('pro_palestine_evaluation'))
        candidate['pro_palestine_explanation']={'summary':'A narrative bound to the existing publication.'}
        replay=attach(data,self.archive,cfg['archive_path'],cfg['archive_sha256'])
        self.assertEqual(replay,data)
        newer=deepcopy(self.archive);newer['id']='jev-new-fixture'
        refreshed=attach(data,newer,'research/gaza-grading/new-fixture.json','f'*64)
        self.assertNotIn('explanations',refreshed['pro_palestine_grading'])
        self.assertFalse(any(c.get('pro_palestine_explanation') for p in refreshed['positions'] for roster in ROSTERS for c in p.get(roster) or []))


if __name__=='__main__':unittest.main()
