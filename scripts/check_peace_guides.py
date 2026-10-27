"""Check guide completeness, recommendation polarity and observation provenance."""
from copy import deepcopy
import json
import unittest

from import_peace_guides import ROOT, REVIEW, apply_guides, check_guides, reviewed_findings
from check_evidence import check_evidence
from research_test_fixtures import before_registered_updates


class GuideChecks(unittest.TestCase):
    def setUp(self):
        self.current = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())
        self.data = before_registered_updates(self.current)
        self.review = json.loads(REVIEW.read_text())
        self.people = {(p['id'], c['name']): c for p in self.data['positions'] for c in p.get('candidates') or []}

    def test_all_source_cards_accounted_for(self):
        findings, evidence = reviewed_findings(self.data, self.review)
        self.assertEqual((len(findings), len(evidence)), (70, 14))
        self.assertEqual(len(self.review['vote_for_peace_cards']), 152)
        self.assertEqual(len(self.review['aroc_cards']), 44)
        self.assertFalse(check_guides(self.current))
        self.assertFalse(check_guides(self.data, updates=[]))
        self.review['aroc_cards'].pop()
        with self.assertRaises(ValueError):
            reviewed_findings(self.data, self.review)

    def test_neutral_primary_and_source_badges_are_not_promoted(self):
        for card in self.review['vote_for_peace_cards']:
            if card['action'] == 'neutral_no_recommendation':
                records = self.people[(card['position_id'], card['candidate'])].get('endorsements', [])
                self.assertFalse(any(r['endorser'] == 'Vote for Peace' for r in records))
        panetta = self.people[('CA2026-007', 'Jimmy Panetta')]
        self.assertEqual(next(r['phase'] for r in panetta['endorsements'] if r['endorser'] == 'Vote for Peace'), 'primary')
        ortiz = self.people[('CA2026-101', 'Peter Ortiz')]
        self.assertEqual(next(r['relation'] for r in ortiz['endorsements'] if r['endorser'] == 'CAIR Action'), 'preferred')
        track = [r for c in self.people.values() for r in c.get('endorsements', []) if r['endorser'].startswith('Track AIPAC')]
        self.assertEqual(len(track), 3)
        self.assertTrue(all(r['relation'] == 'endorsed' for r in track))

    def test_polarity_missing_and_unreviewed_recommendations_fail(self):
        for mutation in ('flip', 'remove', 'add'):
            data = deepcopy(self.data)
            person = next(c for p in data['positions'] for c in p.get('candidates') or [] if c['name'] == 'Steve Hilton')
            record = next(r for r in person['endorsements'] if r['endorser'] == 'Vote for Peace')
            if mutation == 'flip':
                record['relation'] = 'endorsed'
            elif mutation == 'remove':
                person['endorsements'].remove(record)
            else:
                person['endorsements'].append({**record, 'endorser': 'AROC Action', 'relation': 'endorsed'})
            self.assertTrue(check_guides(data, updates=[]))

    def test_guide_dates_are_observations_not_historical_dates(self):
        # Importer tests use the historical baseline; evidence publication must
        # validate the current reviewed data against the current quarantine.
        self.assertFalse(check_evidence(self.current))
        for finding in self.review['gaza_findings']:
            record = finding['record']
            self.assertEqual(record['date_method'], 'source_observed')
            self.assertEqual(record['date'], record['checked_on'])
            self.assertTrue(record['date_note'])
        record = next(r for p in self.current['positions'] for c in p.get('candidates') or [] for r in c.get('gaza_evidence', []) if r['date_method'] == 'source_observed')
        record['date'] = '2026-01-01'
        self.assertTrue(any('guide observation' in e for e in check_evidence(self.current)))

    def test_import_preserves_existing_data_and_is_idempotent(self):
        before = deepcopy(self.data)
        self.assertEqual(apply_guides(self.data, self.review), before)
        self.assertEqual(apply_guides(self.data, self.review), before)
        from apply_endorsement_review import apply_review, REVIEW as PRIOR_REVIEW, EXPORT
        export = json.loads(EXPORT.read_text())
        self.assertEqual(apply_review(deepcopy(self.current), json.loads(PRIOR_REVIEW.read_text()), export)[0], self.current)


