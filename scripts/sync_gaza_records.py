"""Capture congressional sources and prepare/apply exact reviewed candidate updates.

The sheet supplies legislative actions and source assessment colors. Only the
official USCPR scorecard supplies grades. Reviewed identity links bind historical
members to current candidacies; a provider ID alone never establishes identity.
"""
import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

import gaza_voting_records as voting
import uscpr_scorecard as uscpr
from reviewed_updates import apply_file, identity, prepare
from research_endorsements import atomic_json

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / '2026-11-03_Bay_Area_Elections.json'
RESEARCH = ROOT / 'research/gaza-records'


def normalized_name(value):
    return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower())


def snapshot_reference(path):
    path = path.resolve()
    if path.parent != RESEARCH or path.suffix != '.json':
        raise ValueError('Publication snapshots must be saved under research/gaza-records/')
    return {'snapshot_path': str(path.relative_to(ROOT)), 'snapshot_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def build_review(data, votes, grades, links, review_id, votes_path, grades_path):
    if grades.get('format') != uscpr.FORMAT or grades.get('source_url') != uscpr.SCORECARD_URL or grades.get('data_url') != uscpr.DATA_URL:
        raise ValueError('Grades must come from the official USCPR scorecard capture, never spreadsheet Column A')
    checked = max(votes['checked_on'], grades['checked_on'])
    if date.fromisoformat(checked) > date.today():
        raise ValueError('Source capture is dated in the future')
    bound = voting.preview(data, votes, links)
    positions = {p['id']: p for p in data['positions']}
    people = {(p['id'], c['name']): c for p in data['positions'] for c in p.get('candidates') or []}
    sources = {}
    def source(key, url, publisher, digest, note, checked_on):
        sources[key] = {'url': url, 'publisher': publisher, 'role': 'publisher', 'checked_on': checked_on,
                        'content_sha256': digest, 'retrieval': note}
    source('tracker', votes['source_url'], votes['provider'], votes['source']['sha256'],
           'Complete XLSX export at ' + votes['source']['url'] + '; dropdown HTML colors are separately hashed in the source snapshot.', votes['checked_on'])
    page = next(s for s in grades['sources'] if s['url'] == uscpr.SCORECARD_URL)
    source('uscpr', grades['source_url'], 'USCPR Action', page['sha256'],
           'Official scorecard -> embedded application -> public JSON feed; all five capture hashes are preserved in the grade snapshot.', grades['checked_on'])
    feed = next(s for s in grades['sources'] if s['url'] == uscpr.DATA_URL)
    source('uscpr-data', uscpr.DATA_URL, 'USCPR Action', feed['sha256'], 'Complete official embedded scorecard JSON feed.', grades['checked_on'])
    decisions, shared = [], []
    voting_settings = {**bound['gaza_voting'], **snapshot_reference(votes_path)}
    grade_settings = {'provider': 'USCPR Action', 'checked_on': grades['checked_on'], 'source_url': grades['source_url'],
                      'data_url': grades['data_url'], 'methodology_url': grades['methodology_url'],
                      'scope_note': grades['coverage']['method'] + ' ' + grades['coverage']['lifetime_grade_period'] + ' Missing members remain ungraded; the feed can lag membership changes.',
                      **snapshot_reference(grades_path)}
    for field, after, key in [('gaza_voting', voting_settings, 'tracker'), ('uscpr_scorecard', grade_settings, 'uscpr')]:
        if data.get(field) != after:
            shared.append({'field': field, 'before': data.get(field), 'after': after, 'source_key': key})
    by_link = {(r['position_id'], r['candidate_name']): r for r in links['links']}
    def decision(key, field, before, after, source_key, label):
        if before == after:
            return
        link = by_link[key]
        decisions.append({'id': label, 'action': 'change', 'field': field, 'position_id': key[0], 'candidate': key[1],
                          'identity': identity(positions[key[0]]), 'source_key': source_key, 'before': before, 'after': after,
                          'reason': 'Copy the complete source record after reviewing the candidate identity and source scope.',
                          'evidence': {'identity_basis': ' '.join(s['summary'] + ' ' + s['url'] for s in link['identity_sources']),
                                       'date_basis': 'Source observed ' + sources[source_key]['checked_on'] + '; action date labels and grade periods are preserved separately.',
                                       'issue_basis': 'Source-selected Gaza/Israel/Palestine legislative actions or explicitly attributed USCPR publisher assessments; no grade is calculated here.'}})
    for update in bound['candidate_updates']:
        key = update['position_id'], update['candidate_name']
        previous = {r['record_id']: r for r in update['before'] or []}
        current = {r['record_id']: r for r in update['after']}
        for rid in previous.keys() | current.keys():
            after = current.get(rid)
            if after is None:
                raise ValueError('A published member record disappeared; review its removal explicitly: ' + rid)
            source_key = 'record-' + rid
            if source_key not in sources:
                source(source_key, after['source_url'], votes['provider'], votes['source']['sha256'], sources['tracker']['retrieval'], votes['checked_on'])
            decision(key, 'gaza_voting_records', previous.get(rid), after, source_key, 'votes-' + key[0] + '-' + rid)
    grade_status = []
    for key, link in by_link.items():
        matches = [m for m in grades['members'] if normalized_name(m['name']) == normalized_name(key[1]) and m['state'] == 'CA']
        if len(matches) > 1:
            raise ValueError('Ambiguous USCPR member name: ' + key[1])
        if not matches:
            if people[key].get('uscpr_grade'):
                raise ValueError('A published grade profile disappeared; review its removal explicitly: ' + key[1])
            grade_status.append({'position_id': key[0], 'candidate': key[1], 'status': 'not_in_current_feed'})
            continue
        member = matches[0]
        if link.get('member_id') and member['member_id'] != link['member_id']:
            raise ValueError('USCPR name/identifier mismatch requires identity review: ' + key[1])
        after = {**deepcopy(member), 'checked_on': grades['checked_on'], 'source_url': grades['source_url']}
        decision(key, 'uscpr_grade', people[key].get('uscpr_grade'), after, 'uscpr', 'grade-' + key[0])
        grade_status.append({'position_id': key[0], 'candidate': key[1], 'status': 'matched_name_state_and_reviewed_identity'})
    return {'version': 1, 'id': review_id, 'election_date': data['election']['date'], 'reviewed_on': checked,
            'counties': [c['name'] for c in data['election']['counties_in_scope']], 'sources': sources, 'notes': {},
            'shared_changes': shared, 'decisions': sorted(decisions, key=lambda d: d['id']), 'grade_status': grade_status,
            'limits': links.get('unmatched_prior_service', []),
            'binding_sha256': hashlib.sha256(json.dumps(links, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    capture = sub.add_parser('capture', help='Capture both public sources; does not edit the election dataset')
    capture.add_argument('--checked-on', required=True)
    capture.add_argument('--output-dir', type=Path, default=RESEARCH)
    review = sub.add_parser('review', help='Write an exact publication review; optionally apply it locally')
    review.add_argument('--votes', type=Path, default=RESEARCH / 'voting-records-2026-10-14.json')
    review.add_argument('--grades', type=Path, default=RESEARCH / 'uscpr-grades-2026-10-14.json')
    review.add_argument('--links', type=Path, default=RESEARCH / 'candidate-links.json')
    review.add_argument('--id', required=True)
    review.add_argument('--output', type=Path, required=True)
    review.add_argument('--apply', action='store_true', help='Apply validated review locally; never commits or pushes')
    args = parser.parse_args()
    if args.command == 'capture':
        date.fromisoformat(args.checked_on)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        outputs = [args.output_dir / (prefix + args.checked_on + '.json') for prefix in ('voting-records-', 'uscpr-grades-')]
        if any(path.exists() for path in outputs):
            parser.error('A dated capture already exists; preserve published snapshots and choose a new output directory.')
        for script, filename in [('gaza_voting_records.py', 'voting-records-'), ('uscpr_scorecard.py', 'uscpr-grades-')]:
            cmd = [sys.executable, str(ROOT / 'scripts' / script)]
            if script == 'gaza_voting_records.py': cmd.append('capture')
            subprocess.run([*cmd, '--checked-on', args.checked_on, '--output', str(args.output_dir / (filename + args.checked_on + '.json'))], check=True)
        return
    data = json.loads(DATA.read_text())
    result = build_review(data, *(json.loads(p.read_text()) for p in (args.votes, args.grades, args.links)), args.id, args.votes, args.grades)
    if not result['decisions'] and not result['shared_changes']:
        print('No research changes; dataset and existing review files preserved.')
        return
    if args.output.exists():
        raise SystemExit('Review file already exists; preserve immutable history and choose a new review ID/path.')
    # Validate the entire proposed result before writing any review or dataset.
    _, report = prepare(data, result)
    atomic_json(args.output, result)
    if args.apply:
        lock = ROOT / '.research/publication.lock'
        lock.parent.mkdir(exist_ok=True)
        with lock.open('x'):
            try:
                report = apply_file(DATA, args.output)
            finally:
                lock.unlink()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
