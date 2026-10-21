"""Offline finance regressions: no API credentials, network requests or Git pushes."""
import base64
import json
import sqlite3
from types import SimpleNamespace
import urllib.error
import urllib.parse
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import fec_independent_expenditures as ie
import refresh_fec_money as refresh
from schema_validation import SCHEMA, check


class FinanceChecks(unittest.TestCase):
    def row(self, **changes):
        return {"candidate_id": "H6CA00001", "cycle": 2026,
                "committee_id": "C00000001", "committee_name": "Fixture PAC",
                "support_oppose_indicator": "S", "total": 125.25, "count": 2, **changes}

    def cache(self, db, rows, cid="H6CA00001", cycle=2026, method=ie.METHOD_VERSION,
              fetched="2026-10-20T08:00:00+00:00"):
        db.execute("INSERT OR REPLACE INTO aggregate_snapshots VALUES(?,?,?,?,?)",
                   (cid, cycle, method, fetched, json.dumps(rows)))
        db.commit()

    def page(self, rows, count=None, page=1):
        return {"results": rows, "pagination": {"count": len(rows) if count is None else count,
                "is_count_exact": True, "page": page}}

    def test_one_spender_can_support_and_oppose_with_separate_counts(self):
        db = ie.open_db(Path(":memory:"))
        self.cache(db, [self.row(), self.row(support_oppose_indicator="O", total=40, count=1)])
        result = ie.aggregate(db, 2026)['H6CA00001']
        self.assertEqual((result['for_total'], result['against_total']), (125.25, 40))
        rows = {item['direction']: item for item in result['items']}
        self.assertEqual(len(result['registry']), 1)
        self.assertEqual(rows['for']['items'], 2)
        self.assertEqual(rows['against']['items'], 1)
        self.assertNotIn('first_expenditure_date', rows['for'])
        self.assertNotIn('committee_type', result['registry']['C00000001'])
        db.close()

    def test_exact_udp_regression_matches_official_aggregate(self):
        # Source-bound captured evidence, not a synthetic halving of the bad total.
        packet = json.loads((ie.ROOT / 'research/finance/2026-10-20/udp-reconciliation.json').read_text())
        from decimal import Decimal
        raw = packet['rows']
        regular = sum((Decimal(str(r['expenditure_amount'])) for r in raw if not r['is_notice']), Decimal(0))
        notices = sum((Decimal(str(r['expenditure_amount'])) for r in raw if r['is_notice']), Decimal(0))
        self.assertEqual(regular, Decimal('20140908.74'))
        self.assertEqual(notices, Decimal('20423765.29'))
        self.assertEqual(regular + notices, Decimal('40564674.03'))
        regular_by_transaction = {r['transaction_id']: r for r in raw if not r['is_notice']}
        primary_notices = [r for r in raw if r['is_notice'] and r['election_type'] == 'P2026']
        self.assertEqual(len(primary_notices), 24)
        self.assertTrue(all(r['expenditure_amount'] == regular_by_transaction[r['transaction_id']]['expenditure_amount']
                            for r in primary_notices))
        db = ie.open_db(Path(':memory:'))
        self.cache(db, [packet['official_aggregate']], cid='S6MI00418')
        result = ie.aggregate(db, 2026)['S6MI00418']
        self.assertEqual(result['against_total'], 20140908.74)
        self.assertEqual(result['items'][0]['items'], 25)
        db.close()

    def test_aggregate_pagination_and_explicit_two_year_scope(self):
        rows = [self.row(committee_id=f'C{i:08d}') for i in range(101)]
        with patch.object(ie, 'fetch_page', side_effect=[self.page(rows[:100], 101), self.page(rows[100:], 101, 2)]) as fetch, patch.object(ie.time, 'sleep'):
            self.assertEqual(ie.fetch_aggregates('fixture', 'H6CA00001', 2026), rows)
        calls = [call.args[1] for call in fetch.call_args_list]
        self.assertEqual([c['page'] for c in calls], [1, 2])
        self.assertTrue(all(c['election_full'] == 'false' and c['cycle'] == 2026 for c in calls))
        self.assertTrue(ie.API.endswith('/schedule_e/by_candidate/'))

    def test_incomplete_repeated_and_changing_pages_are_rejected(self):
        cases = [
            [{}, self.page([])],
            [self.page([self.row()], 2), self.page([], 2, 2)],
            [self.page([self.row()], 2), self.page([self.row()], 2, 2)],
            [self.page([self.row()], 2), self.page([], 1, 2)],
            [{'results': [], 'pagination': {'count': 0, 'page': 1}}],
        ]
        for pages in cases:
            with self.subTest(pages=pages), patch.object(ie, 'fetch_page', side_effect=pages), patch.object(ie.time, 'sleep'):
                with self.assertRaises(ValueError):
                    ie.fetch_aggregates('fixture', 'H6CA00001', 2026)

    def test_invalid_totals_identity_direction_or_counts_fail_closed(self):
        for changes in [{'total': None}, {'total': -1}, {'total': float('nan')}, {'total': 1.234},
                        {'count': 0}, {'count': True}, {'candidate_id': 'S6MI00418'},
                        {'cycle': 2024}, {'committee_id': None}, {'committee_name': None},
                        {'support_oppose_indicator': 'X'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                ie.normalize_rows([self.row(**changes)], 'H6CA00001', 2026)

    def test_other_direction_rows_pass_validation_but_never_reach_snapshots(self):
        # FEC's by_candidate aggregate emits unclassifiable 'Other' rows (individual
        # filers with no support/oppose indicator). They are valid source data — the
        # validator must not reject them — but this dataset models only S/O, so
        # fetch_aggregates excludes them rather than attributing them to a direction.
        other = self.row(committee_id="C00000002", committee_name="Individual filer",
                         support_oppose_indicator="Other")
        rows = [self.row(), other]
        with patch.object(ie, "fetch_page", return_value=self.page(rows)):
            kept = ie.fetch_aggregates("fixture", "H6CA00001", 2026)
        self.assertEqual([r["support_oppose_indicator"] for r in kept], ["S"])

    def test_genuine_empty_response_is_a_checked_zero(self):
        with patch.object(ie, 'fetch_page', return_value=self.page([])):
            rows = ie.fetch_aggregates('fixture', 'H6CA00001', 2026)
        db = ie.open_db(Path(':memory:'))
        self.cache(db, rows)
        self.assertEqual(ie.aggregate(db, 2026)['H6CA00001']['against_total'], 0)
        db.close()

    def test_legacy_wrong_cycle_and_wrong_method_caches_never_qualify(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ie.sqlite3'
            db = sqlite3.connect(path)
            db.execute('CREATE TABLE candidates(candidate_id TEXT, fetched_at TEXT)')
            db.execute("INSERT INTO candidates VALUES('H6CA00001','2099-01-01')")
            db.commit(); db.close()
            db = ie.open_db(path)
            self.cache(db, [], cycle=2024)
            self.cache(db, [], method='legacy')
            self.assertEqual(ie.aggregate(db, 2026), {})
            self.assertEqual(db.execute('SELECT count(*) FROM candidates').fetchone()[0], 1)
            db.close()

    def test_failure_preserves_previous_snapshot(self):
        db = ie.open_db(Path(':memory:'))
        self.cache(db, [self.row()])
        args = SimpleNamespace(scope=None, county=None, cycle=2026, force=True, refresh_days=7)
        with patch.object(ie, 'fec_key', return_value='fixture'), patch.object(ie, 'eligible', return_value=[('H6CA00001', 'Fixture', 'CA2026-999')]), patch.object(ie, 'fetch_aggregates', side_effect=ValueError('incomplete')):
            with self.assertRaises(ValueError):
                ie.cmd_run(args, db)
        self.assertEqual(ie.aggregate(db, 2026)['H6CA00001']['for_total'], 125.25)
        db.close()

    def test_attach_requires_complete_scope_and_does_not_relabel_stale_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / 'data.json'
            data = json.loads(ie.DATASET.read_text())
            dataset.write_text(json.dumps(data))
            before = dataset.read_bytes()
            dbpath = Path(directory) / 'ie.sqlite3'
            db = ie.open_db(dbpath)
            args = SimpleNamespace(db=str(dbpath), cycle=2026, checked_on='2026-10-20', source_id='S1086', publication_version=None)
            with patch.object(ie, 'DATASET', dataset):
                with self.assertRaises(SystemExit):
                    ie.cmd_attach(args)
                self.assertEqual(dataset.read_bytes(), before)
                for cid, _, _ in ie.eligible(data, None):
                    self.cache(db, [], cid=cid, fetched='2026-10-19T08:00:00+00:00')
                with self.assertRaises(SystemExit):
                    ie.cmd_attach(args)
                self.assertEqual(dataset.read_bytes(), before)
            db.close()

    def test_http_errors_redact_credentials(self):
        secret = 'fixture-secret'
        error = urllib.error.HTTPError('https://example.org/?api_key=' + secret, 403, 'Forbidden', {}, None)
        with patch.object(ie.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaises(RuntimeError) as failure:
                ie.fetch_page(secret, {})
        self.assertNotIn(secret, str(failure.exception))
        self.assertIn('403', str(failure.exception))

    def test_snapshot_dates_share_the_publishers_pacific_day(self):
        self.assertEqual(ie.checked_date('2026-10-20T06:59:00+00:00'), '2026-10-19')
        self.assertEqual(ie.checked_date('2026-10-20T07:00:00+00:00'), '2026-10-20')
        with patch.object(refresh, 'now_utc', return_value='2026-10-20T06:59:00+00:00'):
            self.assertEqual(refresh.next_version('2026-10-19.3'), '2026-10-19.4')
        with self.assertRaises(ValueError):
            ie.checked_date('2026-10-20T07:00:00')

    def test_browse_link_excludes_notices(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(ie.candidate_browse_url('S6MI00418', 2026)).query)
        self.assertEqual(params['is_notice'], ['false'])
        self.assertEqual(params['most_recent'], ['true'])

    def summary(self, **changes):
        return {'receipts': 50, 'coverage_start_date': '2025-01-01',
                'coverage_end_date': '2026-09-30', **changes}

    def unknown(self):
        return {'id': 'H6CA00001', 'receipts': None, 'source_id': 'S001', 'note_id': 'N001'}

    def test_unknown_becomes_fully_dated_reported_amount(self):
        fec = self.unknown()
        status, _ = refresh.update_receipts(fec, self.summary(), '2026-10-14', ['C00000001'])
        self.assertEqual(status, 'updated')
        self.assertEqual(fec['receipts'], 50)
        self.assertEqual((fec['from'], fec['through']), ('2025-01-01', '2026-09-30'))
        self.assertNotIn('note_id', fec)
        self.assertFalse(check(fec, SCHEMA['$defs']['fec']))

    def test_reported_zero_is_not_unavailable(self):
        fec = self.unknown()
        status, _ = refresh.update_receipts(fec, self.summary(receipts=0), '2026-10-14', ['C00000001'])
        self.assertEqual((status, fec['receipts']), ('updated', 0))
        self.assertIn('from', fec)

    def test_unavailable_or_incomplete_summary_preserves_unknown(self):
        for totals in [None, {}, self.summary(coverage_start_date=None), self.summary(coverage_end_date='2026-11-01'), self.summary(coverage_start_date='2026-02-30')]:
            fec = self.unknown(); before = deepcopy(fec)
            self.assertEqual(refresh.update_receipts(fec, totals, '2026-10-14', ['C00000001'])[0], 'skipped')
            self.assertEqual(fec, before)

    def test_reported_amount_without_authorized_committee_stays_held(self):
        fec = self.unknown(); before = deepcopy(fec)
        self.assertEqual(refresh.update_receipts(fec, self.summary(), '2026-10-14')[0], 'skipped')
        self.assertEqual(fec, before)

    def test_multi_cycle_exception_and_newer_snapshot_are_preserved(self):
        fec = {**self.unknown(), 'receipts': 10, 'from': '2023-01-01', 'through': '2026-09-30', 'committee_ids': ['C00000001']}
        before = deepcopy(fec)
        self.assertEqual(refresh.update_receipts(fec, self.summary(), '2026-10-14')[0], 'skipped')
        self.assertEqual(fec, before)
        self.assertEqual(refresh.update_receipts(fec, self.summary(coverage_start_date='2023-01-01', coverage_end_date='2026-06-30'), '2026-10-14')[0], 'skipped')
        self.assertEqual(fec, before)

    def test_environment_key_precedes_legacy_file(self):
        with patch.dict(os.environ, {'FEC_API_KEY': 'fixture-only'}), patch.object(Path, 'read_text', side_effect=AssertionError('Should not read a file')):
            self.assertEqual(refresh.read_secret(('FEC_API_KEY',), '/missing', required=True), 'fixture-only')

    def test_push_has_separate_refspec_and_no_secret_arguments(self):
        token = 'fixture-secret-never-real'
        encoded = base64.b64encode(('x-access-token:' + token).encode()).decode()
        with patch.object(refresh, 'sh') as command, patch.dict(os.environ, {}, clear=True):
            refresh.push_main(token)
        self.assertEqual(command.call_args.args, ('git', 'push', refresh.REMOTE, 'HEAD:main'))
        self.assertNotIn(token, ' '.join(command.call_args.args))
        self.assertEqual(command.call_args.kwargs['env']['GIT_CONFIG_VALUE_0'], 'AUTHORIZATION: basic ' + encoded)

    def test_configured_git_credentials_need_no_token_file(self):
        with patch.object(refresh, 'sh') as command:
            refresh.push_main()
        self.assertIsNone(command.call_args.kwargs['env'])

    def test_failure_output_redacts_raw_encoded_and_url_credentials(self):
        token = 'fixture-secret-never-real'; encoded = 'fixture-encoded-value'
        result = subprocess.CompletedProcess([], 1, token, 'https://user:password@example.com/ ' + encoded)
        with patch.object(refresh.subprocess, 'run', return_value=result):
            with self.assertRaises(SystemExit) as failure:
                refresh.sh('git', 'push', refresh.REMOTE, 'HEAD:main', secrets=(token, encoded))
        for secret in (token, encoded, 'password'):
            self.assertNotIn(secret, str(failure.exception))

    def test_failure_redacts_before_truncating_output(self):
        token = 'fixture-long-secret-' * 120
        result = subprocess.CompletedProcess([], 1, '', token)
        with patch.object(refresh.subprocess, 'run', return_value=result):
            with self.assertRaises(SystemExit) as failure:
                refresh.sh('git', 'push', secrets=(token,))
        self.assertNotIn('fixture-long-secret', str(failure.exception))


if __name__ == '__main__':
    unittest.main()
