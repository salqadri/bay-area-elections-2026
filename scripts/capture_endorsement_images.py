"""Capture a complete review packet; no automatic endorsement or image selection.

Examples:
  python3 scripts/capture_endorsement_images.py --url https://example.org/endorsements --checked-on 2026-10-17 --output .research/images.json
  ... --html .research/rendered.html   # actual browser HTML, never a paraphrase
Review every inventory item (include/exclude/hold with reason). Image bytes are never downloaded or copied; publication uses reviewed_updates.py with
field endorsement_images and image_record(), not the old filename proposal gate.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

from endorsement_images import images_from_html, VERSION
from endorsement_extract import page_from_html
from research_endorsements import Fetcher, atomic_json



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
