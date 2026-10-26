"""Verify every published grade explanation against its frozen archive entry."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from ballotpedia_endorsements import digest, dump
from attach_grade_explanations import EXPLANATION_FIELD, ROOT, DATASET, validate_summary
from publish_jev_grades import ROSTERS


def check(data):
    cfg = data['pro_palestine_grading']['explanations']
    path = (ROOT / cfg['archive_path']).resolve()
    if not path.is_relative_to(ROOT / 'research/gaza-grading'):
        raise ValueError('Explanations archive outside the grading registry')
    archive = json.loads(path.read_text())
    if digest(dump(archive).encode()) != cfg['archive_sha256']:
        raise ValueError('Changed published explanations archive')
    queue = json.loads((ROOT / archive['source_queue_path']).read_text())
    grades = json.loads((ROOT / 'research/gaza-grading/published-2026-10-26.json').read_text())
    rows = {r['id']: r for r in grades['rows']}
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
        if 'explanations' not in cls.data['pro_palestine_grading']:
            raise unittest.SkipTest('No explanations layer published yet')
        cls.archive = check(cls.data)

    def test_scores_and_raw_evaluations_are_untouched(self):
        grades = json.loads((ROOT / 'research/gaza-grading/published-2026-10-26.json').read_text())
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

    def test_na_explanations_state_insufficient_evidence(self):
        for e in self.archive['entries']:
            if e['grade'] == 'N/A':
                self.assertRegex(e['summary'], r'(?i)insufficient|below.{0,30}0\.10|not enough evidence')


if __name__ == '__main__':
    unittest.main()
