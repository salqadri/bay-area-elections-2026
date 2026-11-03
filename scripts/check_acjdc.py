"""Offline source/identity/phase guards for ACJDC research."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

import research_acjdc as acjdc
from grade_gaza import build_state, focused_endorsements

ROOT = Path(__file__).resolve().parent.parent


class ACJDCChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())
        cls.packet = json.loads((ROOT/'research/questionnaires/acjdc-2026-11-02/responses.json').read_text())

    def test_parser_preserves_phases_ranks_and_no_recommendation(self):
        html = ('<h2>November 2026 General Election Endorsements</h2>'
                '<p>Berkeley City Council District 1: Laura Babitt — #1; Ross Bernet — #2</p>'
                '<p>Oakland City Council District 6: No recommendation</p>'
                '<h3>Ballot measures</h3><p>Proposition 1: YES</p>'
                '<h2>June 2026 Primary Endorsements — Archive</h2><p>Governor: Xavier Becerra</p>')
        rows = acjdc.parse_endorsements(html)
        self.assertEqual([r['rank'] for r in rows[:2]], [1, 2])
        self.assertTrue(rows[2]['no_recommendation'])
        self.assertEqual(rows[-1]['phase'], 'primary')
        self.assertEqual(len(rows), 4)

    def test_name_alone_cannot_transfer_an_endorsement_between_offices(self):
        packet = {**self.packet, 'responses': []}
        html = '<h2>June 2026 Primary Endorsements — Archive</h2><p>State Senate District 10: Anne J. Kepner</p>'
        review, audit = acjdc.draft(self.data, html, packet)
        self.assertEqual(review['decisions'], [])
        self.assertTrue(audit['held'])

    def test_question_preamble_and_unanswered_ab715_do_not_become_positions(self):
        aisha = next(r for r in self.packet['responses'] if r['candidate'] == 'Aisha Wahab')
        self.assertEqual(aisha['ab715_status'], 'not_answered')
        self.assertIsNone(aisha['ab715_summary'])
        review, _ = acjdc.draft(self.data, '', {**self.packet, 'responses': [aisha]})
        self.assertFalse(any(d['after']['dimension'] == 'antisemitism_education' for d in review['decisions']))
        self.assertFalse(any('only place' in s for s in aisha['israel_summaries']))

    def test_active_respondents_are_bound_to_current_identity(self):
        self.assertEqual(len(self.packet['responses']), 33)
        positions = {p['id']: p for p in self.data['positions']}
        for row in self.packet['responses']:
            p = positions[row['position_id']]
            self.assertEqual(p['ballot_status'], 'confirmed')
            self.assertIn(row['candidate'], [c['name'] for c in p['candidates']])
        anne = next(r for r in self.packet['responses'] if r['candidate'] == 'Anne J. Kepner')
        self.assertEqual(anne['source_office'], 'State Senate, District 10')
        self.assertIn('SD-10', anne['ab715_summary'])

    def test_state_has_low_weight_organization_context_and_exact_tiers(self):
        p = next(p for p in self.data['positions'] if p['id'] == 'CA2026-016')
        candidate = next(c for c in p['candidates'] if c['name'] == 'Fiona Ma')
        before = deepcopy(candidate)
        state = build_state(p, candidate, self.data)
        context = state['organization_context'][acjdc.NAME]
        self.assertEqual(context['context_weight'], 'low')
        self.assertEqual(context['basis'], 'first_party_club_mission')
        self.assertIn('California Jewish Democrats', state['organization_context'])
        self.assertEqual(candidate, before)
        for e in focused_endorsements(p, candidate):
            if e['endorser'] == 'CAIR Action':
                self.assertEqual(e['relation'], 'preferred')

    def test_owner_scope_excludes_complete_aisha_primary_responses_without_deleting_sources(self):
        p = next(p for p in self.data['positions'] if p['id']=='CA2026-003')
        c = next(c for c in p['candidates'] if c['name']=='Aisha Wahab')
        before = deepcopy(c)
        state = build_state(p,c,self.data)
        text = json.dumps(state)
        self.assertNotIn('strong U.S.-Israel alliance',text)
        self.assertNotIn('Defends civil disobedience',text)
        self.assertEqual(c,before)
        self.assertTrue({'GE-1623','GE-1624'} <= {e['id'] for e in c['gaza_evidence']})
        self.assertIn('congressional_gaza_actions',state)
        other = next(c for c in p['candidates'] if c['name']=='Melissa Hernandez')
        self.assertIn('continued U.S. security assistance',json.dumps(build_state(p,other,self.data)))

    def test_ranked_source_is_not_invented_joint_support(self):
        p = next(p for p in self.data['positions'] if p['id'] == 'CA2026-050')
        for name, rank in [('Laura Babitt', 1), ('Ross Bernet', 2)]:
            c = next(c for c in p['candidates'] if c['name'] == name)
            e = next(e for e in c['endorsements'] if e['endorser'] == acjdc.NAME and e['phase'] == 'general')
            self.assertEqual(e['recommendation_rank'], rank)
            self.assertFalse(e.get('shared'))


if __name__ == '__main__':
    unittest.main()
