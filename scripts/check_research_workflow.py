"""Offline county expansion and reviewed rerun regressions; no live research."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publication_reviews as history
import research_endorsements as collector
from research_scope import DATA, REGISTRY, select_scope, scope_report
import reviewed_updates as updates

BASE = json.loads(DATA.read_text())


def review_for(data=BASE, publisher='Example Civic Organization'):
    p = next(p for p in data['positions'] if p['id'] == 'CA2026-014')
    c = next(c for c in p['candidates'] if c['name'] == 'Steve Hilton')
    source = {'url': 'https://example.org/reviewed-endorsements', 'publisher': publisher, 'role': 'endorser',
              'checked_on': '2026-10-09', 'retrieval': 'test_fixture', 'content_sha256': sha256(b'invented test fixture').hexdigest()}
    record = {'endorser': publisher, 'kind': 'organization', 'relation': 'endorsed', 'phase': 'general',
              'url': source['url'], 'checked_on': source['checked_on'], 'verification': 'endorser_statement'}
    decision = {'id': 'source-card-1', 'action': 'change', 'source_key': 'source1', 'position_id': p['id'], 'candidate': c['name'],
                'identity': updates.identity(p), 'field': 'endorsements', 'before': None, 'after': record,
                'reason': 'Invented candidate-specific general-election endorsement used only for offline tests.',
                'evidence': {'identity_basis': 'Fixture names the candidate and the office of governor.',
                             'date_basis': 'Fixture explicitly identifies the November 2026 general election.',
                             'relationship_basis': 'Fixture explicitly endorses the named candidate.'}}
    return {'version': 1, 'id': 'test-general-review', 'election_date': data['election']['date'], 'reviewed_on': '2026-10-09',
            'counties': ['Alameda'], 'sources': {'source1': source}, 'notes': {}, 'decisions': [decision]}


class ScopeChecks(unittest.TestCase):
    def test_county_union_deduplicates_shared_contests(self):
        selected = select_scope(BASE, ['alameda', 'CONTRA COSTA', 'Alameda'])
        ps = selected['positions']
        self.assertEqual(len({p['id'] for p in ps}), len(ps))
        self.assertTrue(all(set(p['counties']) & {'Alameda', 'Contra Costa'} for p in ps))
        self.assertEqual(selected['requested_counties'], ['Alameda', 'Contra Costa'])
        with self.assertRaises(ValueError):
            select_scope(BASE, ['Santa Clra'])

    def test_presets_separate_requested_scope_from_actual_inventory(self):
        self.assertEqual(len(REGISTRY['counties']), 58)
        self.assertEqual(len({c['fips'] for c in REGISTRY['counties']}), 58)
        bay = scope_report(BASE, scope='bay-area')
        ca = scope_report(BASE, scope='california')
        registered = {c['name'] for c in BASE['election']['counties_in_scope']}
        self.assertEqual(set(bay['missing_counties']), set(REGISTRY['bay_area']) - registered)
        self.assertEqual(len(ca['requested_counties']), 58)
        self.assertEqual(ca['unique_contests'], len(BASE['positions']))
        self.assertTrue(all(not r['inventory_started'] and r['contests'] == 0 for r in ca['county_queue'] if r['county'] in ca['missing_counties']))

    def test_new_bay_and_non_bay_counties_need_no_county_specific_code(self):
        data = deepcopy(BASE)
        for county in ['Marin', 'Los Angeles']:
            data['election']['counties_in_scope'].append({'name': county})
            template = deepcopy(next(p for p in data['positions'] if p['government_level'] == 'City or town' and p.get('candidates')))
            template.update(id='fixture-' + county, counties=[county])
            data['positions'].append(template)
            selected = select_scope(data, [county])
            self.assertEqual(len(selected['positions']), 1)
            self.assertFalse(selected['missing_counties'])
        self.assertNotIn('Marin', scope_report(data, scope='bay-area')['missing_counties'])
        self.assertNotIn('Los Angeles', scope_report(data, scope='california')['missing_counties'])

    def test_ledger_scope_is_explicit_cached_and_cannot_silently_change(self):
        with tempfile.TemporaryDirectory() as temp:
            db = collector.connect(Path(temp) / 'ledger.sqlite3')
            seeds = Path(temp) / 'seeds.json'
            seeds.write_text('{"sources": [], "queries": []}')
            try:
                first = collector.plan(db, DATA, seeds, counties=['Contra Costa'])
                q = db.execute('SELECT q FROM queries LIMIT 1').fetchone()[0]
                db.execute('UPDATE queries SET state="done" WHERE q=?', (q,)); db.commit()
                self.assertEqual(collector.plan(db, DATA, seeds, counties=['Contra Costa']), first)
                self.assertEqual(db.execute('SELECT state FROM queries WHERE q=?', (q,)).fetchone()[0], 'done')
                self.assertTrue(all('Contra Costa' in c['counties'] for c in collector.roster(db).values()))
                self.assertFalse(any('"Alameda"' in r['q'] for r in db.execute('SELECT q FROM queries')))
                with self.assertRaisesRegex(ValueError, 'separate ledger'):
                    collector.plan(db, DATA, seeds, counties=['Alameda'])
                self.assertEqual(collector.setting(db, 'county_scope'), ['Contra Costa'])
            finally:
                db.close()


class UpdateChecks(unittest.TestCase):
    def test_cair_adapter_preserves_unknown_phase_and_original_capture_date(self):
        from import_cair_guide import parse_capture
        capture = parse_capture(b'<div data-testid="card-endorsement-1"><span data-testid="text-candidate-name-1">Steve Hilton</span><p>Governor of California</p><p>Also in Primary (6/2/26)</p><div data-testid="endorsement-level-preferred">Preferred</div></div>', '2026-10-08')
        review = updates.draft(BASE, capture, 'cair-parser-fixture', '2026-10-09', ['Alameda'])
        card = review['decisions'][0]
        self.assertEqual(card['action'], 'hold')
        self.assertEqual(card['source_observation']['label'], 'Preferred')
        self.assertEqual(card['source_observation']['phase'], 'unspecified')
        self.assertEqual(review['sources']['cair']['checked_on'], '2026-10-08')
        self.assertEqual(len(card['suggested_matches']), 1)

    def test_draft_never_publishes_exact_matches_or_source_badges(self):
        review = review_for()
        capture = {'sources': review['sources'], 'cards': [
            {'id': '1', 'name': 'Steve Hilton', 'office_context': 'Governor of California', 'source_key': 'source1', 'label': 'Sources: Example Civic Organization'},
            {'id': '2', 'name': 'Steve Hilton', 'office_context': 'Los Angeles City Council District 1', 'source_key': 'source1', 'label': 'Ally'}]}
        draft = updates.draft(BASE, capture, 'draft-fixture', '2026-10-09', ['Alameda'])
        self.assertTrue(all(d['action'] == 'hold' for d in draft['decisions']))
        self.assertEqual(len(draft['decisions'][0]['suggested_matches']), 1)
        self.assertEqual(draft['decisions'][1]['suggested_matches'], [])
        result, report = updates.prepare(BASE, draft, [])
        self.assertEqual(result, BASE)
        self.assertEqual(report['counts'], {'held': 2})

    def test_addition_is_idempotent_and_preserves_other_fields(self):
        review = review_for()
        result, report = updates.prepare(BASE, review, [])
        self.assertEqual(report['counts'], {'added': 1})
        again, report = updates.prepare(result, review, [])
        self.assertEqual(again, result)
        self.assertEqual(report['counts'], {'unchanged': 1})
        self.assertEqual(result['election'], BASE['election'])
        self.assertEqual(result['finance'], BASE['finance'])
        key = review['decisions'][0]
        person = next(c for p in result['positions'] if p['id'] == key['position_id'] for c in p['candidates'] if c['name'] == key['candidate'])
        person['endorsements'].remove(key['after'])
        self.assertEqual(result, BASE)

    def test_reviewed_source_replacement_supersedes_dated_guard(self):
        review = review_for(publisher='Vote for Peace')
        change = review['decisions'][0]
        original = next(r for p in BASE['positions'] if p['id'] == change['position_id'] for c in p['candidates'] if c['name'] == change['candidate'] for r in c['endorsements'] if r['endorser'] == 'Vote for Peace')
        change['before'] = deepcopy(original)
        change['after'] = {**original, 'relation': 'supported', 'rating': 'Ally'}
        review['sources']['source1']['url'] = original['url']
        result, report = updates.prepare(BASE, review, [])
        self.assertEqual(report['counts'], {'replaced': 1})
        self.assertFalse(history.check_registered_reviews(result, [review]))
        deletion = deepcopy(review)
        deletion['id'] = 'test-explicit-removal'
        deletion['decisions'][0].update(before=deepcopy(change['after']), after=None)
        removed, report = updates.prepare(result, deletion, [review])
        self.assertEqual(report['counts'], {'removed': 1})
        self.assertFalse(history.check_registered_reviews(removed, [review, deletion]))
        again, report = updates.prepare(removed, deletion, [review])
        self.assertEqual(again, removed)
        self.assertEqual(report['counts'], {'unchanged': 1})

    def test_stale_identity_scope_date_and_publisher_fail_without_mutation(self):
        for problem in ['identity', 'scope', 'publisher', 'old_check', 'stale_before', 'missing_basis']:
            review = review_for()
            change = review['decisions'][0]
            if problem == 'identity':
                change['identity']['office'] = 'Mayor'
            elif problem == 'scope':
                review['counties'] = ['Marin']
            elif problem == 'publisher':
                review['sources']['source1']['publisher'] = 'Different Organization'
            elif problem == 'old_check':
                review['sources']['source1']['checked_on'] = '2026-10-08'
            elif problem == 'stale_before':
                change['before'] = {**change['after'], 'checked_on': '2026-10-08'}
            else:
                change.pop('evidence')
            before = deepcopy(BASE)
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                updates.prepare(BASE, review, [])
            self.assertEqual(BASE, before)

    def test_invalid_guide_observation_date_and_quarantine_stay_blocked(self):
        review = review_for()
        change = review['decisions'][0]
        change['field'] = 'gaza_evidence'
        change['evidence']['issue_basis'] = 'Fixture attributes an arms embargo position to the guide.'
        change['after'] = {'id': 'GE-99999', 'url': review['sources']['source1']['url'], 'date': '2026-01-01', 'checked_on': '2026-10-09',
                           'date_method': 'source_observed', 'source_kind': 'voter_guide', 'date_note': 'Observed guide; original date unknown.',
                           'summary': 'The example guide reports the candidate supports an arms embargo.', 'dimension': 'military_aid'}
        with self.assertRaisesRegex(ValueError, 'guide observation'):
            updates.prepare(BASE, review, [])
        review = review_for()
        review['sources']['source1']['url'] = 'https://www.sfchronicle.com/projects/2026/california-voter-guide/'
        review['decisions'][0]['after']['url'] = review['sources']['source1']['url']
        # A real known-bad URL, selected from the publication quarantine.
        from check_published_endorsements import QUARANTINE
        blocked = json.loads(QUARANTINE.read_text())['blocked_urls'][0]['url']
        review['sources']['source1']['url'] = blocked
        review['decisions'][0]['after']['url'] = blocked
        with self.assertRaises(ValueError):
            updates.prepare(BASE, review, [])

    def test_apply_registers_immutable_history_and_rerun_is_noop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'research/reviews'; folder.mkdir(parents=True)
            registry = root / 'research/publication-reviews.json'; registry.write_text('{"version":1,"reviews":[]}')
            dataset = root / 'data.json'; dataset.write_text(json.dumps(BASE))
            manifest = folder / 'fixture.json'; manifest.write_text(json.dumps(review_for()))
            with patch.object(updates, 'ROOT', root), patch.object(updates, 'REGISTRY', registry), patch.object(history, 'ROOT', root), patch.object(history, 'REGISTRY', registry):
                self.assertEqual(updates.apply_file(dataset, manifest)['counts'], {'added': 1})
                written = dataset.read_bytes(), registry.read_bytes()
                self.assertTrue(updates.apply_file(dataset, manifest)['already_applied'])
                self.assertEqual((dataset.read_bytes(), registry.read_bytes()), written)
                from research_test_fixtures import before_registered_updates
                self.assertEqual(before_registered_updates(json.loads(dataset.read_text())), BASE)
                manifest.write_text(manifest.read_text() + ' ')
                with self.assertRaisesRegex(ValueError, 'changed'):
                    updates.apply_file(dataset, manifest)
                self.assertEqual((dataset.read_bytes(), registry.read_bytes()), written)


if __name__ == '__main__':
    unittest.main()
