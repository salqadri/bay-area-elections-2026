"""Offline publication and cache regressions for current race recommendations."""
from copy import deepcopy
import hashlib
import json
import re
import unittest

import build_recommendations as rec


class RecommendationChecks(unittest.TestCase):
    def test_current_page_plan_and_score_publication_agree(self):
        data = json.loads(rec.DATA.read_text())
        plan = json.loads(rec.PLAN.read_text())
        page = json.loads(re.search(r'<script type="application/json" id="rec-data">(.*?)</script>',
                                    rec.OUT_HTML.read_text(), re.S).group(1))
        dataset_hash = hashlib.sha256(rec.DATA.read_bytes()).hexdigest()
        self.assertEqual(plan['source_dataset_sha256'], dataset_hash)
        self.assertEqual(page['source_dataset_sha256'], dataset_hash)
        self.assertEqual(page['plan_sha256'], hashlib.sha256(rec.PLAN.read_bytes()).hexdigest())
        self.assertEqual(plan['source_score_publication_id'], data['pro_palestine_grading']['publication_id'])
        rec.validate_plan(plan['races'], data)
        rec.validate_plan(page['races'], data)
        self.assertEqual(plan['counts'], page['counts'])
        expected = {r['position_id']: r for r in plan['races']}
        for race in page['races']:
            without_order = {k: v for k, v in race.items() if k != 'order'}
            self.assertEqual(without_order, expected[race['position_id']])

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
        old = json.loads((rec.OUTDIR/'recommendations-2026-10-28.json').read_text())
        with self.assertRaisesRegex(ValueError, 'Stale|differs'):
            rec.validate_plan(old['races'], data)


if __name__ == '__main__':
    unittest.main()
