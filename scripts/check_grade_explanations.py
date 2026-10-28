"""Verify every published grade explanation against its frozen archive entry."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from ballotpedia_endorsements import digest, dump
from attach_grade_explanations import EXPLANATION_FIELD, ROOT, DATASET, validate_summary, validate_summary_refreshes, validate_editorial_review
from publish_jev_grades import ROSTERS


def check(data):
    if 'explanations' not in data['pro_palestine_grading']:
        if any(c.get(EXPLANATION_FIELD) for p in data['positions'] for roster in ROSTERS for c in p.get(roster) or []):
            raise ValueError('Orphan explanations without a current archive binding')
        return None
    cfg = data['pro_palestine_grading']['explanations']
    path = (ROOT / cfg['archive_path']).resolve()
    if not path.is_relative_to(ROOT / 'research/gaza-grading'):
        raise ValueError('Explanations archive outside the grading registry')
    archive = json.loads(path.read_text())
    if digest(dump(archive).encode()) != cfg['archive_sha256']:
        raise ValueError('Changed published explanations archive')
    queue = json.loads((ROOT / archive['source_queue_path']).read_text())
    grades = json.loads((ROOT / data['pro_palestine_grading']['archive_path']).read_text())
    rows = {r['id']: r for r in grades['rows']}
    validate_summary_refreshes(archive, rows)
    validate_editorial_review(archive)
    if queue['publication_id'] != cfg['publication_id'] or archive['publication_id'] != cfg['publication_id']:
        raise ValueError('Explanations publication id mismatch')
    if len(archive['entries']) != len(queue['candidates']):
        raise ValueError('Explanations must cover every queued candidacy')
    targets = {}
    for p in data['positions']:
        for roster in ROSTERS:
            for c in p.get(roster) or []:
                if 'pro_palestine_evaluation' in c:
                    targets[c['pro_palestine_evaluation']['candidate_id']] = c
    seen = set()
    for e in archive['entries']:
        row = rows[e['candidate_id']]
        errors = validate_summary({'candidate_id': e['candidate_id'], 'request_sha256': e['request_sha256'],
                                   'publication_id': archive['publication_id'], 'summary': e['summary'],
                                   'model': e['model']}, row, e['grade'], archive['publication_id'])
        if errors:
            raise ValueError('%s %s: %s' % (e['candidate_id'], e['candidate'], '; '.join(errors)))
        c = targets.get(e['candidate_id'])
        expected = {'publication_id': archive['publication_id'], 'candidate_id': e['candidate_id'],
                    'request_sha256': e['request_sha256'], 'summary': e['summary'], 'model': e['model']}
        if c is None or c.get(EXPLANATION_FIELD) != expected:
            raise ValueError('Published explanation differs from the frozen archive: ' + e['candidate'])
        seen.add(e['candidate_id'])
    if seen != set(targets):
        raise ValueError('Missing explanations for %d published evaluations' % (len(set(targets) - seen)))
    return archive


class ExplanationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATASET.read_text())
        cls.archive = check(cls.data)
        if cls.archive is None:
            raise unittest.SkipTest('No explanations layer published yet')

    def test_scores_and_raw_evaluations_are_untouched(self):
        grades = json.loads((ROOT / self.data['pro_palestine_grading']['archive_path']).read_text())
        rows = {r['id']: r for r in grades['rows']}
        entries = {e['candidate_id']: e for e in self.archive['entries']}
        for p in self.data['positions']:
            for roster in ROSTERS:
                for c in p.get(roster) or []:
                    meta = c.get('pro_palestine_evaluation')
                    if not meta:
                        continue
                    row = rows[meta['candidate_id']]
                    self.assertEqual(c['pro_palestine_score'], row['response']['answers']['pro_palestine_score']['score'])
                    self.assertIn(entries[meta['candidate_id']]['summary'], c[EXPLANATION_FIELD]['summary'])

    def test_manual_edit_manifest_and_padding_guard(self):
        validate_editorial_review(self.archive)
        e = next(e for e in self.archive['entries'] if e['grade'] != 'N/A')
        fixture = {'candidate_id': e['candidate_id'], 'request_sha256': e['request_sha256'],
                   'publication_id': self.archive['publication_id'], 'model': e['model'],
                   'summary': 'The supplied record is too thin to characterize the full stance of this candidate.'}
        row = {'id': e['candidate_id'], 'request_sha256': e['request_sha256']}
        self.assertTrue(any('disclaimer padding' in error for error in validate_summary(fixture, row, e['grade'], self.archive['publication_id'])))
        fixture['summary'] = 'CAIR Action endorses this candidate.'
        self.assertEqual(validate_summary(fixture, row, e['grade'], self.archive['publication_id']), [])
        bad = deepcopy(self.archive)
        entry = next(e for e in bad['entries'] if e['grade'] != 'N/A')
        entry['summary'] += ' Unreviewed change.'
        with self.assertRaises(ValueError):
            validate_editorial_review(bad)

    def test_changed_or_missing_explanation_fails(self):
        for change in ('edit', 'drop'):
            d = deepcopy(self.data)
            c = next(c for p in d['positions'] for roster in ROSTERS for c in (p.get(roster) or [])
                     if EXPLANATION_FIELD in c)
            if change == 'edit':
                c[EXPLANATION_FIELD]['summary'] = 'Rewritten without the archive. ' + c[EXPLANATION_FIELD]['summary']
            else:
                c.pop(EXPLANATION_FIELD)
            with self.assertRaises(ValueError):
                check(d)

    def test_refreshed_summary_cannot_change_input_output_or_score_binding(self):
        grades = json.loads((ROOT / self.data['pro_palestine_grading']['archive_path']).read_text())
        rows = {r['id']: r for r in grades['rows']}
        for candidate_id, refresh in self.archive.get('summary_refreshes', {}).items():
            for key in ('input_sha256', 'output_sha256'):
                bad = deepcopy(self.archive); bad['summary_refreshes'][candidate_id][key] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'Changed summary refresh'):
                    validate_summary_refreshes(bad, rows)
            bad = deepcopy(self.archive)
            next(e for e in bad['entries'] if e['candidate_id'] == candidate_id)['summary'] = 'An unrecorded replacement.'
            with self.assertRaisesRegex(ValueError, 'recorded input/output'):
                validate_summary_refreshes(bad, rows)

    def test_na_explanations_state_insufficient_evidence(self):
        for e in self.archive['entries']:
            if e['grade'] == 'N/A':
                self.assertRegex(e['summary'], r'(?i)insufficient|below.{0,30}0\.10|not enough (?:evidence|of this)|could ?n.t find|no (?:statements|record|mention)|canno?t judge|no clear position|too little to judge')


if __name__ == '__main__':
    unittest.main()