class RefreshChecks(unittest.TestCase):
    def test_current_capture_is_complete_and_bound_without_changing_source_labels(self):
        from sync_vote_for_peace import LABELS, same_office, state_of
        from serve_jev_playground import playground_state
        data=json.loads((ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())
        capture=json.loads((ROOT/'research/endorsements/vote-for-peace-2026-10-27.json').read_text())
        dispositions=json.loads((ROOT/'research/endorsements/vote-for-peace-dispositions-2026-10-27.json').read_text())
        review=json.loads((ROOT/'research/reviews/vote-for-peace-2026-10-27.json').read_text())
        self.assertEqual(len(capture['cards']),1429)
        self.assertEqual(len(dispositions['cards']),len(capture['cards']))
        self.assertEqual(len({c['source_id'] for c in dispositions['cards']}),1429)
        self.assertEqual(len(review['decisions']),132)
        cards={c['id']:c for c in capture['cards']}
        positions={p['id']:p for p in data['positions']}
        for d in review['decisions']:
            p=positions[d['position_id']];card=cards[d['source_key'].removeprefix('vfp-')]
            self.assertEqual(state_of(p),card['state_abbr']);self.assertTrue(same_office(p,card))
            label,relation=LABELS[card['our_rating']]
            self.assertEqual(d['after']['relation'],relation);self.assertEqual(d['after']['quote'],label)
            c=next(c for roster in ('candidates','filed_candidates_not_confirmed_on_ballot','qualified_write_in_candidates') for c in p.get(roster) or [] if c['name']==d['candidate'])
            self.assertEqual(c['endorsements'].count(d['after']),1)
            state=playground_state(p,c,data)
            record=next(e for e in state['focused_endorsement_observations'] if e['endorser']=='Vote for Peace' and e['phase']==card['election_stage'])
            self.assertEqual(record['relation'],relation)
            self.assertEqual(record.get('rating') or record.get('source_label'),label)
        garamendi=next(d for d in review['decisions'] if d['candidate']=='John Garamendi')
        self.assertEqual(garamendi['before']['relation'],'opposed');self.assertEqual(garamendi['after']['rating'],'Ally')

    def test_parser_fails_closed_on_unknown_ratings_and_conflicting_source_ids(self):
        from sync_vote_for_peace import source_cards
        card={'id':'source-1','name':'Example','slug':'example','state_abbr':'CA','office_title':'Governor','our_rating':'vote','election_stage':'general','election_date':'Nov 3, 2026'}
        def html(cards):return '<script>self.__next_f.push('+json.dumps([1,'a:'+json.dumps(cards)])+')</script>'
        self.assertEqual(len(source_cards(html([card,card]))),1)
        with self.assertRaises(ValueError):source_cards(html([card,{**card,'our_rating':'neutral'}]))
        with self.assertRaises(ValueError):source_cards(html([{**card,'our_rating':'new-label'}]))
        with self.assertRaises(ValueError):source_cards('<html>Source layout changed</html>')

    def test_identity_rejects_wrong_district_and_absence_does_not_remove_prior_records(self):
        from sync_vote_for_peace import draft, same_office
        data=json.loads((ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())
        p=next(p for p in data['positions'] if p['id']=='CA2026-309')
        card={'office_title':'U.S. Representative','district':'8'}
        self.assertTrue(same_office(p,card));self.assertFalse(same_office(p,{**card,'district':'9'}))
        self.assertFalse(same_office(p,{**card,'office_title':'U.S. Senator'}))
        original=deepcopy(data)
        review,dispositions=draft(data,{'cards':[],'checked_on':'2026-10-27','content_sha256':'0'*64},'empty-source-check')
        self.assertEqual(review['decisions'],[]);self.assertEqual(data,original)

    def test_superseded_evidence_notes_are_not_used_in_current_inputs(self):
        from serve_jev_playground import playground_state
        data=json.loads((ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())
        for name in ('John Garamendi','Sam Liccardo'):
            p=next(p for p in data['positions'] if any(c['name']==name for c in p.get('candidates') or []))
            c=next(c for c in p['candidates'] if c['name']==name)
            notes=[e for e in c['gaza_evidence'] if 'voteforpeace.info' in e['url']]
            self.assertEqual(len(notes),1);self.assertEqual(notes[0]['checked_on'],'2026-10-27')
            self.assertEqual(notes[0]['date'],notes[0]['checked_on'])
            state=playground_state(p,c,data)
            text=' '.join(state.get('gaza_evidence',[]))
            self.assertNotIn('guide’s Neutral label',text)
            if name=='John Garamendi':self.assertNotIn('reports AIPAC/allied-lobby funding',text)


if __name__ == '__main__':
    unittest.main()
