#!/usr/bin/env python3
"""Create/reuse the dedicated Hosting site, deploy this guide, verify every byte.

Run on the Mac already signed into Firebase. No credential enters source code.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
PROJECT = 'tall-bay-area-voter-guide'
SITE = 'tall-voter-guide'
CLI = ['npx', '--yes', 'firebase-tools@15.34.2']


def firebase(*args, capture=False):
    result = subprocess.run([*CLI, *args, '--project', PROJECT], cwd=ROOT,
                            text=True, capture_output=capture)
    if result.returncode:
        if capture:
            print(result.stderr, file=sys.stderr)
        raise SystemExit('Firebase command failed. Run `npx --yes firebase-tools@15.34.2 login` on this computer if you are not signed in.')
    return json.loads(result.stdout) if capture else None


def main():
    if not os.environ.get('TALL_GOOGLE_MAPS_API_KEY', '').strip():
        raise SystemExit('Set TALL_GOOGLE_MAPS_API_KEY to your website-restricted Google Maps key before publishing. Local manual-entry previews do not need a key.')
    subprocess.run([sys.executable, 'voter-guide/build.py'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'voter-guide/tests', '-p', 'test_*.py'], cwd=ROOT, check=True)
    listing = firebase('hosting:sites:list', '--json', capture=True)
    if listing.get('status') != 'success':
        raise SystemExit('Could not inspect Hosting sites; nothing was deployed.')
    sites = listing.get('result', {}).get('sites', [])
    if not any(s.get('name', '').split('/')[-1] == SITE for s in sites):
        firebase('hosting:sites:create', SITE)
    firebase('deploy', '--config', 'firebase.voter-guide.json', '--only', 'hosting:voter-guide')
    local = ROOT / 'voter-guide/dist'
    manifest = json.loads((local / 'release.json').read_text())
    for origin in (f'https://{SITE}.web.app', f'https://{SITE}.firebaseapp.com'):
        for name, digest in manifest['files'].items():
            request = urllib.request.Request(origin + '/' + name, headers={'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(request, timeout=30) as response:
                actual = hashlib.sha256(response.read()).hexdigest()
            if actual != digest:
                raise SystemExit('Deployed file differs from the tested bundle: ' + origin + '/' + name)
        with urllib.request.urlopen(origin + '/release.json', timeout=30) as response:
            if json.loads(response.read()) != manifest:
                raise SystemExit('Deployed release manifest differs: ' + origin)
        print('Verified exact release at ' + origin)
    print('The TALL Voter Guide is live at https://tall-voter-guide.web.app')


if __name__ == '__main__':
    main()
