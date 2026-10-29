"""Offline publication and cache regressions for current race recommendations."""
from copy import deepcopy
import hashlib
import json
import re
import unittest

import build_recommendations as rec
import build_site


class RecommendationChecks(unittest.TestCase):
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
