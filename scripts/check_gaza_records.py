#!/usr/bin/env python3
"""Check pinned Gaza legislative/grade captures and publication identity bindings.

These offline checks establish source consistency, not independent verification
of the tracker or publisher's political judgments. Run this file for regressions;
check_data.py also calls check_gaza_records(data) on the published inventory.
"""
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import gaza_voting_records as voting
import uscpr_scorecard as uscpr

ROOT = Path(__file__).resolve().parents[1]
HASH = re.compile(r'^[0-9a-f]{64}$')
PIN_PATH = re.compile(r'^research/gaza-records/[A-Za-z0-9_.-]+\.json$')
ASSESSMENTS = ('positive', 'negative', 'neutral', 'unclassified')
BASES = ('sheet_dropdown', 'sheet_conditional_format', 'sheet_fill', 'explicit_label', 'none')
STATUSES = ('statement_found', 'no_statement_found', 'unavailable', 'no_website')


def normalized_name(value):
    if not isinstance(value, str):
        return ''
    return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower())


def valid_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def check_date(value, label, errors):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value or parsed > datetime.now(ZoneInfo('America/Los_Angeles')).date():
            raise ValueError
    except (TypeError, ValueError):
        errors.append(label + ': invalid or future checked date')


def pinned_snapshot(settings, label, errors):
    path, digest = settings.get('snapshot_path'), settings.get('snapshot_sha256')
    if not isinstance(path, str) or not PIN_PATH.fullmatch(path):
        errors.append(label + ': missing or unsafe snapshot_path under research/gaza-records/')
        return None
    if not isinstance(digest, str) or not HASH.fullmatch(digest):
        errors.append(label + ': missing or invalid snapshot_sha256')
        return None
    file = ROOT / path
    if file.resolve().parent != (ROOT / 'research/gaza-records').resolve():
        errors.append(label + ': snapshot resolves outside the research directory')
        return None
    try:
        raw = file.read_bytes()
        if len(raw) > 15_000_000 or hashlib.sha256(raw).hexdigest() != digest:
            errors.append(label + ': snapshot SHA-256 does not match committed contents')
            return None
        snapshot = json.loads(raw)
        if not isinstance(snapshot, dict):
            raise ValueError('not an object')
        return snapshot
    except (OSError, ValueError, UnicodeError):
        errors.append(label + ': pinned snapshot cannot be read as JSON')
        return None


def checked_sources(entries, label, errors):
    if not isinstance(entries, list) or not entries:
        errors.append(label + ': source captures are missing')
        return
    for entry in entries:
        if (not isinstance(entry, dict) or not valid_url(entry.get('url'))
                or not isinstance(entry.get('sha256'), str) or not HASH.fullmatch(entry['sha256'])
                or type(entry.get('bytes')) is not int or entry['bytes'] <= 0):
            errors.append(label + ': invalid source URL/hash/byte count')


def load_links(errors):
    try:
        links = json.loads((ROOT / 'research/gaza-records/candidate-links.json').read_text())
        if links.get('format') != 'gaza-legislative-candidate-links/v1' or not isinstance(links.get('links'), list):
            raise ValueError
        result = {}
        for link in links['links']:
            key = link['position_id'], link['candidate_name']
            if (key in result or not isinstance(link.get('matches'), list) or not link['matches']
                    or not isinstance(link.get('identity_sources'), list) or not link['identity_sources']
                    or any(not isinstance(m, dict) for m in link['matches'])
                    or any(not isinstance(s, dict) for s in link['identity_sources'])):
                raise ValueError
            check_date(link.get('reviewed_on'), f'Identity link {key}', errors)
            if not all(valid_url(s.get('url')) for s in link['identity_sources']):
                raise ValueError
            result[key] = link
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        errors.append('Gaza records: reviewed candidate identity links are missing, ambiguous or invalid')
        return {}


