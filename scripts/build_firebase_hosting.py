"""Stage only public reader artifacts for Firebase Hosting; never upload the repo root.

No Firebase credentials or provider calls are needed to build or check this bundle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import build_site

ROOT = build_site.ROOT
OUTPUT = ROOT / '.firebase-public'
PUBLIC_FILES = ('index.html', 'ballot.html', '2026-11-03_Bay_Area_Elections.json', 'elections.schema.json')
NOT_FOUND = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page not found — Bay Area voter guide</title>
<main><h1>Page not found</h1><p><a href="/">Explore all races</a> or <a href="/ballot.html">find your expected ballot</a>.</p></main></html>
'''


def artifacts():
    for page in ('index', 'ballot'):
        if (ROOT / (page + '.html')).read_text() != build_site.render(page):
            raise ValueError('Stale reader: run python3 scripts/build_site.py before deploying')
    payload = {name: (ROOT / name).read_bytes() for name in PUBLIC_FILES}
    payload['404.html'] = NOT_FOUND.encode()
    data = json.loads(payload['2026-11-03_Bay_Area_Elections.json'])
    manifest = {'format': 'firebase-static-release/v1',
                'publication_version': data['election']['publication_version'],
                'score_publication_id': data['pro_palestine_grading']['publication_id'],
                'files': {name: hashlib.sha256(content).hexdigest() for name, content in payload.items()}}
    payload['hosting-release.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    return payload


def stage(check=False):
    expected = artifacts()
    if check:
        actual = {str(p.relative_to(OUTPUT)): p.read_bytes() for p in OUTPUT.rglob('*') if p.is_file()}
        if actual != expected:
            raise ValueError('Static bundle is missing, stale or contains unexpected files; rebuild it')
    else:
        if OUTPUT.is_symlink():
            raise ValueError('Refuse a symlinked output directory')
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        OUTPUT.mkdir()
        for name, content in expected.items():
            (OUTPUT / name).write_bytes(content)
    print(('Verified' if check else 'Built') + f' Firebase bundle: {len(expected)} public files, {sum(map(len, expected.values())):,} bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    stage(parser.parse_args().check)
