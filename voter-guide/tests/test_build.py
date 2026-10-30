"""Import fidelity and publication-boundary checks against the real source JSON."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('tall_build', ROOT / 'voter-guide/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class GuideImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset_path = ROOT / '2026-11-03_Bay_Area_Elections.json'
        cls.plan_path = builder.DEFAULT_PLAN
        cls.dataset = json.loads(cls.dataset_path.read_text())
        cls.plan = json.loads(cls.plan_path.read_text())
        cls.projected = builder.project(cls.dataset, cls.plan)

    def test_only_confirmed_in_scope_contests(self):
        scope = {c['name'] for c in self.dataset['election']['counties_in_scope']}
        expected = {p['id'] for p in self.dataset['positions'] if p['ballot_status'] == 'confirmed' and scope.intersection(p['counties'])}
        self.assertEqual({p['id'] for p in self.projected['positions']}, expected)
        self.assertEqual(len(expected), len(self.projected['positions']))

    def test_every_decision_and_rationale_is_verbatim(self):
        plans = {r['position_id']: r for r in self.plan['races']}
        for p in self.projected['positions']:
            r = plans[p['id']]
            self.assertEqual(p['recommendation']['candidate'], r.get('recommended'))
            self.assertEqual(p['recommendation']['reason'], ((r.get('recommend_reason_text') or r.get('summary'))['text'] if r.get('recommended') else r['recommend_reason']))

    def test_every_candidate_blurb_and_identity_are_verbatim(self):
        positions = {p['id']: p for p in self.dataset['positions']}
        for p in self.projected['positions']:
            original = positions[p['id']]
            candidates = (original.get('candidates') or []) + (original.get('qualified_write_in_candidates') or [])
            self.assertEqual(len(p['candidates'] or []), len(candidates))
            for result, source in zip(p['candidates'] or [], candidates):
                self.assertEqual(result['name'], source['name'])
                self.assertEqual(result.get('party'), source.get('party'))
                self.assertEqual(result.get('incumbent'), source.get('incumbent'))
                self.assertEqual(result.get('blurb', ''), (source.get('pro_palestine_explanation') or {}).get('summary', ''))

    def test_writeins_are_labeled_and_unconfirmed_filers_omitted(self):
        positions = {p['id']: p for p in self.dataset['positions']}
        for p in self.projected['positions']:
            original = positions[p['id']]
            writeins = {c['name'] for c in original.get('qualified_write_in_candidates') or []}
            for c in p['candidates'] or []:
                self.assertEqual(c.get('write_in', False), c['name'] in writeins)
            self.assertFalse({c['name'] for c in original.get('filed_candidates_not_confirmed_on_ballot') or []}.intersection(c['name'] for c in p['candidates'] or []))

    def test_research_and_sensitive_registry_fields_are_not_exported(self):
        for p in self.projected['positions']:
            self.assertLessEqual(set(p), {*builder.POSITION_FIELDS, 'candidates', 'recommendation'})
            for c in p['candidates'] or []:
                self.assertLessEqual(set(c), {'name', 'party', 'incumbent', 'write_in', 'blurb'})
        self.assertLessEqual(set(self.projected), {'format','election','codes','recommendations_date','county_election_urls','positions'})

    def test_mismatched_publication_is_rejected(self):
        plan = copy.deepcopy(self.plan); plan['source_score_publication_id'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'publication IDs'):
            builder.project(self.dataset, plan)

    def test_missing_race_decision_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        target = self.projected['positions'][0]['id']
        plan['races'] = [r for r in plan['races'] if r['position_id'] != target]
        with self.assertRaisesRegex(ValueError, 'Missing or stale'):
            builder.project(self.dataset, plan)

    def test_changed_roster_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        next(r for r in plan['races'] if r['position_id'] == self.projected['positions'][0]['id'])['roster'][0]['name'] = 'Changed name'
        with self.assertRaisesRegex(ValueError, 'roster differs'):
            builder.project(self.dataset, plan)

    def test_changed_explanation_binding_is_rejected(self):
        data = copy.deepcopy(self.dataset)
        next(p for p in data['positions'] if p['id'] == self.projected['positions'][0]['id'])['candidates'][0]['pro_palestine_explanation']['request_sha256'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'Stale candidate explanation'):
            builder.project(data, self.plan)

    def test_stale_dataset_hash_stops_build_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); changed = folder / 'dataset.json'
            changed.write_bytes(self.dataset_path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'dataset changed'):
                builder.build(changed, self.plan_path, folder / 'dist')
            self.assertFalse((folder / 'dist').exists())

    def test_bundle_is_allowlisted_and_hashes_match(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'dist'
            builder.build(self.dataset_path, self.plan_path, out)
            expected = {'index.html','candidates.html','404.html','guide.json','config.js','style.css','app.js','google-autocomplete.js','ballot-order.js','address-services.js','address-matcher.js','favicon.svg','robots.txt','sitemap.xml','release.json'}
            self.assertEqual({p.name for p in out.iterdir()}, expected)
            manifest = json.loads((out / 'release.json').read_text())
            for name, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)
            # The original matching/service code is reused without mutation.
            self.assertEqual((out / 'address-services.js').read_bytes(), (ROOT / 'src/address-services.js').read_bytes())
            self.assertFalse(manifest['google_autocomplete_configured'])

    def test_production_target_does_not_change_the_research_target(self):
        config = json.loads((ROOT / 'firebase.voter-guide.json').read_text())
        targets = json.loads((ROOT / '.firebaserc').read_text())['targets']['tall-bay-area-voter-guide']['hosting']
        self.assertEqual(config['hosting']['public'], 'voter-guide/dist')
        self.assertEqual(config['hosting']['target'], 'voter-guide')
        self.assertEqual(targets['voter-guide'], ['tall-voter-guide'])
        self.assertEqual(targets['research-tool'], ['tall-bay-area-research-tool'])
        self.assertNotIn('rewrites', config['hosting'])


if __name__ == '__main__':
    unittest.main()