def validate_votes_snapshot(snapshot, settings, errors):
    label = 'Gaza voting snapshot'
    if snapshot.get('format') != 'gaza-legislative-tracker/v1' or snapshot.get('source_url') != voting.SOURCE_URL:
        errors.append(label + ': unexpected tracker format or source')
    check_date(snapshot.get('checked_on'), label, errors)
    for key in ('provider', 'checked_on', 'source_url', 'scope_note', 'actions'):
        if settings.get(key) != snapshot.get(key):
            errors.append(f'Gaza voting settings {key}: differs from pinned snapshot')
    checked_sources([snapshot.get('source')], label, errors)
    source = snapshot.get('source') or {}
    if source.get('url') != voting.EXPORT_URL:
        errors.append(label + ': missing public workbook export provenance')
    checked_sources(snapshot.get('color_sources'), label + ' dropdown colors', errors)
    color_sources = snapshot.get('color_sources') or []
    expected_colors = {voting.html_url(config['gid']) for title, config in voting.TABS.items() if title.startswith('119th')}
    if {s.get('url') for s in color_sources if isinstance(s, dict)} != expected_colors:
        errors.append(label + ': current-tab dropdown color captures are incomplete')
    actions, records = snapshot.get('actions'), snapshot.get('records')
    if not isinstance(actions, dict) or not actions or not isinstance(records, list) or not records:
        errors.append(label + ': action/member registry is missing')
        return {}
    registry = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get('record_id'), str):
            errors.append(label + ': malformed member record')
            continue
        rid = record['record_id']
        if rid in registry:
            errors.append(label + ': duplicate record_id ' + rid)
        registry[rid] = record
        check_date(record.get('checked_on'), label + ' ' + rid, errors)
        if record.get('checked_on') != snapshot.get('checked_on') or not valid_url(record.get('source_url')):
            errors.append(label + ' ' + rid + ': mismatched source or checked date')
        validate_action_values(record, actions, label + ' ' + rid, errors)
    counts = snapshot.get('counts') or {}
    if (counts.get('members') != len(records) or counts.get('actions') != len(actions)
            or counts.get('member_action_cells') != sum(len(r.get('actions') or []) for r in records if isinstance(r, dict))):
        errors.append(label + ': capture counts do not match complete member/action registries')
    return registry


