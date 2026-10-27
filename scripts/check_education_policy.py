"""Regression checks for source-bound education-policy refreshes and Jev inputs."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from grade_gaza import build_state
from research_education_policy import plan, legislative_capture, shared_vote_leads, publication_metadata, coauthor_leads
from research_gaza_gaps import search_queries, relevant_lead

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())


class EducationPolicyChecks(unittest.TestCase):
    def test_refresh_covers_every_active_candidacy_even_with_existing_evidence(self):
        rows = plan(DATA)['items']
        self.assertEqual(len(rows), 1296)
        self.assertTrue(any(r['candidate'] == 'Scott Wiener' for r in rows))
        self.assertTrue(any(r['candidate'] == 'Kevin Park' for r in rows))
        self.assertTrue(all('IHRA' in r['query'] and 'AB 715' in r['query'] for r in rows))

    def test_generic_discovery_does_not_require_gaza_keywords(self):
        row = {'candidate': 'Test Candidate', 'identity': {'jurisdiction': 'School District'}}
        self.assertTrue(any('IHRA' in q for q in search_queries(row)))
        self.assertTrue(relevant_lead({'link': 'https://example.org', 'title': 'IHRA adoption vote'}))
        self.assertTrue(relevant_lead({'link': 'https://example.org', 'title': 'AB715 curriculum debate'}))

    def test_policy_channel_retains_evidence_beyond_generic_budget(self):
        p = next(p for p in DATA['positions'] if any(c['name'] == 'Scott Wiener' for c in p.get('candidates') or []))
        c = deepcopy(next(c for c in p['candidates'] if c['name'] == 'Scott Wiener'))
        generic = {'date': '2025-01-01', 'summary': 'Generic evidence', 'dimension': 'other'}
        special = {'date': '2025-09-12', 'summary': 'Named AB 715 action', 'dimension': 'antisemitism_education',
                   'url': 'https://example.org/bill', 'date_note': 'Historical final vote', 'quote': 'Aye'}
        c['gaza_evidence'] = [dict(generic) for _ in range(20)] + [dict(special) for _ in range(15)]
        state = build_state(p, c, DATA)
        self.assertEqual(len(state['gaza_evidence']), 12)
        self.assertEqual(len(state['antisemitism_education_policy_evidence']), 15)
        self.assertEqual(state['antisemitism_education_policy_evidence'][0],{'date':special['date'],'summary':special['summary'],'context':special['date_note']})
        self.assertNotIn('pro_palestine_score', state)

    def test_compact_policy_context_keeps_date_uncertainty_without_capture_mechanics(self):
        from grade_gaza import compact_policy_evidence
        base={'date':'2025-06-01','summary':'Source reports a policy action.','url':'https://example.org',
              'quote':'Repeated quote','source_kind':'news_report','date_method':'page_metadata'}
        original={**base,'date_note':'Article publication metadata date, not necessarily the date of the action described; events may precede this report.'}
        self.assertEqual(compact_policy_evidence(original),{'date':base['date'],'summary':base['summary'],'context':'Report date; action may be earlier.'})
        original['date_note']='June statement about an earlier bill version, before September amendments.'
        self.assertEqual(compact_policy_evidence(original)['context'],original['date_note'])
        original['date_note']='CalMatters structured VoteAction date/labels, not an independently verified official roll call; quote is field transcription.'
        self.assertEqual(compact_policy_evidence(original)['context'],'Tracker date, not an independently verified official roll call.')

    def test_roll_call_capture_preserves_nay_and_nonvotes_without_inventing_support(self):
        raw = b'''<rollcall-vote><vote-metadata><congress>118</congress><legis-num>H R 6090</legis-num>
          <vote-question>On Passage</vote-question><vote-desc>Antisemitism Awareness Act</vote-desc>
          <action-date>1-May-2024</action-date><vote-result>Passed</vote-result></vote-metadata>
          <vote-data><recorded-vote><legislator name-id="T000001" unaccented-name="Test" state="CA">Test</legislator>
          <vote>Not Voting</vote></recorded-vote></vote-data></rollcall-vote>'''
        obj = legislative_capture(raw, 'https://clerk.house.gov/evs/2024/roll172.xml', 'house-rollcall-xml')
        self.assertEqual(obj['votes'][0]['vote'], 'Not Voting')
        self.assertEqual(obj['vote_metadata']['vote-question'], 'On Passage')
        with self.assertRaises(ValueError):
            legislative_capture(raw, 'https://other.example/roll172.xml', 'house-rollcall-xml')
        with self.assertRaises(ValueError):
            legislative_capture(raw.replace(b'<action-date>1-May-2024</action-date>', b''),
                                'https://clerk.house.gov/evs/2024/roll172.xml', 'house-rollcall-xml')

    def test_california_source_uses_latest_floor_vote_and_keeps_abstain_label(self):
        person = {'name': 'Scott Wiener'}
        def action(date, chamber, option):
            return {'@type': 'VoteAction', 'startTime': date, 'location': {'name': chamber},
                    'description': 'AB 715', 'actionOption': option, 'agent': [person]}
        packet = {'kind': 'california-legislation-jsonld', 'votes': [
            action('2025-06-01', 'Senate Floor', 'Aye'),
            action('2025-09-12', 'Senate Floor', 'Abstain'),
            action('2025-09-13', 'Senate Standing Committee on Education', 'Aye')]}
        rows = [r for r in shared_vote_leads(DATA, packet) if r['candidate'] == 'Scott Wiener']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source_vote']['vote'], 'Abstain')
        self.assertEqual(rows[0]['source_vote']['date'], '2025-09-12')
        self.assertEqual(rows[0]['status'], 'identity_and_meaning_review_required')

    def test_california_capture_binds_bill_url_and_transcribes_named_action(self):
        url = 'https://calmatters.digitaldemocracy.org/bills/ca_fixture'
        entity = {'@type': 'Legislation', 'name': 'AB 715', 'url': url, 'text': 'Bill text', 'subjectOf': [{'@type': 'Event'}]}
        doc = {'mainEntity': entity, 'potentialAction': [{'@type': 'VoteAction', 'startTime': '2025-09-12',
               'location': {'name': 'Senate Floor'}, 'description': 'AB 715', 'actionOption': 'Aye',
               'agent': [{'name': 'Scott Wiener'}]}]}
        raw = ('<script type="application/ld+json">' + json.dumps(doc) + '</script>').encode()
        result = legislative_capture(raw, url, 'california-legislation-jsonld')
        self.assertIn('Scott Wiener | Aye', result['text'])
        with self.assertRaises(ValueError):
            legislative_capture(raw, url + '_other', 'california-legislation-jsonld')

    def test_publication_metadata_does_not_use_current_navigation_date(self):
        raw = b'<p>October 26, 2026</p><meta property="article:published_time" content="2021-02-25T12:00:00Z">'
        self.assertEqual(publication_metadata(raw), {'published_date': '2021-02-25'})
        self.assertEqual(publication_metadata(b'<p>October 26, 2026</p>'), {})
        self.assertEqual(publication_metadata(raw + b'<meta property="article:published_time" content="2022-01-01">'), {})

    def test_coauthor_names_are_candidate_leads_not_published_judgments(self):
        packet = {'text': 'Introduced by Assembly Members Zbur and Addis\n(Principal coauthors: Senators Becker and Wiener)\n(Coauthors: Assembly Members Stefani and Wicks)\nFebruary 21, 2025\nAn act to add a section.'}
        leads = coauthor_leads(DATA, packet)
        self.assertTrue(any(r['candidate'] == 'Scott Wiener' for r in leads))
        self.assertTrue(any(r['candidate'] == 'Catherine Stefani' for r in leads))
        self.assertTrue(all(r['status'] == 'identity_and_meaning_review_required' for r in leads))
        self.assertTrue(all('record' not in r and 'grade' not in r for r in leads))

    def test_published_scott_evidence_and_future_state_include_both_roles_and_objections(self):
        p = next(p for p in DATA['positions'] if any(c['name'] == 'Scott Wiener' for c in p.get('candidates') or []))
        c = next(c for c in p['candidates'] if c['name'] == 'Scott Wiener')
        state = build_state(p, c, DATA)
        policies = state['antisemitism_education_policy_evidence']
        self.assertGreaterEqual(len(policies), 4)
        self.assertTrue(any('principal coauthor' in e['summary'] for e in policies))
        self.assertTrue(any('CAIR' in e['summary'] and 'June' in e['summary'] for e in policies))
        self.assertTrue(any('AB 1468' in e['summary'] and 'failed' in e['summary'] for e in policies))
        self.assertTrue(all(set(e)<= {'date','summary','context'} for e in policies))
        self.assertTrue(all(e.get('date') and e.get('summary') for e in policies))

    def test_existing_scores_and_preferred_prompt_keep_the_original_evaluation_binding(self):
        cfg=DATA['pro_palestine_grading']
        archive = json.loads((ROOT / cfg['archive_path']).read_text())
        preferred = json.loads((ROOT / cfg['preferred_criteria_path']).read_text())
        self.assertEqual(preferred, archive['preferred_criteria'])
        rows = {r['id']: r for r in archive['rows']}
        for p in DATA['positions']:
            for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates'):
                for c in p.get(roster) or []:
                    evaluation = c.get('pro_palestine_evaluation')
                    if evaluation:
                        old = rows[evaluation['candidate_id']]
                        self.assertEqual(c['pro_palestine_score'], old['response']['answers']['pro_palestine_score']['score'])
                        self.assertEqual(evaluation['request_sha256'], old['request_sha256'])

    def test_sweep_accounts_for_all_candidates_and_actual_source_decisions(self):
        from ballotpedia_endorsements import digest, dump
        from grade_gaza import candidates
        sweep = json.loads((ROOT / 'research/education-policy/sweep-2026-10-26.json').read_text())
        wanted = {(p['id'], c['name'], roster) for p, c, roster in candidates(DATA, 'all')}
        actual = {(r['position_id'], r['candidate'], r['roster']) for r in sweep['candidates']}
        self.assertEqual(actual, wanted)
        self.assertEqual(sweep['counts']['new_evidence_records'], 129)
        lookup = {(p['id'], c['name']): c for p, c, _ in candidates(DATA, 'all')}
        for row in sweep['added_records']:
            self.assertTrue(any(e['id'] == row['evidence_id'] and e['dimension'] == 'antisemitism_education'
                                for e in lookup[row['position_id'], row['candidate']]['gaza_evidence']))
        decisions = json.loads((ROOT / 'research/education-policy/source-decisions-2026-10-26.json').read_text())['decisions']
        for row in sweep['source_outcomes']:
            if row.get('jev_ref'):
                decision = decisions[row['jev_ref']]
                self.assertEqual(row['jev_ref'], digest(dump(decision['request']).encode()))
                self.assertEqual(decision['response']['model'], 'jev-1.14.0')
                self.assertEqual(decision['response']['answers']['coverage'], row['answer'])
                self.assertTrue(all(q['type'] == 'choice' for q in decision['request']['questions'].values()))


if __name__ == '__main__':
    unittest.main()
