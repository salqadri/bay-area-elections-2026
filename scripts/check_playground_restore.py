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
        self.assertEqual(len(runs), 3)
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
            for _, raw in runs[1:]:
                update = json.loads(raw)
                expected = update['rows'][0]
                actual = next(row for row in bootstrap['latest']['rows'] if row['id'] == expected['id'])
                self.assertEqual(actual['request'], expected['request'])
                self.assertEqual(actual['response'], expected['response'])
                self.assertEqual(actual['evaluation']['run_id'], update['id'])
                self.assertEqual(bootstrap['questions'], update['questions'])
            haney = next(row for row in bootstrap['latest']['rows'] if row['candidate'] == 'Matt Haney')
            self.assertTrue(any('genocide' in text and 'owner confirmed' in text
                                for text in haney['request']['state']['gaza_evidence']))

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
