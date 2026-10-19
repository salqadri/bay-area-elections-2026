"""Export a portable, hash-checked campaign audit from the local SQLite ledger.

Read-only; does not accept credentials, make model calls, or publish claims.
Machine decisions remain proposals requiring a publication review. Images and
source text remain separate evidence; no names are inferred from image metadata.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import re
from urllib.parse import urlsplit
from functools import lru_cache

from campaign_endorsements import dump, is_distinction, site_key
from endorsement_extract import candidates_from_data, norm, uid
from endorsement_images import VERSION

name_norm = lru_cache(maxsize=16_384)(norm)


def classification(record, existing):
    """Deduplication hints only: never merge names or delete existing records."""
    same = [r for r in existing if name_norm(r['endorser']) == name_norm(record['endorser'])]
    if same:
        return 'existing_name'
    name = name_norm(record['endorser'])
    if any(min(len(name), len(name_norm(r['endorser']))) >= 8 and
           (' ' + name + ' ' in ' ' + name_norm(r['endorser']) + ' ' or
            ' ' + name_norm(r['endorser']) + ' ' in ' ' + name + ' ') for r in existing):
        return 'possible_name_variant'
    return 'unmatched_name'


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(db_path, dataset, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose a new empty output directory; preserve prior audit snapshots')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'sites').mkdir()
    data = json.loads(dataset.read_text())
    candidates = candidates_from_data(data)
    existing = {uid('C-', p['id'], norm(c['name'])): c.get('endorsements', [])
                for p in data['positions'] for c in p.get('candidates') or []}
    source = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
    db = sqlite3.connect(':memory:')
    try:
        source.backup(db)  # release the live ledger before a long export
    finally:
        source.close()
    db.row_factory = sqlite3.Row
    counts = Counter({'media_pages': 0}); files = []; failures = []
    try:
        for task in db.execute('SELECT * FROM tasks ORDER BY site_key'):
            key = task['site_key']; pages = []
            for r in db.execute('SELECT * FROM pages WHERE site_key=? ORDER BY url', (key,)):
                pages.append({**dict(r), 'page': json.loads(r['page_json'])})
                pages[-1].pop('page_json')
                if re.search(r'\.(png|jpe?g|gif|webp|avif|svg)$', urlsplit(r['url']).path, re.I):
                    pages[-1]['format_warning'] = 'Media URL from the earlier crawl; decoded bytes are not campaign-page text. Retained for audit, never publish named claims from this resource.'
                    counts['media_pages'] += 1
            if pages:
                actual = hashlib.sha256(dump({p['url']: p['page'] for p in pages}).encode()).hexdigest()
                if any(p['sha'] != actual for p in pages):
                    raise ValueError('Site fingerprint mismatch: ' + key)
            # The old crawler decoded a few PNGs as text. Do not copy image
            # bytes (even decoded as garbage) into Git. Keep URL + hashes only.
            for page in pages:
                if page.get('format_warning'):
                    raw_page = page['page']
                    page['omitted_media_page_sha256'] = hashlib.sha256(dump(raw_page).encode()).hexdigest()
                    page['page'] = {k: raw_page[k] for k in ('final_url', 'source_sha256', 'image_parser_version', 'capture', 'crawl_limits') if k in raw_page}
                    page['page'].update(text='', images=[], unresolved_images=[])
            by_url = {p['url']: p for p in pages}
            normalized = {p['url']: ' ' + norm(p['page']['text']) + ' ' for p in pages}
            proposals = []
            for row in db.execute('SELECT * FROM proposals WHERE site_key=? ORDER BY proposal_id', (key,)):
                rec = json.loads(row['record_json']); pid = row['proposal_id']
                binding = db.execute('SELECT * FROM proposal_bindings WHERE proposal_id=?', (pid,)).fetchone()
                page = by_url.get(rec['url']); text = normalized.get(rec['url'], '')
                current = bool(binding and page and binding['page_url'] == rec['url'] and
                    binding['source_sha'] == page['sha'] and row['gate'] == 'quote_verified_v2' and
                    page['page'].get('image_parser_version') == VERSION and
                    pid == uid('P2-', row['candidacy_id'], page['sha'], dump(rec)) and
                    norm(rec['endorser']) and norm(rec.get('quote', '')) and
                    ' ' + norm(rec['endorser']) + ' ' in text and
                    ' ' + norm(rec['quote']) + ' ' in text and
                    not is_distinction(rec['endorser'] + ' ' + rec['quote']))
                decision = db.execute('SELECT * FROM decisions WHERE proposal_id=?', (pid,)).fetchone()
                triage = db.execute('SELECT * FROM jev_triage WHERE proposal_id=?', (pid,)).fetchone()
                status = ('machine_accepted_pending_publication_review' if current and decision and
                          decision['action'] == 'accept' else 'held' if current else 'stale_source')
                hint = classification(rec, existing.get(row['candidacy_id'], []))
                counts[status] += 1
                if status == 'machine_accepted_pending_publication_review':
                    counts['accepted_' + hint] += 1
                proposals.append({'id': pid, 'candidacy_id': row['candidacy_id'],
                    'record': rec, 'source_binding': dict(binding) if binding else None,
                    'status': status, 'existing_name_hint': hint,
                    'decision': dict(decision) if decision else None,
                    'jev': ({**{k: triage[k] for k in triage.keys() if k != 'answer_json'},
                             'response': json.loads(triage['answer_json'])} if triage else None)})
            ids = json.loads(task['candidacy_ids'])
            targets = [{k: candidates[i].get(k) for k in ('id', 'position_id', 'name', 'office', 'campaign_url')}
                       for i in ids if i in candidates]
            holds = [{'id': r['hold_id'], 'item': json.loads(r['item_json']), 'reason': r['reason']}
                     for r in db.execute('SELECT * FROM proposal_holds WHERE site_key=? ORDER BY hold_id', (key,))]
            result = db.execute('SELECT model,created_at FROM results WHERE site_key=?', (key,)).fetchone()
            packet = {'version': 1, 'task': dict(task), 'candidates': targets,
                      'pages': pages, 'proposals': proposals, 'extraction_holds': holds,
                      'capture_fingerprint': pages[0]['sha'] if pages else None,
                      'snapshot_sha256': hashlib.sha256(dump({p['url']: p['page'] for p in pages}).encode()).hexdigest(),
                      'extraction': dict(result) if result else None,
                      'publication': 'Named proposals require separate publication review; no automatic carry-forward or withdrawal.'}
            name = 'sites/' + key + '.json'
            sha = write(output / name, packet)
            files.append({'path': name, 'sha256': sha, 'sites': 1, 'pages': len(pages),
                          'image_occurrences': sum(len(p['page'].get('images', [])) for p in pages),
                          'proposals': len(proposals), 'extraction_holds': len(holds)})
            if not pages or task['error']:
                failures.append({'site_key': key, 'url': task['campaign_url'], 'error': task['error']})
            counts['sites'] += 1; counts['captured_sites'] += bool(pages)
            counts['extracted_sites'] += bool(result); counts['pages'] += len(pages)
            counts['image_occurrences'] += files[-1]['image_occurrences']
            counts['extraction_holds'] += len(holds)
        usage = Counter()
        for r in db.execute('SELECT usage_json FROM extraction_batches'):
            for k, v in json.loads(r[0]).items():
                if isinstance(v, int): usage[k] += v
        known = {Path(f['path']).stem for f in files}
        additional = {}
        for candidate in candidates.values():
            url = candidate.get('campaign_url')
            if url and site_key(url) not in known:
                entry = additional.setdefault(site_key(url), {'url': url, 'candidates': [], 'status': 'not_in_original_batch'})
                entry['candidates'].append({'id': candidate['id'], 'name': candidate['name'], 'position_id': candidate['position_id']})
        manifest = {'version': 1, 'dataset_sha256': hashlib.sha256(dataset.read_bytes()).hexdigest(),
                    'counts': dict(counts), 'local_model_usage': dict(usage), 'files': files,
                    'additional_site_queue': [additional[k] for k in sorted(additional)],
                    'fetch_failures': failures,
                    'limitations': ['A captured page is not an exhaustive crawl or current-cycle endorsement certification.',
                        'Names, offices, election cycles, duplicate title variants and quote attribution need publication review.',
                        'Failed fetches, unvisited links and held proposals do not establish absence or withdrawal.',
                        'Images are external URLs with neutral metadata; filenames and alt text establish no identity.']}
        write(output / 'manifest.json', manifest)
        return manifest['counts']
    finally:
        db.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db', type=Path, required=True)
    ap.add_argument('--dataset', type=Path, default=Path('2026-11-03_Bay_Area_Elections.json'))
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(export(args.db, args.dataset, args.output_dir), indent=2))
