"""Offline regression checks for collector/publication reconciliation."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
COLLECTOR = ROOT / 'research/gaza-stance'
sys.path.insert(0, str(COLLECTOR))
import merge_gaza_evidence as merge


class LedgerChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())
        cls.ledger = merge.load_ledger()

    def test_reconciled_merge_preserves_every_published_record(self):
        actual, _ = merge.merged_data(self.data, self.ledger)
        self.assertEqual(actual, self.data)
        self.assertEqual(merge.sync_published(self.data)['changed_files'], 0)

    def test_missing_published_dossier_is_rejected(self):
        ledger = deepcopy(self.ledger)
        ledger.pop(merge.norm_name('Mike Hutchinson'))
        with self.assertRaisesRegex(ValueError, 'Missing collector evidence'):
            merge.merged_data(self.data, ledger)

    def test_stale_dossier_cannot_remove_manual_guide_observation(self):
        ledger = deepcopy(self.ledger)
        name = merge.norm_name('Jimmy Panetta')
        ledger[name] = [r for r in ledger[name] if r.get('date_method') != 'source_observed']
        with self.assertRaisesRegex(ValueError, 'replace or remove published evidence'):
            merge.merged_data(self.data, ledger)

    def test_quarantined_source_cannot_be_reintroduced(self):
        quarantine = json.loads((ROOT / 'docs/reviews/evidence-quarantine.json').read_text())
        held = next(r for r in quarantine['items'] if r['evidence']['id'] == 'GE-0197')
        ledger = deepcopy(self.ledger)
        ledger[merge.norm_name(held['candidate'])] = [{**held['evidence'], 'person': held['candidate']}]
        with self.assertRaisesRegex(ValueError, 'quarantined source'):
            merge.merged_data(self.data, ledger)

    def test_invalid_dates_fail_and_guide_provenance_survives(self):
        guide = next(r for rows in self.ledger.values() for r in rows if r.get('date_method') == 'source_observed')
        self.assertEqual(merge.clean_item(guide)['date_note'], guide['date_note'])
        with self.assertRaisesRegex(ValueError, 'Invalid ledger item'):
            merge.clean_item({**guide, 'date': '2026-02-30'})

    def test_synchronization_does_not_discard_unreviewed_drafts(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'draft.json').write_text(json.dumps([{
                'id': 'GE-99999', 'person': 'Unreviewed Fixture Candidate',
                'url': 'https://example.org/statement'}]))
            with patch.object(merge, 'LEDGER', directory):
                with self.assertRaisesRegex(ValueError, 'Unreviewed collector item would be lost'):
                    merge.sync_published(self.data)


if __name__ == '__main__':
    for filename in ('test_date_resolvers.py', 'test_validate_evidence.py'):
        subprocess.run([sys.executable, str(COLLECTOR / 'tests' / filename)], check=True)
    unittest.main()
