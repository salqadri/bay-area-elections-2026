"""Offline regressions for the Firebase publication boundary and release hashes."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_firebase_hosting as hosting


class HostingChecks(unittest.TestCase):
    def test_public_bundle_is_allowlisted_and_matches_current_readers(self):
        files = hosting.artifacts()
        self.assertEqual(set(files), {*hosting.PUBLIC_FILES, '404.html', 'hosting-release.json'})
        manifest = json.loads(files['hosting-release.json'])
        data = json.loads(files['2026-11-03_Bay_Area_Elections.json'])
        self.assertEqual(manifest['publication_version'], data['election']['publication_version'])
        self.assertEqual(manifest['score_publication_id'], data['pro_palestine_grading']['publication_id'])
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256(files[name]).hexdigest(), digest)

    def test_bundle_check_rejects_unexpected_or_stale_files(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(hosting, 'OUTPUT', Path(temp)/'public'), \
             patch.object(hosting, 'artifacts', return_value={'index.html': b'current'}):
            hosting.stage()
            hosting.stage(check=True)
            private = hosting.OUTPUT/'private.env'
            private.write_text('fixture credential')
            with self.assertRaisesRegex(ValueError, 'unexpected'):
                hosting.stage(check=True)
            hosting.stage()
            self.assertFalse(private.exists())
            (hosting.OUTPUT/'index.html').write_bytes(b'old')
            with self.assertRaisesRegex(ValueError, 'stale'):
                hosting.stage(check=True)

    def test_deploy_targets_only_the_named_hosting_site(self):
        config = json.loads((hosting.ROOT/'firebase.json').read_text())
        targets = json.loads((hosting.ROOT/'.firebaserc').read_text())
        self.assertEqual(config['hosting']['public'], '.firebase-public')
        self.assertEqual(config['hosting']['target'], 'research-tool')
        self.assertEqual(targets['targets']['tall-bay-area-voter-guide']['hosting']['research-tool'],
                         ['tall-bay-area-research-tool'])
        self.assertNotIn('rewrites', config['hosting'])


if __name__ == '__main__':
    unittest.main()
