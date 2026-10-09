"""Offline regressions for endorsement collection. Uses invented source fixtures."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import endorsement_extract as ex
import research_endorsements as research


META = {'publisher': 'Example County Civic Club', 'role': 'endorser', 'kind': 'organization', 'assertion': 'endorsements'}
URL = 'https://example.org/2026-endorsements'


def dataset():
    return {'election': {'date': '2026-11-03'}, 'positions': [
        {'id': 'P1', 'office': 'City Council Member', 'jurisdiction': 'City of Exampleville', 'district_or_seat': 'District 1', 'term': '4 years', 'counties': ['Example'], 'candidates': [{'name': 'Alex Rivera', 'campaign_url': 'https://alex.example.org/'}, {'name': 'Dana Lee'}]},
        {'id': 'P2', 'office': 'Governor', 'jurisdiction': 'California', 'district_or_seat': 'Statewide', 'counties': ['Example'], 'candidates': [{'name': 'Morgan Vale'}, {'name': 'Taylor Reed'}]},
    ]}


def page(body):
    return {'text': body, 'links': [], 'image_labels': []}


def example_body():
    return '# November 2026 General Election Endorsements\n## Exampleville City Council\n- District 1\n  - Alex Rivera\n  - Dana Lee\n'


class ExtractionChecks(unittest.TestCase):
    def setUp(self):
        self.people = ex.candidates_from_data(dataset())

    def test_one_source_matches_multiple_candidates(self):
        records, issues = ex.extract(page(example_body()), META, self.people, 2026)
        self.assertEqual(len(records), 2)
        self.assertFalse(issues)
        self.assertEqual({x['phase'] for x in records}, {'general'})

    def test_primary_stays_primary_and_old_cycle_not_accepted(self):
        text = example_body().replace('November 2026 General', 'June 2026 Primary') + '\n# November 2024 General Election Endorsements\nGovernor: Morgan Vale'
        records, issues = ex.extract(page(text), META, self.people, 2026)
        self.assertEqual(len(records), 2)
        self.assertTrue(all(x['phase'] == 'primary' for x in records))
        self.assertIn('different_election_cycle', issues[-1]['reasons'])

    def test_primary_carry_forward_prose_does_not_relabel_general_section(self):
        text = '# November 2026 General Election Endorsements\nMembers voted in September 2026. June primary endorsements remain in effect for November.\nGovernor: Morgan Vale\n## June 2026 Primary Endorsements Archive\nGovernor: Taylor Reed'
        records, _ = ex.extract(page(text), META, self.people, 2026)
        self.assertEqual([r['phase'] for r in records], ['general', 'primary'])

    def test_footer_year_does_not_prove_cycle(self):
        html = '<h1>Endorsements</h1><h2>Exampleville City Council District 1</h2><ul><li>Alex Rivera</li></ul><footer>Copyright 2026</footer>'
        records, issues = ex.extract(ex.page_from_html(html, URL), META, self.people, 2026)
        self.assertFalse(records)
        self.assertIn('cycle_unproven', issues[0]['reasons'])

    def test_questionnaire_respondents_and_forum_guests_not_endorsed(self):
        text = '# November 2026 General Election Endorsements\nGovernor: Morgan Vale\n## Candidate questionnaires\nGovernor: Taylor Reed\n## Candidate forum\nGovernor: Taylor Reed'
        records, _ = ex.extract(page(text), META, self.people, 2026)
        self.assertEqual(len(records), 1)
        self.assertIn('Morgan Vale', records[0]['evidence']['quote'])

    def test_normal_section_resumes_after_ballot_measures(self):
        text = '# November 2026 Endorsements\n## Ballot measures\nYES on A\n## Exampleville City Council\n- District 1\n  - Alex Rivera'
        records, _ = ex.extract(page(text), META, self.people, 2026)
        self.assertEqual(len(records), 1)

    def test_opposition_withdrawal_and_mixed_pages_are_reviewed(self):
        for body in ('Governor: Morgan Vale*\n*Vote AGAINST Taylor Reed.', 'Governor: Morgan Vale — endorsement withdrawn', 'Governor: no endorsement of Morgan Vale'):
            records, issues = ex.extract(page('# November 2026 Endorsements\n'+body), META, self.people, 2026)
            self.assertFalse(records)
            self.assertIn('negative_withdrawal_or_qualified_claim', issues[0]['reasons'])
        records, issues = ex.extract(page(example_body()), {**META, 'assertion': 'mixed'}, self.people, 2026)
        self.assertFalse(records)
        self.assertTrue(issues)

    def test_rank_dual_and_recommendation_preserved(self):
        text = '# November 2026 Endorsements\n## Exampleville City Council District 1\n- Dual: #1 Alex Rivera | #2 Dana Lee'
        records, _ = ex.extract(page(text), {**META, 'assertion': 'recommendations'}, self.people, 2026)
        self.assertEqual({r['rank'] for r in records}, {1, 2})
        self.assertTrue(all(r['shared'] and r['relation'] == 'recommended' for r in records))

    def test_shared_qualifier_on_parent_list_applies_to_children(self):
        text = example_body().replace('District 1', 'District 1 — dual endorsement')
        records, _ = ex.extract(page(text), META, self.people, 2026)
        self.assertEqual(len(records), 2)
        self.assertTrue(all(r['shared'] for r in records))

    def test_wrong_district_and_same_name_other_race_do_not_merge(self):
        records, issues = ex.extract(page(example_body().replace('District 1', 'District 11')), META, self.people, 2026)
        self.assertFalse(records); self.assertTrue(issues)
        d = dataset(); other = copy.deepcopy(d['positions'][0]); other['id'] = 'P3'; other['district_or_seat'] = 'District 2'; d['positions'].append(other)
        records, issues = ex.extract(page(example_body()), META, ex.candidates_from_data(d), 2026)
        self.assertFalse(records)
        self.assertTrue(any('same_name_multiple_races' in x['reasons'] for x in issues))

    def test_campaign_claims_do_not_turn_person_titles_into_city_endorsement(self):
        c = next(c for c in self.people.values() if c['name'] == 'Alex Rivera')
        text = '# 2026 Election Endorsements\n## Alex Rivera — Exampleville City Council District 1\n- Jamie Chen, Mayor of Elsewhere\nTitles for identification only.\n- Sign up'
        records, _ = ex.extract(page(text), {'role': 'campaign', 'candidate_ids': [c['id']]}, self.people, 2026)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['verification'], 'campaign_claim')
        self.assertEqual(records[0]['endorser'], 'Jamie Chen, Mayor of Elsewhere')
        self.assertTrue(records[0]['titles_for_identification_only'])

    def test_navigation_links_survive_but_navigation_text_and_script_do_not(self):
        parsed = ex.page_from_html('<nav><a href="/endorsements">Endorsements 2024</a></nav><script>Fake Mayor Endorsement</script><h1>Hello</h1>', URL)
        self.assertNotIn('2024', parsed['text'])
        self.assertNotIn('Fake', parsed['text'])
        self.assertEqual(parsed['links'][0]['url'], 'https://example.org/endorsements')

    def test_alias_is_reviewed_and_typo_never_silently_accepted(self):
        c = next(c for c in self.people.values() if c['name'] == 'Alex Rivera')
        c['name'] = 'Alex M. Rivera'
        records, issues = ex.extract(page(example_body()), META, {c['id']: c}, 2026)
        self.assertFalse(records)
        self.assertEqual(issues[0]['reasons'], ['name_variant_requires_confirmed_alias'])
        c['aliases'] = ['Alex Rivera']
        records, _ = ex.extract(page(example_body()), META, {c['id']: c}, 2026)
        self.assertEqual(len(records), 1)


class LedgerChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.db = research.connect(self.root/'ledger.sqlite3')
        self.data = self.root/'data.json'; self.data.write_text(json.dumps(dataset()))
        self.seeds = self.root/'seeds.json'; self.seeds.write_text(json.dumps({'sources': [{'url': URL, **META}]}))
        research.plan(self.db, self.data, self.seeds)

    def tearDown(self):
        self.db.close(); self.temp.cleanup()

    def test_replan_search_and_page_cache_are_idempotent(self):
        before = research.status(self.db)
        research.plan(self.db, self.data, self.seeds)
        self.assertEqual(research.status(self.db), before)
        research.save_page(self.db, URL, page(example_body()), research.now(), 'fixture')
        first = research.extract_all(self.db); second = research.extract_all(self.db)
        self.assertEqual(first['accepted_observations'], 2)
        self.assertEqual(second['pages_processed'], 0)
        self.assertEqual(research.status(self.db)['observations'], 2)

    def test_search_snippets_never_become_endorsements(self):
        q = self.db.execute('SELECT * FROM queries LIMIT 1').fetchone()
        research.save_search(self.db, q['q'], json.loads(q['ids']), {'organic': [{'link': 'https://news.example.org/endorses', 'snippet': 'Everyone endorses Alex Rivera in 2026'}]}, research.now())
        research.extract_all(self.db)
        self.assertEqual(research.status(self.db)['observations'], 0)

    def test_snapshot_changes_preserve_history_without_inferred_withdrawal(self):
        research.save_page(self.db, URL, page(example_body()), research.now(), 'fixture'); research.extract_all(self.db)
        research.save_page(self.db, URL, page('# November 2026 Endorsements\nUpdates coming soon.'), research.now(), 'fixture'); research.extract_all(self.db)
        result = research.export_ledger(self.db, self.root/'export.json')
        exported = json.loads((self.root/'export.json').read_text())
        self.assertEqual(result['candidates_with_evidence'], 0)
        self.assertEqual(len(exported['records']), 2)
        self.assertTrue(all(not r['current_source_version'] and r['relation'] == 'endorsed' for r in exported['records']))

    def test_review_packets_group_candidates_and_reject_stale_decisions(self):
        research.add_source(self.db, URL, META)
        research.save_page(self.db, URL, page(example_body().replace('District 1', 'District 9')), research.now(), 'fixture'); research.extract_all(self.db)
        summary = research.write_packets(self.db, self.root/'packets', 24000)
        self.assertEqual(summary['source_groups'], 1)
        self.assertEqual(summary['bounded_packets'], 1)
        r = self.db.execute('SELECT * FROM reviews LIMIT 1').fetchone()
        research.save_page(self.db, URL, page(example_body()), research.now(), 'fixture')
        p = self.root/'decisions.json'; p.write_text(json.dumps([{'review_id': r['id'], 'snapshot_id': r['snapshot'], 'action': 'reject', 'reviewed_by': 'test', 'reason': 'old'}]))
        with self.assertRaisesRegex(ValueError, 'Stale'):
            research.apply_decisions(self.db, p)

    def test_failed_fetch_has_one_lookup_packet(self):
        self.db.execute('UPDATE sources SET state=?,error=? WHERE url=?', ('error', 'HTTP 403', URL)); self.db.commit()
        summary = research.write_packets(self.db, self.root/'packets', 24000)
        self.assertEqual(summary['failed_lookups'], 1)
        packet = json.loads((self.root/'packets/packet-0001.json').read_text())
        self.assertEqual(packet['type'], 'lookup_needed')

    def test_import_adapter_does_not_guess_observation_dates(self):
        p = self.root/'lookup.jsonl'; p.write_text(json.dumps({'type': 'page', 'url': URL, 'observed_at': '2026-10-08', 'content': example_body()})+'\n')
        with self.assertRaises(ValueError):
            research.import_lookups(self.db, p)

    def test_all_candidates_export_with_unknowns_not_zero_endorsements(self):
        research.export_ledger(self.db, self.root/'export.json')
        data = json.loads((self.root/'export.json').read_text())
        self.assertEqual(len(data['candidates']), 4)
        self.assertTrue(all(c['research_status'] == 'incomplete' and c['exhaustive'] is False for c in data['candidates'].values()))

    def test_review_accept_reversal_and_atomic_batch_failure(self):
        self.db.execute('UPDATE sources SET meta=? WHERE url=?', (research.dump({**META, 'assertion': 'mixed'}), URL)); self.db.commit()
        text = '# November 2026 General Election Endorsements\nGovernor: Morgan Vale'
        research.save_page(self.db, URL, page(text), research.now(), 'fixture'); research.extract_all(self.db)
        r = self.db.execute('SELECT * FROM reviews LIMIT 1').fetchone()
        record = json.loads(r['data'])['proposal']; record['evidence']['context'] = text
        decision = {'review_id': r['id'], 'snapshot_id': r['snapshot'], 'reviewed_by': 'fixture reviewer', 'reason': 'Explicit source line checked', 'action': 'accept', 'record': record}
        path = self.root/'decisions.json'; path.write_text(json.dumps([decision]))
        research.apply_decisions(self.db, path)
        self.assertEqual(research.status(self.db)['observations'], 1)
        rejected = {k: v for k, v in decision.items() if k != 'record'}; rejected['action'] = 'reject'
        path.write_text(json.dumps([rejected, {**rejected, 'review_id': 'invalid'}]))
        with self.assertRaises(ValueError):
            research.apply_decisions(self.db, path)
        self.assertEqual(research.status(self.db)['observations'], 1)
        path.write_text(json.dumps([rejected])); research.apply_decisions(self.db, path)
        self.assertEqual(research.status(self.db)['observations'], 0)
        self.assertEqual(len(json.loads(self.db.execute('SELECT resolution FROM reviews WHERE id=?', (r['id'],)).fetchone()[0])), 2)

    def test_export_refuses_to_overwrite_input_dataset(self):
        before = self.data.read_bytes()
        with self.assertRaises(ValueError):
            research.export_ledger(self.db, self.data)
        self.assertEqual(self.data.read_bytes(), before)

    def test_blocked_network_checkpoints_error_and_stops(self):
        args = SimpleNamespace(serper_key_file=None, no_search=True, retry_failed=False, refresh_days=None,
                               workers=1, max_queries=0, max_pages=5)
        with patch.object(research.Fetcher, 'page', side_effect=research.Blocked('network denied')) as fetch:
            with self.assertRaises(research.Blocked):
                research.run_collection(self.db, args)
        self.assertEqual(fetch.call_count, 1)
        row = self.db.execute('SELECT state,error FROM sources WHERE url=?', (URL,)).fetchone()
        self.assertEqual(row['state'], 'error'); self.assertEqual(row['error'], 'network denied')

    def test_serper_contract_and_public_url_guard(self):
        with patch.object(research.Fetcher, 'request', return_value=(b'{"organic":[]}', 'application/json', research.SERPER_URL)) as request:
            research.Fetcher().search('Example 2026 endorsements', 'test-key')
            self.assertEqual(request.call_args.args[0], research.SERPER_URL)
            self.assertEqual(request.call_args.args[1]['q'], 'Example 2026 endorsements')
            self.assertEqual(request.call_args.args[2], 'test-key')
        with patch.object(research.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 80))]):
            with self.assertRaises(ValueError):
                research.public_url('https://example.org/private')

    def test_page_refresh_error_does_not_erase_existing_evidence(self):
        research.save_page(self.db, URL, page(example_body()), research.now(), 'fixture'); research.extract_all(self.db)
        self.db.execute('UPDATE sources SET state=?,error=? WHERE url=?', ('error', 'HTTP 503', URL)); self.db.commit()
        research.export_ledger(self.db, self.root/'export.json')
        records = json.loads((self.root/'export.json').read_text())['records']
        self.assertEqual(len(records), 2)
        self.assertTrue(all(r['source_refresh_failed'] for r in records))


if __name__ == '__main__':
    unittest.main()
