"""Offline CAIR capture, disposition, replacement and polarity regressions."""
import copy
import json
from pathlib import Path
import unittest

from import_cair_guide import URL, DATA, REVIEW, parse_capture, recommendation, reviewed_records, apply_capture
from check_published_endorsements import check_endorsements
from research_test_fixtures import before_registered_updates


def card(ident, name, level, office='Example School Board Area 2', annotation=''):
    return (f'<div data-testid="card-endorsement-{ident}"><img alt="ignore" src="/portrait">'
            f'<span data-testid="text-candidate-name-{ident}">{name}</span><p>{office}</p>'
            f'<p>{annotation}</p><div data-testid="endorsement-level-{level.lower()}">{level}</div></div>')


class CaptureChecks(unittest.TestCase):
    def test_recommendation_levels_and_cross_election_annotations_survive(self):
        html = '<span class="uppercase">School District</span>' + ''.join(card(i, 'Alex Rivera', level, annotation='Also in Primary (6/2/26)') for i, level in enumerate(['Endorsed', 'Preferred', 'Oppose', 'Joint Endorsement']))
        parsed = parse_capture(html.encode(), '2026-10-09')
        self.assertEqual(parsed['card_count'], 4)
        self.assertEqual([x['level'] for x in parsed['cards']], ['Endorsed', 'Preferred', 'Oppose', 'Joint Endorsement'])
        self.assertEqual(parsed['cards'][0]['annotations'], ['Also in Primary (6/2/26)'])
        review = {**parsed, 'phase': 'unspecified', 'publication_note_id': 'N1'}
        records = [recommendation(c, review) for c in parsed['cards']]
        self.assertEqual([r['relation'] for r in records], ['endorsed', 'preferred', 'opposed', 'endorsed'])
        self.assertTrue(records[-1]['shared'])
        self.assertTrue(all(r['phase'] == 'unspecified' and r['url'] == URL for r in records))

    def test_unknown_level_and_incomplete_card_fail_closed(self):
        for html in [card(1, 'Alex Rivera', 'Probably'), card(1, 'Alex Rivera', 'Endorsed', office=''), '<div>No cards</div>']:
            with self.assertRaises(ValueError):
                parse_capture(html.encode(), '2026-10-09')

    def test_duplicate_source_card_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            parse_capture((card(1, 'Alex Rivera', 'Preferred') * 2).encode(), '2026-10-09')

    def test_conflicting_levels_cannot_be_deduplicated(self):
        capture = parse_capture((card(1, 'Alex Rivera', 'Preferred') + card(2, 'Alex Rivera', 'Oppose')).encode(), '2026-10-09')
        capture.update(phase='unspecified', publication_note_id='N1', dispositions={
            '1': {'action': 'publish', 'position_id': 'P1', 'candidate': 'Alex Rivera', 'reason': 'Matched office.'},
            '2': {'action': 'duplicate', 'position_id': 'P1', 'candidate': 'Alex Rivera', 'duplicate_of': '1', 'reason': 'Candidate repeated.'}})
        data = {'positions': [{'id': 'P1', 'candidates': [{'name': 'Alex Rivera'}]}]}
        with self.assertRaisesRegex(ValueError, 'conflicting duplicate'):
            reviewed_records(data, capture)


class PublishedChecks(unittest.TestCase):
    def setUp(self):
        self.current = json.loads(DATA.read_text())
        self.data = before_registered_updates(self.current)
        self.review = json.loads(REVIEW.read_text())

    def test_all_200_cards_accounted_for_and_95_candidacies_published(self):
        records = reviewed_records(self.data, self.review)
        self.assertEqual(len(records), 95)
        self.assertEqual(self.review['card_count'], 200)
        self.assertEqual(self.review['disposition_counts'], {'not_in_current_roster': 102, 'publish': 95, 'duplicate': 2, 'held_office_mismatch': 1})
        self.assertFalse(check_endorsements(self.current))
        self.assertFalse(check_endorsements(self.data, reviews=[]))

    def test_opposition_preference_and_duplicate_handling(self):
        records = reviewed_records(self.data, self.review)
        self.assertEqual(records[('CA2026-150', 'Marc Cooper')]['relation'], 'opposed')
        self.assertEqual(records[('CA2026-309', 'John Garamendi')]['relation'], 'preferred')
        for pid, name in [('CA2026-101', 'Peter Ortiz'), ('CA2026-103', 'Gordon Chester')]:
            person = next(c for p in self.data['positions'] if p['id'] == pid for c in p['candidates'] if c['name'] == name)
            self.assertEqual(len([r for r in person['endorsements'] if r['endorser'] == 'CAIR Action']), 1)
        self.assertNotIn(('CA2026-170', 'Tomara Hall'), records)

    def test_import_is_idempotent_and_preserves_other_publishers(self):
        original = copy.deepcopy(self.data)
        self.assertEqual(apply_capture(self.data, self.review), original)
        self.assertEqual(apply_capture(self.data, self.review), original)

    def test_wrong_relation_missing_record_and_secondary_url_fail_publication(self):
        for change in ('relation', 'url', 'remove'):
            d = copy.deepcopy(self.data)
            person = next(c for p in d['positions'] if p['id'] == 'CA2026-150' for c in p['candidates'] if c['name'] == 'Marc Cooper')
            record = next(r for r in person['endorsements'] if r['endorser'] == 'CAIR Action')
            if change == 'remove':
                person['endorsements'].remove(record)
            else:
                record[change] = 'endorsed' if change == 'relation' else 'https://bluevoterguide.org/endorser-org/CAIR_Action/CA/7054'
            self.assertTrue(check_endorsements(d, reviews=[]))


if __name__ == '__main__':
    unittest.main()
