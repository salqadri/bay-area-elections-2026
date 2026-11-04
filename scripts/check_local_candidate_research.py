"""Offline source/scope regressions for local candidate enrichment."""
import json
from pathlib import Path
import unittest

from ballotpedia_endorsements import digest, dump
from local_candidate_research import accepted_link, ballotpedia_profile_shape, inventory, local_positions
from review_local_campaigns import literal_proposal
from serve_jev_playground import snapshot as playground_snapshot

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / 'research/fresno/local-2026-11-03'


class LocalResearchChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())
        cls.people = {(p['id'], c['name']): (p, c) for p in local_positions(cls.data, 'Fresno')
                      for c in p.get('candidates') or []}

    def test_scope_includes_every_named_on_ballot_local_candidate_and_no_other_races(self):
        planned = inventory(self.data, 'Fresno')
        self.assertEqual(len(planned['candidates']), 84)
        self.assertEqual(planned['unnamed_contests'], ['CA2026-480'])
        self.assertEqual(sum(p['government_level'] in {'County', 'City or town'}
                             for p, c in self.people.values()), 80)
        self.assertTrue(all(len(row['queries']) == 4 for row in planned['candidates']))
        self.assertEqual(inventory(self.data, 'Not a county')['candidates'], [])

    def test_html_profile_marker_does_not_authorize_a_wrong_person_or_directory(self):
        html = '<table class="infobox person"><tr><td>A person</td></tr></table>'
        profile = 'https://ballotpedia.org/Example_Person'
        self.assertTrue(ballotpedia_profile_shape(html, profile))
        for url in ['https://ballotpedia.org/Endorsements_Example',
                    'https://ballotpedia.org/California_elections,_2026',
                    'https://elsewhere.example/Example_Person']:
            self.assertFalse(ballotpedia_profile_shape(html, url))
        self.assertFalse(ballotpedia_profile_shape('<a class="infobox person">Name</a>', profile))
        decision = {'response': {'answers': {
            'identity': {'choice': 'hold', 'probabilities': {'match': .1, 'hold': .9}},
            'link': {'choice': 'supported', 'probabilities': {'supported': .99, 'hold': .01}}}}}
        self.assertFalse(accepted_link({'field': 'ballotpedia_url', 'url': profile}, decision, html))
        decision['response']['answers']['identity'] = {'choice': 'match', 'probabilities': {'match': .89, 'hold': .11}}
        self.assertFalse(accepted_link({'field': 'ballotpedia_url', 'url': profile}, decision, html))

    def test_short_quote_cannot_authorize_invented_context_or_long_quotation(self):
        text = 'Our priorities: repair school buildings and improve student safety.'
        item = {'quote': 'repair school buildings', 'context': text}
        self.assertTrue(literal_proposal(item, text))
        self.assertFalse(literal_proposal({**item, 'context': 'We support a Gaza ceasefire.'}, text))
        self.assertFalse(literal_proposal({'quote': 'repair school buildings', 'context': 'Invented: repair school buildings'}, text))
        long = ' '.join(['word'] * 26)
        self.assertFalse(literal_proposal({'quote': long, 'context': long}, long))

    def test_every_candidate_has_an_explicit_research_disposition(self):
        audit = json.loads((AUDIT / 'research-manifest.json').read_text())
        self.assertEqual(len(audit['queries']), audit['discovery_queries'])
        self.assertEqual(audit['discovery_queries'], 353)
        self.assertEqual({(r['position_id'], r['candidate']) for r in audit['outcomes']}, set(self.people))
        self.assertTrue(all(r['search_complete'] and len(r['queries']) >= 4 for r in audit['outcomes']))
        self.assertEqual(sum(r['grade'] == 'N/A' for r in audit['outcomes']), 79)

    def test_portable_link_decisions_keep_identity_and_literal_profile_proof(self):
        audit = json.loads((AUDIT / 'links-review.json').read_text())
        refs = {}
        for row in audit['reviewed']:
            self.assertEqual(digest(dump(row['decision']['request']).encode()), row['jev_ref'])
            refs[row['jev_ref']] = row
        self.assertEqual(len(audit['changes']), 97)
        for change in audit['changes']:
            source = refs[change['jev_ref']]
            self.assertTrue(accepted_link(source, source['decision'], '\n'.join(source['profile_html_markers'])))
            candidate = self.people[change['position_id'], change['candidate']][1]
            self.assertEqual(candidate[change['field']], change['after'])

    def test_campaign_proposals_are_bound_to_actual_model_inputs_and_literal_source_text(self):
        audit = json.loads((ROOT / 'research/reviews/fresno-local-campaigns-2026-11-03.audit.json').read_text())
        for ref, decision in audit['jev_decisions'].items():
            self.assertEqual(digest(dump(decision['request']).encode()), ref)
        for source in audit['sources']:
            decision = audit['jev_decisions'][source['jev_ref']]
            state = json.loads(decision['request']['state'])
            self.assertEqual(state['source_url'], source['source_url'])
            for i, item in enumerate(source['items']):
                self.assertTrue(literal_proposal(item['proposal'], state['full_source_text']))
                if item['accepted']:
                    answers = decision['response']['answers']
                    self.assertEqual(answers['identity']['choice'], 'match')
                    self.assertGreaterEqual(answers['identity']['probabilities']['match'], .90)
                    self.assertEqual(answers['item_' + str(i)]['choice'], 'supported')
                    self.assertGreaterEqual(answers['item_' + str(i)]['probabilities']['supported'], .85)

    def test_vote_stages_and_iran_statement_are_not_conflated(self):
        arambula = self.people['CA2026-477', 'Joaquin Arambula'][1]['gaza_evidence']
        self.assertEqual([(e['date'], e['quote']) for e in arambula],
                         [('2025-05', 'Joaquin Arambula | Aye'), ('2025-09', 'Joaquin Arambula | Abstain')])
        karbassi = self.people['CA2026-466', 'Mike Karbassi'][1]['gaza_evidence'][0]
        self.assertIn('Iran', karbassi['summary'])
        self.assertEqual(karbassi['dimension'], 'other')
        self.assertNotIn('gaza_evidence', self.people['CA2026-481', 'Gary K. Yep'][1])

    def test_fresh_state_snapshot_and_new_scores_bind_the_final_source_data(self):
        snapshot = json.loads((AUDIT / 'current-jev-states.json').read_text())
        current = {(r['position_id'], r['candidate']): r['state']
                   for r in playground_snapshot(self.data)['candidates']}
        self.assertEqual(snapshot['dataset_sha256'], digest((ROOT / '2026-11-03_Bay_Area_Elections.json').read_bytes()))
        for row in snapshot['candidates']:
            p, c = self.people[row['position_id'], row['candidate']]
            self.assertEqual(row['state'], current[row['position_id'], row['candidate']])
        archive = json.loads((ROOT / self.data['pro_palestine_grading']['archive_path']).read_text())
        rows = {r['id']: r for r in archive['rows']}
        receipt = json.loads((AUDIT / 'score-refresh.json').read_text())
        for change in receipt['changed_candidates']:
            row = rows[change['id']]
            p, c = self.people[row['position_id'], row['candidate']]
            self.assertEqual(row['request']['state'], current[row['position_id'], row['candidate']])
            self.assertNotEqual(c['pro_palestine_score_grade'], 'N/A')
        for name, pid in [('Maria Pacheco', 'CA2026-466'), ('Naindeep Singh', 'CA2026-476'),
                          ('Joaquin Arambula', 'CA2026-477'), ('Ariana Martinez Lott', 'CA2026-478')]:
            c = self.people[pid, name][1]
            self.assertTrue(any(e['endorser'] == 'CAIR Action' and e['relation'] == 'endorsed'
                                for e in c['endorsements']))


if __name__ == '__main__':
    unittest.main()
