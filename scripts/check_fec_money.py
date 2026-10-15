"""Offline finance regressions: no API credentials, network requests or Git pushes."""
import base64
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
    def test_one_spender_can_support_and_oppose_with_separate_counts_and_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            db = ie.open_db(Path(directory) / 'ie.sqlite3')
            db.execute('INSERT INTO candidates(candidate_id,name,position_id) VALUES(?,?,?)',
                       ('H6CA00001', 'Fixture Candidate', 'CA2026-999'))
            for index, direction, amount, day in [(1, 'S', 100, '2026-05-01'), (2, 'O', 40, '2026-09-01'), (3, 'S', 25.25, '2026-06-01')]:
                db.execute('''INSERT INTO rows(sub_id,candidate_id,link_id,committee_id,committee_name,
                           support_oppose,election_type,amount,most_recent,expenditure_date)
                           VALUES(?,?,?,?,?,?,?,?,?,?)''',
                           (str(index), 'H6CA00001', index, 'C00000001', 'Fixture PAC', direction, 'G2026', amount, 1, day))
            result = ie.aggregate(db, 2026)['H6CA00001']
            self.assertEqual((result['for_total'], result['against_total']), (125.25, 40))
            rows = {item['direction']: item for item in result['items']}
            self.assertEqual(len(result['registry']), 1)
            self.assertEqual(rows['for']['items'], 2)
            self.assertEqual(rows['for']['last_expenditure_date'], '2026-06-01')
            self.assertEqual(rows['against']['items'], 1)
            self.assertEqual(rows['against']['first_expenditure_date'], '2026-09-01')
            db.close()

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
