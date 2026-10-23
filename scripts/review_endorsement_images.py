"""Deterministic image-evidence updates from complete source packets.

No identity inference. `decisions --policy all-content` keeps every non-chrome
image (including unknown logos and portraits); `hold` creates a task for each
item for a reviewer. Every item needs a disposition before build-review runs.
Shards can be delegated by capture; do not split one capture across writers.
Publication is a separate exact before/after reviewed_updates.py apply step.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

from endorsement_images import image_record, VERSION, SUPPORTED_VERSIONS
from publication_reviews import file_sha
from research_endorsements import atomic_json, dump, digest
from reviewed_updates import identity


def decisions(packet, packet_sha, policy='hold'):
    seen = set(); items = []
    for image in packet['images']:
        action = 'hold'
        reason = 'Review source placement; no identity or relationship is inferred.'
        if policy == 'all-content':
            action = 'exclude' if image['chrome'] or image['src'] in seen else 'include'
            reason = 'Navigation/header/footer or repeated asset.' if action == 'exclude' else 'Preserve content image neutrally, including ambiguous logos and portraits.'
        items.append({'id': image['observation_id'], 'action': action, 'reason': reason})
        if action == 'include':
            seen.add(image['src'])
    return {'version': 1, 'packet_sha256': packet_sha, 'policy': policy, 'items': items}


def selected_images(packet, review, packet_sha):
    if packet['version'] not in SUPPORTED_VERSIONS or review['packet_sha256'] != packet_sha:
        raise ValueError('Stale packet or unsupported parser version')
    images = {i['observation_id']: i for i in packet['images']}
    items = review['items']
    if len(images) != len(packet['images']) or len({i['id'] for i in items}) != len(items) or {i['id'] for i in items} != set(images):
        raise ValueError('Every inventory item needs exactly one disposition; missing, duplicate or unknown ID')
    for item in items:
        if item['action'] not in {'include', 'exclude', 'hold'} or len(item.get('reason', '').strip()) < 8:
            raise ValueError('Expected include/exclude/hold with concrete reason')
    if packet.get('unresolved_images') and not review.get('unresolved_reason'):
        raise ValueError('Unsupported/missing image URLs require an explicit unresolved_reason; absence cannot be inferred')
    if any(i['action'] == 'hold' for i in items):
        raise ValueError('Unresolved images: include neutrally or document exclusion; do not silently omit holds')
    return [images[i['id']] for i in items if i['action'] == 'include']


def build_review(data, packet, review, packet_sha, position_id, candidate, review_id):
    images = selected_images(packet, review, packet_sha)
    position = next(p for p in data['positions'] if p['id'] == position_id)
    eligible_nationwide = not position['counties'] and (position.get('government_level') == 'Federal' or position.get('office') == 'Governor')
    roster = list(position.get('candidates') or []) + (list(position.get('filed_candidates_not_confirmed_on_ballot') or []) if eligible_nationwide else [])
    person = next(c for c in roster if c['name'] == candidate)
    if not person.get('campaign_url'):
        raise ValueError('A reviewed candidate campaign URL is required')
    from urllib.parse import urlsplit
    host = lambda u: urlsplit(u).hostname.removeprefix('www.')
    if host(packet['source_url']) != host(person['campaign_url']):
        raise ValueError('Captured page must belong to this candidate campaign host; separately review redirects/shared sites')
    changes = []
    existing = {r['id']: r for r in person.get('endorsement_images', [])}
    for image in images:
        record = image_record(image, packet['source_url'], packet['checked_on'], packet['source_sha256'])
        before = existing.get(record['id']) or next((r for r in existing.values() if
            r['source_url'] == record['source_url'] and r['image_url'] == record['image_url']), None)
        if before:
            record['id'] = before['id']
        if before == record:
            continue
        changes.append({'id': 'image-' + record['id'], 'action': 'change', 'field': 'endorsement_images',
                        'source_key': 'page', 'position_id': position_id, 'candidate': candidate,
                        'identity': identity(position), 'before': before, 'after': record,
                        'reason': 'Preserve selected campaign image without asserting identity or endorsement.',
                        'evidence': {'identity_basis': 'Reviewed campaign URL and exact candidacy/office identity.',
                                     'date_basis': 'Actual source packet observation date, not announcement date.',
                                     'issue_basis': 'Neutral source-image evidence; every inventory item has a disposition.'}})
    return {'version': 1, 'id': review_id, 'election_date': data['election']['date'],
            'reviewed_on': packet['checked_on'], 'counties': position['counties'] or [c['name'] for c in data['election']['counties_in_scope']],
            'base_dataset_sha256': digest(dump(data)), 'notes': {},
            'sources': {'page': {'url': packet['source_url'], 'checked_on': packet['checked_on'],
                                  'publisher': candidate + ' campaign', 'role': 'campaign', 'candidate': candidate,
                                  'content_sha256': packet['source_sha256'], 'retrieval': 'Complete HTML image inventory; decisions bound to packet SHA-256 ' + packet_sha}},
            'decisions': changes, 'image_dispositions': review}


def export_ledger(db_path, output_dir, data):
    """Export ALL current source pages, grouped for deterministic/delegated work.

    Legacy captures stay in the queue with an explicit recrawl requirement.
    No LLM extraction is needed to preserve images neutrally.
    """
    import sqlite3
    from endorsement_extract import candidates_from_data
    rows = candidates_from_data(data)
    if not Path(db_path).is_file():
        raise ValueError('Campaign ledger does not exist; plan/crawl first')
    db = sqlite3.connect(Path(db_path).resolve().as_uri() + '?mode=ro', uri=True); db.row_factory = sqlite3.Row
    output_dir.mkdir(parents=True, exist_ok=True)
    queue = []
    try:
        for task in db.execute('SELECT * FROM tasks ORDER BY site_key'):
            captured = db.execute('SELECT * FROM pages WHERE site_key=? ORDER BY url', (task['site_key'],)).fetchall()
            targets = [rows[cid] for cid in json.loads(task['candidacy_ids']) if cid in rows]
            if not captured:
                queue.append({'site_key': task['site_key'], 'url': task['campaign_url'], 'status': 'needs_capture', 'error': task['error']})
            for row in captured:
                page = json.loads(row['page_json'])
                entry = {'site_key': task['site_key'], 'url': row['url'], 'candidates': [
                    {'position_id': c['position_id'], 'candidate': c['name']} for c in targets],
                    'crawl_limits': page.get('crawl_limits', [])}
                if page.get('image_parser_version') != VERSION or not page.get('source_sha256'):
                    entry['status'] = 'needs_recrawl'
                elif len(targets) != 1:
                    entry['status'] = 'needs_candidate_attribution'
                else:
                    packet = {'version': VERSION, 'source_url': row['url'], 'checked_on': row['observed_at'][:10],
                              'source_sha256': page['source_sha256'], 'text': page['text'], 'images': page.get('images', []),
                              'unresolved_images': page.get('unresolved_images', []),
                              'limitation': 'HTML inventory only; crawl limits remain explicit; no absence or endorsement inference.'}
                    filename = task['site_key'] + '-' + hashlib.sha256(row['url'].encode()).hexdigest()[:12] + '-' + row['sha'][:12] + '.json'
                    path = output_dir / filename
                    if path.exists() and json.loads(path.read_text()) != packet:
                        raise ValueError('Existing packet differs; preserve captures and choose a new output directory')
                    atomic_json(path, packet)
                    decision_path = path.with_name(path.stem + '-decisions.json')
                    if not decision_path.exists():
                        atomic_json(decision_path, decisions(packet, file_sha(path), 'all-content'))
                    entry.update(status='ready', capture=str(path), decisions=str(decision_path))
                queue.append(entry)
        atomic_json(output_dir / 'queue.json', {'version': 1, 'items': queue})
    finally:
        db.close()
    return {'items': len(queue), 'ready': sum(e['status'] == 'ready' for e in queue), 'queue': str(output_dir / 'queue.json')}


def build_queue(data, queue, review_id, reviewed_on):
    """One deterministic, reviewable update for every ready source in a queue."""
    result = {'version': 1, 'id': review_id, 'election_date': data['election']['date'],
              'reviewed_on': reviewed_on, 'counties': [], 'base_dataset_sha256': digest(dump(data)),
              'sources': {}, 'notes': {}, 'decisions': [], 'outstanding_queue': []}
    seen = set()
    for entry in queue['items']:
        if entry['status'] != 'ready':
            result['outstanding_queue'].append(entry)
            continue
        path = Path(entry['capture']); packet = json.loads(path.read_text())
        dispositions = json.loads(Path(entry['decisions']).read_text())
        target = entry['candidates'][0]
        position = next(p for p in data['positions'] if p['id'] == target['position_id'])
        if not position['counties'] and position.get('government_level') != 'Federal' and position.get('office') != 'Governor':
            result['outstanding_queue'].append({**entry, 'status': 'outside_publication_scope'})
            continue
        part = build_review(data, packet, dispositions, file_sha(path), target['position_id'], target['candidate'], review_id)
        key = hashlib.sha256((target['position_id'] + target['candidate'] + packet['source_url']).encode()).hexdigest()[:24]
        result['sources'][key] = part['sources']['page']
        result['counties'] += part['counties']
        for change in part['decisions']:
            unique = (change['position_id'], change['candidate'], change['after']['id'])
            if unique in seen:
                raise ValueError('Repeated source/candidacy in queue; resolve before applying')
            seen.add(unique)
            result['decisions'].append({**change, 'id': key + '-' + change['id'], 'source_key': key})
    result['counties'] = sorted(set(result['counties']))
    return result


def plan_missing(data, nationwide_house=False):
    """Find publication gaps from actual campaign-claim source URLs, not name guesses."""
    from urllib.parse import urlsplit, urlunsplit
    def canonical(u):
        p = urlsplit(u)
        return urlunsplit((p.scheme, p.netloc.lower().removeprefix('www.'), p.path.rstrip('/'), '', ''))
    entries = []
    for p in data['positions']:
        if nationwide_house and not (not p['counties'] and p.get('office_category') == 'U.S. House'):
            continue
        for c in p.get('candidates') or []:
            if not c.get('campaign_url'):
                continue
            captures = c.get('endorsement_images', [])
            urls = sorted({e['url'] for e in c.get('endorsements', []) if e.get('verification') == 'campaign_claim'
                           and urlsplit(e['url']).hostname.removeprefix('www.') == urlsplit(c['campaign_url']).hostname.removeprefix('www.')
                           and 'endorse' in urlsplit(e['url']).path.lower()})
            for url in urls:
                previous = [i for i in captures if canonical(i['source_url']) == canonical(url)]
                newest_image = max((i.get('checked_on', '') for i in previous), default='')
                newest_text = max((e.get('checked_on', '') for e in c.get('endorsements', []) if canonical(e['url']) == canonical(url)), default='')
                if not previous or newest_image < newest_text:
                    entries.append({'url': url, 'status': 'needs_capture',
                                    'reason': 'No page image inventory' if not previous else 'Text source observed after image snapshot',
                                    'candidates': [{'position_id': p['id'], 'candidate': c['name']}]})
    return {'version': 1, 'scope': 'nationwide_house' if nationwide_house else 'all_printed', 'items': entries,
            'limitation': 'Known published campaign endorsement pages lacking image evidence. Not a complete crawl, image identity inference or absence finding.'}


def capture_plan(plan, output_dir, checked_on, workers=4):
    from concurrent.futures import ThreadPoolExecutor
    from capture_endorsement_images import capture
    from research_endorsements import Fetcher, Blocked
    # Refuse before fetching or writing: a repeated run must not replace its
    # ready queue with failures caused by the existing immutable packets.
    if output_dir.exists():
        raise ValueError('Preserve captures and queue; choose a fresh output directory')
    output_dir.mkdir(parents=True)
    urls = sorted({e['url'] for e in plan['items']})
    def one(url):
        try:
            raw, mime, final = Fetcher().request(url)
            if mime not in {'text/html', 'application/xhtml+xml'}:
                raise ValueError('HTML required; explicit browser/PDF review needed')
            packet = capture(raw, final, checked_on)
            name = hashlib.sha256(url.encode()).hexdigest()[:24]
            path = output_dir / (name + '.json'); dp = output_dir / (name + '-decisions.json')
            if path.exists() or dp.exists():
                raise ValueError('Preserve captures; choose a fresh output directory')
            atomic_json(path, packet)
            disposition = decisions(packet, file_sha(path), 'all-content')
            if packet.get('unresolved_images'):
                return url, {'status': 'unresolved_images', 'capture': str(path), 'unresolved_images': packet['unresolved_images']}
            atomic_json(dp, disposition)
            return url, {'status': 'ready', 'capture': str(path), 'decisions': str(dp)}
        except (ValueError, OSError, Blocked) as exc:
            return url, {'status': 'unavailable', 'reason': str(exc)[:240]}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fetched = dict(pool.map(one, urls))
    queue = {'version': 1, 'items': [{**entry, **fetched[entry['url']]} for entry in plan['items']]}
    atomic_json(output_dir / 'queue.json', queue)
    return {'pages': len(urls), 'ready': sum(e['status'] == 'ready' for e in queue['items']),
            'outstanding': sum(e['status'] != 'ready' for e in queue['items'])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('plan-missing'); q.add_argument('--nationwide-house', action='store_true')
    q.add_argument('--dataset', type=Path, default=Path('2026-11-03_Bay_Area_Elections.json')); q.add_argument('--output', type=Path, required=True)
    q = sub.add_parser('capture-plan'); q.add_argument('--plan', type=Path, required=True); q.add_argument('--output-dir', type=Path, required=True)
    q.add_argument('--checked-on', required=True); q.add_argument('--workers', type=int, choices=range(1,5), default=4)
    q = sub.add_parser('export-ledger'); q.add_argument('--db', type=Path, required=True)
    q.add_argument('--dataset', type=Path, default=Path('2026-11-03_Bay_Area_Elections.json')); q.add_argument('--output-dir', type=Path, required=True)
    q = sub.add_parser('build-queue'); q.add_argument('--queue', type=Path, required=True)
    q.add_argument('--dataset', type=Path, default=Path('2026-11-03_Bay_Area_Elections.json')); q.add_argument('--id', required=True)
    q.add_argument('--reviewed-on', required=True); q.add_argument('--output', type=Path, required=True)
    q = sub.add_parser('decisions'); q.add_argument('--policy', choices=['hold', 'all-content'], default='hold')
    q.add_argument('--capture', type=Path, required=True); q.add_argument('--output', type=Path, required=True)
    q = sub.add_parser('build-review'); q.add_argument('--capture', type=Path, required=True)
    q.add_argument('--decisions', type=Path, required=True); q.add_argument('--dataset', type=Path, default=Path('2026-11-03_Bay_Area_Elections.json'))
    q.add_argument('--position-id', required=True); q.add_argument('--candidate', required=True)
    q.add_argument('--id', required=True)
    q.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.command == 'plan-missing':
        if args.output.exists(): p.error('Choose a fresh plan output')
        result = plan_missing(json.loads(args.dataset.read_text()), args.nationwide_house)
        atomic_json(args.output, result); print(json.dumps({'missing_pages': len(result['items'])})); return
    if args.command == 'capture-plan':
        print(json.dumps(capture_plan(json.loads(args.plan.read_text()), args.output_dir, args.checked_on, args.workers))); return
    if args.command == 'export-ledger':
        print(json.dumps(export_ledger(args.db, args.output_dir, json.loads(args.dataset.read_text()))))
        return
    if args.output.exists():
        p.error('Choose a new output; preserve reviewed captures and decisions')
    if args.command == 'build-queue':
        result = build_queue(json.loads(args.dataset.read_text()), json.loads(args.queue.read_text()), args.id, args.reviewed_on)
        atomic_json(args.output, result)
        print(json.dumps({'changes': len(result['decisions']), 'outstanding': len(result['outstanding_queue']), 'output': str(args.output)}))
        return
    packet = json.loads(args.capture.read_text()); sha = file_sha(args.capture)
    if args.command == 'decisions':
        result = decisions(packet, sha, args.policy)
    else:
        result = build_review(json.loads(args.dataset.read_text()), packet, json.loads(args.decisions.read_text()), sha,
                              args.position_id, args.candidate, args.id)
    args.output.parent.mkdir(parents=True, exist_ok=True); atomic_json(args.output, result)
    print(json.dumps({'output': str(args.output), 'items': len(result.get('items', result.get('decisions', [])))}))


if __name__ == '__main__':
    main()
