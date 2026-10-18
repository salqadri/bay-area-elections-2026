"""Capture a complete review packet; no automatic endorsement or image selection.

Examples:
  python3 scripts/capture_endorsement_images.py --url https://example.org/endorsements --checked-on 2026-10-17 --output .research/images.json
  ... --html .research/rendered.html   # actual browser HTML, never a paraphrase
Review every inventory item (include/exclude/hold with reason). Selected images
can be copied with archive_image(); publication uses reviewed_updates.py with
field endorsement_images and image_record(), not the old filename proposal gate.
"""
import argparse
from datetime import date
import hashlib
import json
import re
from pathlib import Path

from endorsement_images import images_from_html, image_record, VERSION
from endorsement_extract import page_from_html
from research_endorsements import Fetcher, atomic_json

ROOT = Path(__file__).resolve().parent.parent
MIMES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp',
         'image/gif': 'gif', 'image/avif': 'avif', 'image/svg+xml': 'svg'}


def capture(raw, url, checked_on):
    date.fromisoformat(checked_on)
    if date.fromisoformat(checked_on) > date.today():
        raise ValueError('Future observation date')
    html = raw.decode('utf-8-sig', errors='replace')
    page = page_from_html(html, url)
    unresolved = []
    images = images_from_html(html, url, unresolved)
    return {'version': VERSION, 'source_url': url, 'checked_on': checked_on,
            'source_sha256': hashlib.sha256(raw).hexdigest(), 'text': page['text'],
            'images': images, 'unresolved_images': unresolved, 'limitation': 'Static HTML inventory; inspect browser output for JS/CSS-only images. No absence or endorsement inference.'}


def archive_image(record, fetcher=None, root=ROOT):
    """Preserve actual image bytes under a content hash; fail explicitly on errors."""
    raw, mime, final = (fetcher or Fetcher()).request(record['image_url'])
    if mime not in MIMES:
        raise ValueError('Expected image response; received ' + mime)
    if mime == 'image/svg+xml':
        svg = raw.decode('utf-8-sig')
        if re.search(r'<!(?:DOCTYPE|ENTITY)|<\s*(?:script|foreignObject)\b|\bon[a-z]+\s*=|(?:href|src)\s*=\s*[\"\'](?!#)|@import|url\(\s*[\"\']?(?:https?:|//|data:)', svg, re.I):
            raise ValueError('Active or externally referenced SVG cannot be archived on the site origin')
    sha = hashlib.sha256(raw).hexdigest()
    path = 'assets/endorsement-evidence/' + sha + '.' + MIMES[mime]
    target = root / path; target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(raw)
    return {**record, 'asset_path': path, 'image_sha256': sha}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', required=True)
    p.add_argument('--checked-on', required=True)
    p.add_argument('--html', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    if args.output.exists():
        p.error('Preserve existing captures; choose a new output')
    if args.html:
        raw, url = args.html.read_bytes(), args.url
    else:
        raw, mime, url = Fetcher().request(args.url)
        if mime not in {'text/html', 'application/xhtml+xml'}:
            p.error('HTML required; use a separately reviewed PDF/browser workflow')
    packet = capture(raw, url, args.checked_on)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output, packet)
    print(json.dumps({'source_url': url, 'images': len(packet['images']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
