"""Offline publication and cache regressions for current race recommendations."""
from copy import deepcopy
import hashlib
import json
import re
import unittest
from unittest.mock import patch

import build_recommendations as rec
import build_site
from recommendation_evidence import evidence_from_state


class DirectionChecks(unittest.TestCase):
    def state(self, relation='opposed', endorser='BAMC Action'):
        return {'focused_endorsement_observations': [
            {'endorser': endorser, 'relation': relation, 'phase': 'general'}]}

    def test_opposition_is_not_support_and_neutral_is_not_directional(self):
        state = self.state()
        state['campaign_platform_points'] = ['Repair school facilities.']
        state['spenders_supporting'] = [{'amount_usd': 0, 'organization_context': 'Known source'},
                                      {'amount_usd': 1000}]
        state['congressional_gaza_actions'] = [{'response': 'Not voting'}]
        state['official_uscpr_scorecard'] = ['2026: Not graded']
        state['focused_endorsement_observations'].append(
            {'endorser': 'Vote for Peace', 'relation': 'neutral', 'rating': 'Neutral'})
        original = deepcopy(state)
        self.assertTrue(evidence_from_state(state)['opposition_only'])
        self.assertEqual(state, original)
        state['focused_endorsement_observations'][0]['relation'] = 'supported'
        self.assertFalse(evidence_from_state(state)['opposition_only'])
        self.assertFalse(evidence_from_state(self.state(endorser='Unreviewed organization'))['opposition_only'])
        historical = self.state(); historical['focused_endorsement_observations'][0]['historical'] = True
        self.assertFalse(evidence_from_state(historical)['opposition_only'])

    def test_other_relevant_material_is_preserved_without_assigning_direction(self):
        for field, value in (
            ('gaza_evidence', ['Candidate supported a ceasefire.']),
            ('antisemitism_education_policy_evidence', [{'summary': 'A recorded bill position.'}]),
            ('reviewed_gaza_platform_statement', 'The candidate has a recorded position.'),
            ('campaign_platform_points', ['Palestine: a documented candidate statement.']),
            ('congressional_gaza_actions', [{'response': 'Nay', 'alignment': 'unknown'}]),
            ('official_uscpr_scorecard', ['2026: B']),
            ('spenders_opposing', [{'amount_usd': 100, 'organization_context': 'Known source'}]),
        ):
            with self.subTest(field=field):
                state = self.state(); state[field] = value
                self.assertFalse(evidence_from_state(state)['opposition_only'])

    def fixture(self):
        return {'position_id': 'fixture', 'office': 'Board', 'roster': [
            {'name': 'Unassessed', 'grade': 'N/A'}, {'name': 'Graded', 'grade': 'D'}],
            'selection_evidence': {
                'Unassessed': evidence_from_state(self.state('supported')),
                'Graded': evidence_from_state(self.state()),
            }}

    def test_request_keeps_na_support_and_opposition_without_promoting_either(self):
        race = self.fixture(); request = rec.jev_request(race)
        people = {c['name']: c for c in request['state']['candidates']}
        self.assertEqual(set(people), {'Unassessed', 'Graded'})
        self.assertEqual(people['Unassessed']['observations'][0]['relation'], 'supported')
        self.assertEqual(people['Graded']['observations'][0]['relation'], 'opposed')
        self.assertEqual(people['Unassessed']['grade'], 'N/A')
        self.assertEqual(request['questions']['best_candidate']['criteria'], {})
        cached = {'choice': 'Graded', 'request': request, 'request_sha256': rec.request_hash(request)}
        self.assertFalse(rec.cached_pick_matches(cached, request))

    def test_supported_relationship_is_retained_in_rationale_input(self):
        community, contrast = rec.relevant_endorsements({'name': 'Fixture', 'endorsements': [
            {'endorser': 'CAIR Action', 'relation': 'supported'}]})
        self.assertEqual(community, [('CAIR Action', 'supported')])
        self.assertEqual(contrast, [])

    def test_documented_jstreetpac_alias_is_allowed_without_weakening_word_boundaries(self):
        position = {'id':'fixture','candidates':[{'name':'Fixture','endorsements':[
            {'endorser':'JStreetPAC','relation':'endorsed'},
            {'endorser':'American Library Association','relation':'endorsed'}]}]}
        race = {'position_id':'fixture'}
        self.assertEqual(rec.out_of_policy_endorsers(race,{'fixture':position},
            'JStreetPAC endorsed Fixture.'), [])
        self.assertTrue(rec.out_of_policy_endorsers(race,{'fixture':position},
            'American Library Association endorsed Fixture.'))
        self.assertFalse(rec._policy_match('american library association', {'ican'}))

    def test_summary_grouping_does_not_match_ican_inside_american_names(self):
        candidate = {'name':'Fixture','endorsements':[
            {'endorser':'Asian American Action Fund','relation':'endorsed'},
            {'endorser':'American Federation of Musicians Local 47','relation':'endorsed'},
            {'endorser':'The Israeli-American Civic Action Network','relation':'endorsed'},
            {'endorser':'Americans4Hindus','relation':'endorsed'},
            {'endorser':'TrackAIPAC','relation':'endorsed'},
            {'endorser':'JStreetPAC','relation':'endorsed'}]}
        community, contrast = rec.relevant_endorsements(candidate)
        self.assertEqual(community, [('TrackAIPAC','endorsed')])
        self.assertEqual(contrast,[('The Israeli-American Civic Action Network','endorsed'),
                                  ('Americans4Hindus','endorsed'),('JStreetPAC','endorsed')])

    def test_oc_action_does_not_match_inside_aroc_action(self):
        position = {'id':'fixture','candidates':[{'name':'Fixture','endorsements':[
            {'endorser':'AROC Action','relation':'endorsed'},
            {'endorser':'OC Action','relation':'endorsed'}]}]}
        self.assertEqual(rec.out_of_policy_endorsers({'position_id':'fixture'}, {'fixture':position},
                                                   'AROC Action endorsed Fixture.'), [])
        self.assertEqual(rec.out_of_policy_endorsers({'position_id':'fixture'}, {'fixture':position},
                                                   'OC Action endorsed Fixture.'), ['OC Action'])

    def test_hindu_identity_name_does_not_imply_hindutva_alignment(self):
        c={'name':'Fixture','endorsements':[
            {'endorser':"Hindu's for Human Rights Action PAC",'relation':'endorsed'},
            {'endorser':'Hindu American PAC','relation':'endorsed'}]}
        _, contrast=rec.relevant_endorsements(c)
        self.assertEqual(contrast,[('Hindu American PAC','endorsed')])

    def test_direction_change_invalidates_request_even_when_grades_stay_identical(self):
        race = self.fixture()
        race['selection_evidence']['Graded'] = evidence_from_state(self.state('supported'))
        request = rec.jev_request(race)
        cached = {'choice': 'Graded', 'request': request, 'request_sha256': rec.request_hash(request)}
        self.assertTrue(rec.cached_pick_matches(cached, request))
        changed = self.fixture()
        self.assertFalse(rec.cached_pick_matches(cached, rec.jev_request(changed)))
        changed['jev'] = {'choice': 'Graded', 'request': rec.legacy_jev_request(changed),
                          'request_sha256': rec.request_hash(rec.legacy_jev_request(changed))}
        changed['recommended'] = 'Graded'
        self.assertIsNone(rec.legacy_revalidation(changed))

    def test_one_graded_candidate_cannot_override_its_only_opposition_record(self):
        data = {'positions': [{'id': 'fixture', 'office': 'Board', 'candidates': [
            {'name': 'Unassessed', 'pro_palestine_score_grade': 'N/A'},
            {'name': 'Graded', 'pro_palestine_score_grade': 'D'}]}]}
        evidence = self.fixture()['selection_evidence']
        with patch.object(rec, 'candidate_evidence', side_effect=lambda p, c, d: evidence[c['name']]):
            race = rec.classify(data, {'observations': []})[0]
        self.assertEqual(race['category'], rec.CAT_NO_INFO)
        self.assertIsNone(race['recommended'])
        self.assertFalse(race['needs_summary'])

    def test_duplicate_projection_receipt_preserves_exact_answer_and_rejects_new_facts(self):
        race = self.fixture()
        state = self.state('supported')
        state['focused_endorsement_observations'][0]['phase'] = 'general'
        race['selection_evidence']['Graded'] = evidence_from_state(state)
        current = rec.jev_request(race)
        archived = deepcopy(current)
        person = next(c for c in archived['state']['candidates'] if c['name'] == 'Graded')
        person['observations'].append({**person['observations'][0], 'phase': 'unspecified'})
        race.update(recommended='Graded', jev={'choice':'Graded', 'request':archived,
                    'request_sha256':rec.request_hash(archived)})
        original = deepcopy(race)
        self.assertFalse(rec.cached_pick_matches(race['jev'], current))
        receipt = rec.legacy_revalidation(race)
        self.assertEqual(receipt['current_request_sha256'], rec.request_hash(current))
        self.assertEqual(race, original)
        race['selection_evidence']['Graded']['observations'][0]['relation'] = 'opposed'
        self.assertIsNone(rec.legacy_revalidation(race))

    def test_legacy_response_retention_is_explicit_and_not_a_current_cache_hit(self):
        race = self.fixture()
        race['selection_evidence']['Graded'] = evidence_from_state(self.state('supported'))
        old_request = rec.legacy_jev_request(race)
        race.update(recommended='Graded', jev={
            'choice': 'Graded', 'request': old_request, 'request_sha256': rec.request_hash(old_request)})
        original = deepcopy(race['jev'])
        receipt = rec.legacy_revalidation(race)
        self.assertEqual(receipt['archived_request_sha256'], original['request_sha256'])
        self.assertFalse(rec.cached_pick_matches(race['jev'], rec.jev_request(race)))
        self.assertEqual(race['jev'], original)

    def test_offline_revalidation_withdraws_without_choosing_or_rescoring(self):
        data = {'positions': [{'id': 'fixture', 'office': 'Board', 'candidates': [
            {'name': 'Unassessed', 'pro_palestine_score_grade': 'N/A'},
            {'name': 'Graded', 'pro_palestine_score_grade': 'D'}]}]}
        evidence = self.fixture()['selection_evidence']
        before = deepcopy(data)
        initially_supported = {**evidence, 'Graded': evidence_from_state(self.state('supported'))}
        with patch.object(rec, 'candidate_evidence', side_effect=lambda p, c, d: initially_supported[c['name']]):
            old = rec.classify(data, {'observations': []})[0]
        request = rec.legacy_jev_request(old)
        old.update(recommended='Graded', jev={'choice': 'Graded', 'request': request,
                   'request_sha256': rec.request_hash(request)},
                   summary={'text': 'An old recommendation.'}, recommend_reason_text={'text': 'An old reason.'})
        plan = {'races': [old]}; original = deepcopy(plan)
        with patch.object(rec, 'candidate_evidence', side_effect=lambda p, c, d: evidence[c['name']]):
            result, audit = rec.revalidate_plan(plan, data)
        self.assertIsNone(result['races'][0]['recommended'])
        for key in ('summary', 'recommend_reason_text', 'jev'):
            self.assertNotIn(key, result['races'][0])
        self.assertEqual(audit['model_calls'], 0)
        self.assertEqual(audit['changed_choices'][0]['previous'], original['races'][0])
        self.assertEqual(plan, original)
        self.assertEqual(data, before)


