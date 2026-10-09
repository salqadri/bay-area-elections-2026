"""Check guide completeness, recommendation polarity and observation provenance."""
from copy import deepcopy
import json
import unittest

from import_peace_guides import ROOT, REVIEW, apply_guides, check_guides, reviewed_findings
from check_evidence import check_evidence


class GuideChecks(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())
        self.review = json.loads(REVIEW.read_text())
        self.people = {(p['id'], c['name']): c for p in self.data['positions'] for c in p.get('candidates') or []}

    def test_all_source_cards_accounted_for(self):
        findings, evidence = reviewed_findings(self.data, self.review)
        self.assertEqual((len(findings), len(evidence)), (70, 14))
        self.assertEqual(len(self.review['vote_for_peace_cards']), 152)
        self.assertEqual(len(self.review['aroc_cards']), 44)
        self.assertFalse(check_guides(self.data))
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
            self.assertTrue(check_guides(data))

    def test_guide_dates_are_observations_not_historical_dates(self):
        self.assertFalse(check_evidence(self.data))
        for finding in self.review['gaza_findings']:
            record = finding['record']
            self.assertEqual(record['date_method'], 'source_observed')
            self.assertEqual(record['date'], record['checked_on'])
            self.assertTrue(record['date_note'])
        record = next(r for c in self.people.values() for r in c.get('gaza_evidence', []) if r['date_method'] == 'source_observed')
        record['date'] = '2026-01-01'
        self.assertTrue(any('guide observation' in e for e in check_evidence(self.data)))

    def test_import_preserves_existing_data_and_is_idempotent(self):
        before = deepcopy(self.data)
        self.assertEqual(apply_guides(self.data, self.review), before)
        self.assertEqual(apply_guides(self.data, self.review), before)
        from apply_endorsement_review import apply_review, REVIEW as PRIOR_REVIEW, EXPORT
        export = json.loads(EXPORT.read_text())
        self.assertEqual(apply_review(self.data, json.loads(PRIOR_REVIEW.read_text()), export)[0], before)


if __name__ == '__main__':
    unittest.main()
