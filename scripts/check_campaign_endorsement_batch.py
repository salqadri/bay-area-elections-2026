"""Verify portable audit packets offline; no network, credentials or model calls."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from campaign_endorsements import dump, is_distinction
from endorsement_extract import norm, uid
from endorsement_images import SUPPORTED_VERSIONS


def verify(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    counts = Counter(); files = set()
    for file in manifest['files']:
        path = (root / file['path']).resolve()
        if not path.is_relative_to(root.resolve()) or path in files:
            raise ValueError('Unsafe or repeated packet path')
        files.add(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != file['sha256']:
            raise ValueError('Changed packet: ' + file['path'])
        packet = json.loads(path.read_text()); pages = packet['pages']
        snapshot_sha = hashlib.sha256(dump({p['url']: p['page'] for p in pages}).encode()).hexdigest()
        site_sha = packet['capture_fingerprint']
        if snapshot_sha != packet['snapshot_sha256'] or any(p['sha'] != site_sha for p in pages):
            raise ValueError('Source fingerprint mismatch')
        if not any(p.get('format_warning') for p in pages) and pages and site_sha != snapshot_sha:
            raise ValueError('Original capture differs from complete exported snapshot')
        by_url = {p['url']: p for p in pages}
        normalized_text = {p['url']: ' ' + norm(p['page']['text']) + ' ' for p in pages}
        counts['media_pages'] += sum(bool(p.get('format_warning')) for p in pages)
        for proposal in packet['proposals']:
            status = proposal['status']; counts[status] += 1
            if status != 'machine_accepted_pending_publication_review':
                continue
            record = proposal['record']; page = by_url[record['url']]
            if page.get('format_warning'):
                raise ValueError('Media resource cannot support a named endorsement')
            binding = proposal['source_binding']; text = normalized_text[record['url']]
            if (binding['page_url'] != record['url'] or binding['source_sha'] != site_sha or
                page['page'].get('image_parser_version') not in SUPPORTED_VERSIONS or
                proposal['id'] != uid('P2-', proposal['candidacy_id'], site_sha, dump(record)) or
                not norm(record['endorser']) or not norm(record['quote']) or
                ' ' + norm(record['endorser']) + ' ' not in text or
                ' ' + norm(record['quote']) + ' ' not in text or
                is_distinction(record['endorser'] + ' ' + record['quote'])):
                raise ValueError('Accepted proposal lacks exact source-local name/quote binding')
            review = proposal['jev']
            if (proposal['decision']['action'] != 'accept' or review['choice'] != 'endorsement' or
                review['p_endorse'] < .75 or review['policy_version'] != 'source-entry-v2' or
                review['response']['answer']['choice'] != 'endorsement' or
                review['response']['answer']['probabilities'].get('endorsement') != review['p_endorse']):
                raise ValueError('Missing classifier acceptance provenance')
            counts['accepted_' + proposal['existing_name_hint']] += 1
        counts['sites'] += 1; counts['captured_sites'] += bool(pages)
        counts['extracted_sites'] += bool(packet['extraction']); counts['pages'] += len(pages)
        counts['image_occurrences'] += sum(len(p['page'].get('images', [])) for p in pages)
        counts['extraction_holds'] += len(packet['extraction_holds'])
    if dict(counts) != manifest['counts']:
        raise ValueError('Manifest totals disagree with packets')
    return dict(counts)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory', type=Path)
    args = ap.parse_args()
    print(json.dumps({'passed': True, 'counts': verify(args.directory)}, indent=2))
