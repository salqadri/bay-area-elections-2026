"""Firebase custom-404 verification without provider calls."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('tall_deploy', ROOT / 'voter-guide/deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeploymentChecks(unittest.TestCase):
    origin = 'https://example.test'
    missing_page = b'<!doctype html><title>Page not found</title>'

    def manifest(self):
        return {'files': {'404.html': hashlib.sha256(self.missing_page).hexdigest()}}

    def response(self, status=404, body=None):
        manifest = self.manifest()
        def open_url(request, timeout):
            if request.full_url.endswith('/release.json'):
                return io.BytesIO(json.dumps(manifest).encode())
            payload = self.missing_page if body is None else body
            if status == 200:
                return io.BytesIO(payload)
            raise urllib.error.HTTPError(request.full_url, status, 'Test status', None, io.BytesIO(payload))
        return open_url

    def test_custom_404_status_and_matching_body_are_verified(self):
        for status in (200, 404):
            with self.subTest(status=status), patch.object(deploy.urllib.request, 'urlopen', side_effect=self.response(status)):
                deploy.verify_release(self.origin, self.manifest())

    def test_custom_404_with_wrong_body_is_rejected(self):
        with patch.object(deploy.urllib.request, 'urlopen', side_effect=self.response(body=b'Default host error page')):
            with self.assertRaisesRegex(SystemExit, 'Deployed file differs.*404.html'):
                deploy.verify_release(self.origin, self.manifest())

    def test_unexpected_http_errors_are_not_accepted(self):
        for filename, status in [('index.html', 404), ('release.json', 404), ('404.html', 403), ('404.html', 500)]:
            error = urllib.error.HTTPError(self.origin+'/'+filename, status, 'Test status', None, io.BytesIO(b'error'))
            with self.subTest(filename=filename, status=status), patch.object(deploy.urllib.request, 'urlopen', side_effect=error):
                with self.assertRaises(urllib.error.HTTPError):
                    deploy.published_bytes(self.origin, filename)


if __name__ == '__main__':
    unittest.main()