class RecommendationChecks(unittest.TestCase):
    def test_race_writer_receives_vote_response_with_alignment_and_full_source_evidence(self):
        data = json.loads(rec.DATA.read_text())
        position = next(p for p in data['positions'] if p['id'] == 'CA2026-003')
        candidate = deepcopy(next(c for c in position['candidates'] if c['name'] == 'Aisha Wahab'))
        candidate['pro_palestine_explanation'] = {'summary': 'An earlier misleading paraphrase.'}
        lines = rec.reason_evidence(candidate, position, data)
        projected = json.loads(lines[0].split(': ', 1)[1])
        row = next(r for r in projected['congressional_gaza_actions']
                   if r['title'] == 'Defund universities that boycott Israel')
        self.assertEqual((row['response'], row['alignment']), ('No', 'aligned'))
        self.assertNotIn('earlier misleading paraphrase', '\n'.join(lines))
        self.assertEqual(len(projected.get('gaza_evidence', [])),
                         len(__import__('grade_gaza').build_state(position, candidate, data).get('gaza_evidence', [])))
        race = next(r for r in json.loads(rec.PLAN.read_text())['races'] if r['position_id'] == position['id'])
        prompt = rec.reason_prompt(race, {position['id']: position})
        self.assertIn('LEGISLATIVE CONSISTENCY', prompt)
        self.assertIn('"response":"No","alignment":"aligned"', prompt)

    def test_race_context_keeps_relevant_na_observations_without_absence_inference(self):
        data = json.loads(rec.DATA.read_text())
        position = next(p for p in data['positions'] if p['id'] == 'CA2026-047')
        race = next(r for r in rec.classify(data, {'observations':[]}) if r['position_id'] == position['id'])
        race['recommended'] = 'Tracy Jensen'
        prompt = rec.reason_prompt(race, {position['id']:position})
        self.assertIn('Malia Vella', prompt)
        self.assertIn('N/A means unassessed', prompt)
        self.assertIn('An absent entry does not establish', prompt)
        self.assertNotIn('effectively supports the status quo', prompt)
        self.assertNotIn('has not called it a genocide; has not backed', prompt)

    def test_owner_hold_withholds_humbert_even_when_grade_is_eligible(self):
        data = json.loads(rec.DATA.read_text())
        position = deepcopy(next(p for p in data['positions'] if p['id']=='CA2026-053'))
        person = next(c for c in position['candidates'] if c['name']=='Mark Humbert')
        original = deepcopy(person)
        for grade in ('D','A'):
            person['pro_palestine_score_grade'] = grade
            race = rec.classify({**data,'positions':[position]}, {'observations':[]})[0]
            self.assertIsNone(race['recommended'])
            self.assertFalse(race['needs_summary'])
            self.assertEqual(race['owner_review_hold']['candidate'],'Mark Humbert')
        self.assertEqual({k:v for k,v in person.items() if k!='pro_palestine_score_grade'},
                         {k:v for k,v in original.items() if k!='pro_palestine_score_grade'})

    def test_harris_context_is_source_bound_and_never_selects_a_candidate(self):
        from publisher_review_context import context_digest, current_context
        data = json.loads(rec.DATA.read_text())
        original = deepcopy(data)
        position = next(p for p in data['positions'] if p['id'] == 'CA2026-120')
        hold = next(h for h in json.loads((rec.ROOT / 'research/candidate-recommendations/owner-review-holds.json').read_text())['holds']
                    if h['position_id'] == position['id'])
        context = current_context(hold['narrative_context_path'], position, data, hold)
        self.assertIsNotNone(context)
        race = next(r for r in rec.classify(data, {'observations': []}) if r['position_id'] == position['id'])
        self.assertIsNone(race['recommended'])
        self.assertFalse(race['needs_summary'])
        self.assertEqual(race['recommend_reason'], context['text'])
        self.assertEqual(data, original)
        modified_hold = {**hold, 'reviewed_on': '2099-01-01'}
        self.assertIsNone(current_context(hold['narrative_context_path'], position, data, modified_hold))
        position['candidates'][0]['name'] += ' changed'
        self.assertNotEqual(context_digest(position, data, hold), context['source_context_sha256'])
        race = next(r for r in rec.classify(data, {'observations': []}) if r['position_id'] == position['id'])
        self.assertIsNone(race['recommended'])
        self.assertEqual(race['recommend_reason'], hold['public_reason'])

    def test_readers_embed_the_current_recommendation_plan(self):
        plan = json.loads(rec.PLAN.read_text())
        data = json.loads(rec.DATA.read_text())
        dataset_hash = hashlib.sha256(rec.DATA.read_bytes()).hexdigest()
        self.assertEqual(plan['source_dataset_sha256'], dataset_hash)
        self.assertEqual(plan['source_score_publication_id'], data['pro_palestine_grading']['publication_id'])
        rec.validate_plan(plan['races'], data)
        expected = {}
        for race in plan['races']:
            entry = {'category': race['category'], 'recommended': race.get('recommended'),
                     'recommend_reason': race.get('recommend_reason')}
            expected[race['position_id']] = entry
        self.assertEqual(len(expected), 539)
        for page in ('index', 'ballot'):
            html = (rec.ROOT / f'{page}.html').read_text(encoding='utf-8')
            match = re.search(r'<script id="recommendations-data" type="application/json">(.*?)</script>', html, re.S)
            self.assertIsNotNone(match, f'{page}.html embeds the recommendation map')
            embedded = json.loads(match.group(1))
            self.assertEqual(embedded['plan_sha256'], hashlib.sha256(rec.PLAN.read_bytes()).hexdigest(),
                             f'{page}.html binds the current plan')
            self.assertEqual(embedded['byPosition'].keys(), expected.keys())
            for pid, entry in expected.items():
                got = embedded['byPosition'][pid]
                for key, value in entry.items():
                    self.assertEqual(got[key], value, f'{page}:{pid}:{key}')
                if entry['recommended']:
                    self.assertIn('why', got, f'{page}:{pid} recommended pick carries a reason')

    def test_changed_grade_or_roster_cannot_reuse_a_cached_pick(self):
        race = {'position_id': 'fixture', 'office': 'Council', 'roster': [
            {'name': 'One', 'grade': 'B'}, {'name': 'Two', 'grade': 'C'}]}
        request = rec.jev_request(race)
        cached = {'request': request, 'request_sha256': rec.request_hash(request), 'choice': 'One'}
        self.assertTrue(rec.cached_pick_matches(cached, request))
        self.assertFalse(rec.cached_pick_matches({'choice': 'One'}, request))
        changed = deepcopy(race); changed['roster'][1]['grade'] = 'A'
        self.assertFalse(rec.cached_pick_matches(cached, rec.jev_request(changed)))
        changed = deepcopy(race); changed['roster'].pop()
        self.assertFalse(rec.cached_pick_matches(cached, rec.jev_request(changed)))
        cached['choice'] = 'Two'
        self.assertFalse(rec.cached_pick_matches(cached, request))

    def test_old_plan_is_rejected_after_score_updates(self):
        data = json.loads(rec.DATA.read_text())
        old = json.loads((rec.OUTDIR / 'recommendations-2026-10-28.json').read_text())
        with self.assertRaisesRegex(ValueError, 'Stale|differs'):
            rec.validate_plan(old['races'], data)

    def test_standalone_reader_is_retired(self):
        self.assertFalse((rec.ROOT / 'recommendations.html').exists())
        self.assertNotIn('recommendations.html', (rec.ROOT / 'index.html').read_text())
        self.assertNotIn('recommendations.html', (rec.ROOT / 'ballot.html').read_text())


if __name__ == '__main__':
    unittest.main()
