"""Offline reproduction and safety checks for the portable playground review."""
import json
from pathlib import Path
import tempfile
import unittest

from restore_jev_playground import DEFAULT_BUNDLE, load_review, restore
from serve_jev_playground import RunManager


class RestoreChecks(unittest.TestCase):
    def test_fresh_restore_reproduces_latest_candidate_results_and_thresholds(self):
        manifest, mapping, runs = load_review()
        self.assertEqual(len(runs), len(manifest['runs']))
        self.assertGreaterEqual(len(runs), 3)
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            self.assertEqual(restore(work=work)['restored_runs'], len(runs))
            self.assertEqual(restore(work=work)['already_present_runs'], len(runs))
            for run_id, raw in runs:
                self.assertEqual((work / 'runs' / run_id / 'run.json').read_bytes(), raw)
            manager = RunManager(work=work)
            bootstrap = manager.bootstrap()
            self.assertEqual(bootstrap['score_grade_mapping'], mapping)
            self.assertEqual(len(bootstrap['latest']['rows']), 1296)
            self.assertEqual(bootstrap['latest']['completed'], 1296)
            self.assertEqual(set(bootstrap['questions']), {'pro_palestine_score', 'evidence_score'})
            updates = {}
            for _, raw in runs[1:]:
                update = json.loads(raw)
                for expected in update['rows']:
                    updates[expected['id']] = (update, expected)
            for update, expected in updates.values():
                actual = next(row for row in bootstrap['latest']['rows'] if row['id'] == expected['id'])
                self.assertEqual(actual['request'], expected['request'])
                self.assertEqual(actual['response'], expected['response'])
                self.assertEqual(actual['evaluation']['run_id'], update['id'])
            haney = next(row for row in bootstrap['latest']['rows'] if row['candidate'] == 'Matt Haney')
            self.assertTrue(any('genocide' in text and 'owner confirmed' in text
                                for text in haney['request']['state']['gaza_evidence']))
            gabriel = next(row for row in bootstrap['latest']['rows'] if row['candidate'] == 'Gabriel Gutierrez')
            self.assertTrue(any('Community report:' in text and 'divesting from Israel' in text
                                for text in gabriel['request']['state']['gaza_evidence']))
            merchant = next(row for row in bootstrap['latest']['rows'] if row['candidate'] == 'Shahida S. Merchant')
            self.assertEqual(len(merchant['request']['state']['campaign_platform_points']), 5)

    def test_acjdc_targeted_refresh_preserves_unaffected_results(self):
        manifest, mapping, runs = load_review()
        entry = next(x for x in manifest['runs'] if '/acjdc-refresh-2026-11-02/' in x['path'])
        run = next(json.loads(raw) for id_, raw in runs if id_ == entry['run_id'])
        root = Path(__file__).resolve().parent.parent
        scope = json.loads((root/'research/questionnaires/acjdc-2026-11-02/state-changes.json').read_text())['candidates']
        self.assertEqual({(r['position_id'],r['candidate']) for r in run['rows']},
                         {(r['position_id'],r['candidate']) for r in scope})
        self.assertEqual(len(run['rows']), 44)
        self.assertEqual(run['score_grade_mapping'], mapping)
        # This historical targeted run retains its own v9 questions even when
        # a later full-roster run becomes the preferred prompt.
        original_questions = json.loads((root/'research/gaza-grading/criteria-pro-palestine-v9.json').read_text())['questions']
        self.assertEqual(run['questions'], original_questions)
        self.assertEqual(set(run['questions']), {'pro_palestine_score','evidence_score'})
        self.assertIn('v24-acjdc-questionnaires', run['state_version'])
        before = {}
        for id_, raw in runs:
            if id_ == run['id']:
                break
            before.update({r['id']:r for r in json.loads(raw)['rows']})
        after = {**before, **{r['id']:r for r in run['rows']}}
        affected = {r['id'] for r in run['rows']}
        self.assertEqual(len(after), 1296)
        self.assertEqual(sum(after[id_] != row for id_,row in before.items()), 44)
        self.assertTrue(all(after[id_] == row for id_,row in before.items() if id_ not in affected))

    def test_acjdc_summaries_are_bound_to_fresh_scores_and_all_race_inputs(self):
        import hashlib
        from generate_grade_explanations import validate, summary_inventory
        from summary_source_policy import policy_for_state
        from score_grade import row_grade
        from build_recommendations import cached_pick_matches, jev_request, CAT_JEV
        manifest, mapping, runs = load_review()
        root = Path(__file__).resolve().parent.parent
        run = next(json.loads(raw) for _,raw in runs if json.loads(raw).get('scope') == 'source-refresh')
        latest = {}
        for id_,raw in runs:
            latest.update({row['id']:row for row in json.loads(raw)['rows']})
            if id_ == run['id']:break
        people = {row['id']:row for row in run['rows']}
        outputs = []
        for entry in manifest['review_outputs']:
            if '/acjdc-refresh-2026-11-02/' not in entry['path']:
                continue
            raw = (root/entry['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['sha256'])
            outputs.append(json.loads(raw))
        candidate_outputs = [x for x in outputs if x.get('format') == 'held-grade-explanation/v1']
        self.assertEqual({x['candidate_id'] for x in candidate_outputs},
                         {cid for cid,row in people.items() if row_grade(row,mapping) != 'N/A'})
        for result in candidate_outputs:
            row = people[result['candidate_id']]
            self.assertEqual(result['grade'], row_grade(row,mapping))
            self.assertIsNone(validate(result,row,result['grade'],policy_for_state(row['request']['state'],row['position_id']),summary_inventory(row)))
            self.assertLessEqual(len(result['summary'].split()),80)
            self.assertIn('generation_request_sha256',result)
            self.assertNotEqual(result['generation_request_sha256'],result['request_sha256'])
        plan = next(x for x in outputs if x.get('format') == 'held-source-refresh-plan/v1')
        self.assertEqual({r['position_id'] for r in plan['races']},
                         {r['position_id'] for r in run['rows']} | set(plan.get('additional_narrative_only_races',[])))
        for race in plan['races']:
            if race['category'] == CAT_JEV:
                self.assertTrue(cached_pick_matches(race['jev'],jev_request(race)))
        race_outputs = [x for x in outputs if x.get('format') == 'held-race-rationale/v1']
        self.assertEqual({x['position_id'] for x in race_outputs},
                         {r['position_id'] for r in plan['races'] if r.get('recommended')})
        for output in race_outputs:
            expected = {cid:r['request_sha256'] for cid,r in latest.items() if r['position_id'] == output['position_id']}
            self.assertEqual(output['source_candidate_request_sha256'],expected)
            self.assertLessEqual(len(output['text'].split()),200)

    def test_preserves_existing_local_thresholds(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            existing = {'upper_bounds': [.1, 1, 2, 3, 4], 'minimum_evidence_score': .4}
            path = work / 'score-grade-mapping.json'
            path.write_text(json.dumps(existing))
            self.assertEqual(restore(work=work)['thresholds'], 'preserved_existing')
            self.assertEqual(json.loads(path.read_text()), existing)

    def test_conflicting_history_is_rejected_before_writing(self):
        _, _, runs = load_review()
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            target = work / 'runs' / runs[-1][0] / 'run.json'
            target.parent.mkdir(parents=True)
            target.write_text('different local history')
            with self.assertRaisesRegex(ValueError, 'Refusing to overwrite'):
                restore(work=work)
            self.assertEqual(target.read_text(), 'different local history')
            self.assertFalse((work / 'runs' / runs[0][0]).exists())

    def test_tampered_bundle_is_rejected(self):
        manifest = json.loads(DEFAULT_BUNDLE.read_text())
        manifest['runs'][0]['sha256'] = '0' * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'manifest.json'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                load_review(path)


if __name__ == '__main__':
    unittest.main()