def validate_action_values(record, actions, label, errors):
    values = record.get('actions')
    if not isinstance(values, list) or not values:
        errors.append(label + ': member action values are missing')
        return
    seen = set()
    for item in values:
        if not isinstance(item, dict):
            errors.append(label + ': malformed action value')
            continue
        aid = item.get('action_id')
        if not isinstance(aid, str) or aid not in actions:
            errors.append(label + ': unknown action reference ' + str(aid))
        if isinstance(aid, str) and aid in seen:
            errors.append(label + ': duplicate action_id ' + aid)
        seen.add(aid if isinstance(aid, str) else None)
        if item.get('assessment') not in ASSESSMENTS or not isinstance(item.get('value'), str):
            errors.append(label + ': invalid assessment/value')
        fill = item.get('sheet_color')
        if 'sheet_color' not in item or (fill is not None and (not isinstance(fill, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', fill))):
            errors.append(label + ': invalid or missing source color')
        if item.get('assessment_basis', 'none') not in BASES:
            errors.append(label + ': invalid assessment basis')
        if item.get('source_url') is not None and not valid_url(item['source_url']):
            errors.append(label + ': invalid action source URL')
        metadata = actions.get(aid) if isinstance(aid, str) else None
        if isinstance(metadata, dict):
            if any(metadata.get(key) != record.get(key) for key in ('congress', 'chamber', 'sheet_title')):
                errors.append(label + ': action belongs to another source tab')


def validate_grade_snapshot(snapshot, settings, errors):
    label = 'USCPR scorecard snapshot'
    if (snapshot.get('format') != uscpr.FORMAT or snapshot.get('source_url') != uscpr.SCORECARD_URL
            or snapshot.get('data_url') != uscpr.DATA_URL or snapshot.get('methodology_url') != uscpr.METHODOLOGY_URL):
        errors.append(label + ': expected official scorecard delivery chain')
    check_date(snapshot.get('checked_on'), label, errors)
    if settings.get('provider') != 'USCPR Action':
        errors.append('USCPR settings: publisher attribution is missing')
    for key in ('checked_on', 'source_url', 'data_url', 'methodology_url'):
        if settings.get(key) != snapshot.get(key):
            errors.append(f'USCPR settings {key}: differs from pinned snapshot')
    if not settings.get('scope_note'):
        errors.append('USCPR settings: source scope note is missing')
    checked_sources(snapshot.get('sources'), label, errors)
    sources = {s.get('role'): s.get('url') for s in snapshot.get('sources') or [] if isinstance(s, dict)}
    expected = {'scorecard': uscpr.SCORECARD_URL, 'embedded_application': uscpr.APP_URL,
                'grades_feed': uscpr.DATA_URL, 'methodology': uscpr.METHODOLOGY_URL}
    if any(sources.get(role) != url for role, url in expected.items()) or not str(sources.get('application_bundle', '')).startswith(uscpr.APP_URL + 'assets/'):
        errors.append(label + ': official page/application/feed provenance is incomplete')
    members = snapshot.get('members')
    if not isinstance(members, list) or not members:
        errors.append(label + ': member feed is missing')
        return []
    identities = set()
    for member in members:
        if not isinstance(member, dict):
            errors.append(label + ': malformed member profile')
            continue
        key = member.get('member_id'), member.get('name'), member.get('state'), member.get('chamber')
        if key in identities:
            errors.append(label + ': duplicate member identity')
        identities.add(key)
        grades = member.get('grades')
        if not isinstance(grades, list) or not grades:
            errors.append(label + ': missing grade periods')
            continue
        periods = set()
        for grade in grades:
            if not isinstance(grade, dict):
                errors.append(label + ': malformed grade')
                continue
            period = grade.get('period')
            if period in periods or period not in ('119th Congress', 'Lifetime'):
                errors.append(label + ': invalid or duplicate grade period')
            periods.add(period)
            letter = grade.get('grade')
            source_letter = grade.get('source_grade')
            if (source_letter not in ('A', 'B', 'C', 'D', 'F', 'N/A') or letter not in ('A', 'B', 'C', 'D', 'F', None)
                    or letter != (None if source_letter == 'N/A' else source_letter)):
                errors.append(label + ': missing/ungraded value must not become a letter grade')
            try:
                score = uscpr.percentage(grade.get('source_score'))
            except ValueError:
                errors.append(label + ': invalid publisher percentage')
            else:
                if grade.get('score') != score:
                    errors.append(label + ': publisher score was recalculated or changed')
        if periods != {'119th Congress', 'Lifetime'}:
            errors.append(label + ': expected both official grade periods')
    coverage = snapshot.get('coverage') or {}
    if coverage.get('member_count') != len(members):
        errors.append(label + ': member count differs from captured feed')
    return members


def validate_platform(candidate, platform, label, errors):
    if not isinstance(platform, dict):
        errors.append(label + ': platform review must be an object')
        return
    status, pages = platform.get('status'), platform.get('pages')
    if status not in STATUSES:
        errors.append(label + ': invalid platform status')
    check_date(platform.get('checked_on'), label, errors)
    if not isinstance(platform.get('scope_note'), str) or not platform['scope_note'].strip():
        errors.append(label + ': platform scope/absence limitation is missing')
    if not isinstance(pages, list):
        errors.append(label + ': platform pages are missing')
        pages = []
    urls = []
    for page in pages:
        if (not isinstance(page, dict) or not valid_url(page.get('url')) or not isinstance(page.get('title'), str)
                or not isinstance(page.get('content_sha256'), str) or not HASH.fullmatch(page['content_sha256'])):
            errors.append(label + ': page capture needs URL, title and content hash')
        elif page['url'] in urls:
            errors.append(label + ': duplicate platform page URL')
        else:
            urls.append(page['url'])
    if status == 'statement_found':
        if not pages or any(not isinstance(platform.get(key), str) or not platform[key].strip() for key in ('summary', 'quote', 'source_url')):
            errors.append(label + ': a platform position requires summary, quote and captured source page')
        if platform.get('source_url') not in urls:
            errors.append(label + ': platform position source is not among captured pages')
    elif any(key in platform for key in ('summary', 'quote', 'source_url')):
        errors.append(label + ': an absence/unavailable result must not publish a stance summary or quote')
    if status == 'no_statement_found' and not pages:
        errors.append(label + ': no-statement finding needs successfully captured pages')
    if status == 'no_website' and (pages or candidate.get('campaign_url')):
        errors.append(label + ': no-website finding conflicts with an existing campaign URL or captured pages')


def check_gaza_records(data):
    """Return publication consistency errors without changing data or research files."""
    errors = []
    people = {}
    for position in data.get('positions', []):
        for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates'):
            for candidate in position.get(roster) or []:
                if isinstance(candidate, dict):
                    people[(position.get('id'), candidate.get('name'), roster)] = candidate
    any_votes = any('gaza_voting_records' in c for c in people.values())
    any_grades = any('uscpr_grade' in c for c in people.values())
    votes_settings, grade_settings = data.get('gaza_voting'), data.get('uscpr_scorecard')
    for field, settings, present in [('gaza_voting', votes_settings, any_votes), ('uscpr_scorecard', grade_settings, any_grades)]:
        if present and not isinstance(settings, dict):
            errors.append(field + ': candidate records require pinned shared source settings')
    votes = pinned_snapshot(votes_settings, 'Gaza voting', errors) if isinstance(votes_settings, dict) else None
    grades = pinned_snapshot(grade_settings, 'USCPR scorecard', errors) if isinstance(grade_settings, dict) else None
    registry = validate_votes_snapshot(votes, votes_settings, errors) if votes else {}
    members = validate_grade_snapshot(grades, grade_settings, errors) if grades else []
    links = load_links(errors) if any_votes or any_grades or votes or grades else {}
    shared_actions = votes_settings.get('actions', {}) if isinstance(votes_settings, dict) else {}
    if not isinstance(shared_actions, dict):
        errors.append('Gaza voting: shared action registry must be an object')
        shared_actions = {}
    for (pid, name, roster), candidate in people.items():
        label = str(pid) + ' / ' + str(name)
        link = links.get((pid, name))
        expected_votes = []
        if link and votes:
            for match in link['matches']:
                found = [r for r in registry.values() if (r.get('sheet_title'), r.get('member_name'), r.get('district')) == (match.get('sheet_title'), match.get('member_name'), match.get('district'))]
                if len(found) != 1:
                    errors.append(label + ': reviewed member/tab/district identity is absent or ambiguous in snapshot')
                else:
                    expected_votes.append(found[0]['record_id'])
        records = candidate.get('gaza_voting_records')
        if 'gaza_voting_records' in candidate:
            if not isinstance(records, list) or not records:
                errors.append(label + ': legislative records must be a nonempty array')
                records = []
            if not link:
                errors.append(label + ': legislative records have no reviewed candidate identity binding')
            seen = set()
            for record in records:
                if not isinstance(record, dict):
                    errors.append(label + ': malformed legislative record')
                    continue
                rid = record.get('record_id')
                if not isinstance(rid, str) or rid in seen:
                    errors.append(label + ': duplicate or invalid member record_id')
                seen.add(rid if isinstance(rid, str) else None)
                if isinstance(rid, str) and (rid not in registry or record != registry[rid]):
                    errors.append(label + ': member record differs from pinned source snapshot: ' + rid)
                validate_action_values(record, shared_actions, label, errors)
                check_date(record.get('checked_on'), label, errors)
            if votes and set(expected_votes) != seen:
                errors.append(label + ': published records do not equal the complete reviewed member/tab bindings')
        elif expected_votes and roster == 'candidates':
            errors.append(label + ': reviewed legislative records are missing from publication')
        expected_member = []
        if link and grades:
            expected_member = [m for m in members if isinstance(m, dict) and normalized_name(m.get('name')) == normalized_name(name)
                               and m.get('state') == 'CA' and m.get('member_id') == link.get('member_id')]
            if len(expected_member) > 1:
                errors.append(label + ': official grade member identity is ambiguous')
        profile = candidate.get('uscpr_grade')
        if 'uscpr_grade' in candidate:
            if not isinstance(profile, dict) or not link or len(expected_member) != 1:
                errors.append(label + ': USCPR grade lacks a reviewed name/state/member-ID identity match')
            else:
                expected = {**expected_member[0], 'checked_on': grades['checked_on'], 'source_url': grades['source_url']}
                if profile != expected:
                    errors.append(label + ': USCPR grade profile differs from official pinned source')
                check_date(profile.get('checked_on'), label + ' USCPR', errors)
        elif expected_member and roster == 'candidates':
            errors.append(label + ': matched official USCPR profile is missing from publication')
        if 'gaza_platform' in candidate:
            validate_platform(candidate, candidate['gaza_platform'], label + ' platform', errors)
    return errors


if __name__ == '__main__':
    import unittest
    from unittest.mock import patch

    class GazaRecordTests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.directory = tempfile.TemporaryDirectory()
            cls.root = Path(cls.directory.name)
            folder = cls.root / 'research/gaza-records'
            folder.mkdir(parents=True)
            for name in ('voting-records-2026-10-14.json', 'uscpr-grades-2026-10-14.json', 'candidate-links.json'):
                (folder / name).write_bytes((ROOT / 'research/gaza-records' / name).read_bytes())
            cls.votes = json.loads((folder / 'voting-records-2026-10-14.json').read_text())
            cls.grades = json.loads((folder / 'uscpr-grades-2026-10-14.json').read_text())
            cls.links = json.loads((folder / 'candidate-links.json').read_text())
            cfg = lambda name: {'snapshot_path': 'research/gaza-records/' + name,
                                'snapshot_sha256': hashlib.sha256((folder / name).read_bytes()).hexdigest()}
            positions = {}
            for link in cls.links['links']:
                positions.setdefault(link['position_id'], {'id': link['position_id'], 'candidates': []})
                candidate = {'name': link['candidate_name']}
                candidate['gaza_voting_records'] = [deepcopy(r) for match in link['matches'] for r in cls.votes['records']
                                                    if (r['sheet_title'], r['member_name'], r.get('district')) == (match['sheet_title'], match['member_name'], match.get('district'))]
                matches = [m for m in cls.grades['members'] if normalized_name(m['name']) == normalized_name(candidate['name']) and m['state'] == 'CA' and m['member_id'] == link['member_id']]
                if matches:
                    candidate['uscpr_grade'] = {**deepcopy(matches[0]), 'source_url': cls.grades['source_url'], 'checked_on': cls.grades['checked_on']}
                positions[link['position_id']]['candidates'].append(candidate)
            cls.baseline = {'positions': list(positions.values()),
                            'gaza_voting': {**{k: deepcopy(cls.votes[k]) for k in ('provider', 'checked_on', 'source_url', 'scope_note', 'actions')}, **cfg('voting-records-2026-10-14.json')},
                            'uscpr_scorecard': {'provider': 'USCPR Action', 'scope_note': 'Attributed publisher assessment; missing members remain ungraded.',
                                                **{k: cls.grades[k] for k in ('checked_on', 'source_url', 'data_url', 'methodology_url')}, **cfg('uscpr-grades-2026-10-14.json')}}

        @classmethod
        def tearDownClass(cls):
            cls.directory.cleanup()

        def setUp(self):
            self.data = deepcopy(self.baseline)
            self.root_patch = patch.dict(globals(), ROOT=self.root)
            self.root_patch.start()

        def tearDown(self):
            self.root_patch.stop()

        def candidate(self, name='John Garamendi'):
            return next(c for p in self.data['positions'] for c in p['candidates'] if c['name'] == name)

        def test_valid_complete_sources_and_unknown_grade_allowed(self):
            self.assertEqual(check_gaza_records(self.data), [])
            self.assertNotIn('uscpr_grade', self.candidate('Aisha Wahab'))
            self.assertNotIn('uscpr_grade', self.candidate('Barbara Lee'))

        def test_changed_vote_and_missing_action_reference_rejected(self):
            action = self.candidate()['gaza_voting_records'][0]['actions'][0]
            action['value'] = 'Invented vote'
            self.assertTrue(any('differs from pinned' in e for e in check_gaza_records(self.data)))
            action['action_id'] = 'missing-action'
            self.assertTrue(any('unknown action reference' in e for e in check_gaza_records(self.data)))

        def test_action_metadata_duplicate_and_bad_assessment_rejected(self):
            action = self.candidate()['gaza_voting_records'][0]['actions'][0]
            self.data['gaza_voting']['actions'][action['action_id']]['title'] = 'Changed framing'
            self.assertTrue(any('settings actions' in e for e in check_gaza_records(self.data)))
            action['assessment'] = 'good'
            self.candidate()['gaza_voting_records'][0]['actions'].append(deepcopy(action))
            errors = check_gaza_records(self.data)
            self.assertTrue(any('duplicate action_id' in e for e in errors))
            self.assertTrue(any('invalid assessment' in e for e in errors))

        def test_pinned_path_hash_and_capture_dates_required(self):
            self.data['gaza_voting']['snapshot_path'] = '../source.json'
            self.data['uscpr_scorecard']['snapshot_sha256'] = '0' * 64
            errors = check_gaza_records(self.data)
            self.assertTrue(any('unsafe snapshot_path' in e for e in errors))
            self.assertTrue(any('SHA-256 does not match' in e for e in errors))
            self.data = deepcopy(self.baseline)
            self.candidate()['gaza_voting_records'][0]['checked_on'] = '2026-02-30'
            self.assertTrue(any('invalid or future' in e for e in check_gaza_records(self.data)))

        def test_complete_candidate_records_cannot_be_dropped_or_duplicated(self):
            self.candidate()['gaza_voting_records'].pop()
            self.assertTrue(any('complete reviewed' in e for e in check_gaza_records(self.data)))
            self.data = deepcopy(self.baseline)
            self.candidate()['gaza_voting_records'].append(deepcopy(self.candidate()['gaza_voting_records'][0]))
            self.assertTrue(any('duplicate or invalid member record_id' in e for e in check_gaza_records(self.data)))

        def test_grade_changes_and_missing_matched_profile_rejected(self):
            self.candidate()['uscpr_grade']['grades'][0]['grade'] = 'F' if self.candidate()['uscpr_grade']['grades'][0]['grade'] != 'F' else 'A'
            self.assertTrue(any('profile differs' in e for e in check_gaza_records(self.data)))
            self.candidate().pop('uscpr_grade')
            self.assertTrue(any('profile is missing' in e for e in check_gaza_records(self.data)))

        def test_same_id_does_not_transfer_swalwell_grade_to_wahab(self):
            stale = next(m for m in self.grades['members'] if m['name'] == 'Eric Swalwell')
            self.candidate('Aisha Wahab')['uscpr_grade'] = {**deepcopy(stale), 'source_url': uscpr.SCORECARD_URL, 'checked_on': self.grades['checked_on']}
            self.assertTrue(any('name/state/member-ID' in e for e in check_gaza_records(self.data)))

        def test_publisher_na_remains_ungraded_instead_of_f_or_zero(self):
            snapshot = deepcopy(self.grades)
            member = next(m for m in snapshot['members'] if m['name'] == 'John Garamendi')
            for grade in member['grades']:
                grade.update(grade=None, source_grade='N/A', score=None, source_score='N/A')
            path = self.root / 'research/gaza-records/ungraded.json'
            raw = (json.dumps(snapshot) + '\n').encode()
            path.write_bytes(raw)
            self.data['uscpr_scorecard'].update(snapshot_path='research/gaza-records/ungraded.json', snapshot_sha256=hashlib.sha256(raw).hexdigest())
            self.candidate()['uscpr_grade'] = {**deepcopy(member), 'checked_on': snapshot['checked_on'], 'source_url': snapshot['source_url']}
            self.assertEqual(check_gaza_records(self.data), [])
            self.candidate()['uscpr_grade']['grades'][0].update(grade='F', score=0)
            self.assertTrue(any('profile differs' in e for e in check_gaza_records(self.data)))

        def test_foreign_record_cannot_be_attached_by_name_or_district(self):
            self.candidate('Barbara Lee')['gaza_voting_records'] = deepcopy(self.candidate('Lateefah Simon')['gaza_voting_records'])
            self.assertTrue(any('complete reviewed' in e for e in check_gaza_records(self.data)))

        def test_platform_statement_requires_captured_quote_source(self):
            page = {'url': 'https://example.org/issues', 'title': 'Issues', 'content_sha256': 'a' * 64}
            self.candidate()['gaza_platform'] = {'status': 'statement_found', 'checked_on': '2026-10-14', 'scope_note': 'Candidate platform pages checked.',
                                                 'pages': [page], 'summary': 'Supports a ceasefire.', 'quote': 'I support a ceasefire.', 'source_url': page['url']}
            self.assertEqual(check_gaza_records(self.data), [])
            self.candidate()['gaza_platform']['source_url'] = 'https://unrelated.example.org/'
            self.assertTrue(any('not among captured pages' in e for e in check_gaza_records(self.data)))

        def test_platform_absence_is_scoped_and_not_a_stance(self):
            platform = {'status': 'no_statement_found', 'checked_on': '2026-10-14', 'scope_note': 'No statement found on these successfully captured pages; this is not neutrality.',
                        'pages': [{'url': 'https://example.org/issues', 'title': 'Issues', 'content_sha256': 'b' * 64}]}
            self.candidate()['gaza_platform'] = platform
            self.assertEqual(check_gaza_records(self.data), [])
            platform['summary'] = 'Neutral'
            self.assertTrue(any('must not publish a stance' in e for e in check_gaza_records(self.data)))
            platform.pop('summary')
            platform['pages'] = []
            self.assertTrue(any('needs successfully captured pages' in e for e in check_gaza_records(self.data)))

    unittest.main()
