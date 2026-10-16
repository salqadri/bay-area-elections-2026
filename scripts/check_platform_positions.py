#!/usr/bin/env python3
"""Publication guards for reviewed campaign platform positions (schema 1.20)."""
from copy import deepcopy
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
STATUSES = {'positions_found', 'no_positions_found', 'unavailable', 'no_website'}
TOPICS = ['Housing', 'Homelessness', 'Criminal justice & public safety', 'Immigration', 'Israel / Palestine',
          'International affairs', 'Education', 'Parental rights in schools', 'Environment & climate', 'Healthcare',
          'Economy & cost of living', 'Jobs & labor', 'Transportation', 'Civil liberties, privacy & surveillance',
          'Government accountability & ethics', 'Other']
HASH = re.compile(r'^[0-9a-f]{64}$')


def check_date(value, label, errors):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        errors.append(label + ': platform positions need a full calendar checked_on date')


def validate_positions(candidate, platform, label, errors):
    if not isinstance(platform, dict):
        errors.append(label + ': platform positions must be an object')
        return
    status, pages = platform.get('status'), platform.get('pages')
    if status not in STATUSES:
        errors.append(label + ': invalid platform positions status')
    check_date(platform.get('checked_on'), label + ' platform positions', errors)
    if not isinstance(platform.get('scope_note'), str) or not platform['scope_note'].strip():
        errors.append(label + ': platform positions scope limitation is missing')
    if not isinstance(pages, list):
        errors.append(label + ': platform positions pages are missing')
        pages = []
    urls = []
    for page in pages:
        if (not isinstance(page, dict) or not isinstance(page.get('url'), str) or not page['url'].startswith('https://')
                or not isinstance(page.get('title'), str) or not isinstance(page.get('content_sha256'), str)
                or not HASH.fullmatch(page['content_sha256'])):
            errors.append(label + ': platform positions page needs HTTPS URL, title and content hash')
        elif page['url'] in urls:
            errors.append(label + ': duplicate platform positions page URL')
        else:
            urls.append(page['url'])
    points = platform.get('points')
    if not isinstance(points, list):
        errors.append(label + ': platform positions points must be an array')
        points = []
    seen_quotes = set()
    for point in points:
        if not isinstance(point, dict):
            errors.append(label + ': malformed platform position point')
            continue
        if point.get('topic') not in TOPICS:
            errors.append(label + ': platform position topic is outside the fixed vocabulary')
        summary, quote = point.get('summary'), point.get('quote')
        if not isinstance(summary, str) or not (10 <= len(summary.strip()) <= 400):
            errors.append(label + ': platform position summary must be a faithful 10-400 character statement')
        if not isinstance(quote, str) or not (8 <= len(quote.strip()) <= 320):
            errors.append(label + ': platform position needs an exact quote of 8-320 characters')
        elif quote in seen_quotes:
            errors.append(label + ': duplicate platform position quote')
        else:
            seen_quotes.add(quote)
        if point.get('source_url') not in urls:
            errors.append(label + ': platform position source is not among captured pages')
    if status == 'positions_found' and (not points or not pages):
        errors.append(label + ': positions found requires at least one point and one captured page')
    if status != 'positions_found' and points:
        errors.append(label + ': only a positions-found result may publish position points')
    if status == 'no_positions_found' and not pages:
        errors.append(label + ': no-positions finding needs successfully captured pages')
    if status == 'no_website' and (pages or points or candidate.get('campaign_url')):
        errors.append(label + ': no-website finding conflicts with an existing campaign URL, pages or points')


def check_platform_positions(data):
    """Return publication consistency errors for the platform positions layer."""
    errors = []
    for position in data.get('positions', []):
        for roster in ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates'):
            for candidate in position.get(roster) or []:
                if not isinstance(candidate, dict) or 'platform_positions' not in candidate:
                    continue
                label = str(position.get('id')) + ' / ' + str(candidate.get('name'))
                validate_positions(candidate, candidate['platform_positions'], label, errors)
    return errors


def main():
    data = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())
    errors = check_platform_positions(data)
    if errors:
        raise SystemExit('Platform positions check failed:\n' + '\n'.join(errors[:40]))
    covered = sum(bool(c.get('platform_positions')) for p in data['positions'] for c in p.get('candidates') or [])
    with_points = sum(1 for p in data['positions'] for c in p.get('candidates') or []
                      if (c.get('platform_positions') or {}).get('status') == 'positions_found')
    print(json.dumps({'checked': True, 'printed_candidates_with_platform_positions': covered,
                      'candidates_with_published_points': with_points}))


class PlatformPositionsGuardTests(unittest.TestCase):
    def candidate(self, **platform):
        base = {'status': 'positions_found', 'checked_on': '2026-10-16', 'scope_note': 'Bounded website check.',
                'pages': [{'url': 'https://campaign.example.org/issues', 'title': 'Issues', 'content_sha256': 'a' * 64}],
                'points': [{'topic': 'Housing', 'summary': 'The campaign commits to building more affordable housing units.',
                            'quote': 'build more affordable housing units', 'source_url': 'https://campaign.example.org/issues'}]}
        base.update(platform)
        return {'name': 'Example Candidate', 'campaign_url': 'https://campaign.example.org/', 'platform_positions': base}

    def data(self, candidate):
        return {'positions': [{'id': 'CA2026-001', 'candidates': [candidate]}]}

    def test_valid_record_passes(self):
        self.assertEqual(check_platform_positions(self.data(self.candidate())), [])

    def test_off_vocabulary_topic_rejected(self):
        candidate = self.candidate()
        candidate['platform_positions']['points'][0]['topic'] = 'Vibes'
        self.assertTrue(any('vocabulary' in e for e in check_platform_positions(self.data(candidate))))

    def test_point_source_must_be_a_captured_page(self):
        candidate = self.candidate()
        candidate['platform_positions']['points'][0]['source_url'] = 'https://elsewhere.example.org/x'
        self.assertTrue(any('not among captured pages' in e for e in check_platform_positions(self.data(candidate))))

    def test_silence_cannot_carry_points_and_positions_found_needs_one(self):
        silence = self.candidate(status='no_positions_found', points=[])
        self.assertEqual(check_platform_positions(self.data(silence)), [])
        silence['platform_positions']['points'] = deepcopy(self.candidate()['platform_positions']['points'])
        self.assertTrue(any('only a positions-found result' in e for e in check_platform_positions(self.data(silence))))
        empty = self.candidate(points=[])
        self.assertTrue(any('positions found requires' in e for e in check_platform_positions(self.data(empty))))

    def test_no_website_conflicts_with_url_pages_or_points(self):
        candidate = self.candidate(status='no_website', pages=[], points=[])
        self.assertTrue(any('conflicts' in e for e in check_platform_positions(self.data(candidate))))
        candidate.pop('campaign_url')
        self.assertEqual(check_platform_positions(self.data(candidate)), [])

    def test_duplicate_quote_rejected(self):
        candidate = self.candidate()
        candidate['platform_positions']['points'].append(deepcopy(candidate['platform_positions']['points'][0]))
        self.assertTrue(any('Duplicate' in e or 'duplicate' in e for e in check_platform_positions(self.data(candidate))))


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PlatformPositionsGuardTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    main()
