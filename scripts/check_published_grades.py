"""Verify public grades against immutable Jev inputs, outputs and exact candidacies."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from ballotpedia_endorsements import digest
from publish_jev_grades import ROOT, DATASET, FIELDS, ROSTERS, attach, projection


def check(data):
    cfg=data['pro_palestine_grading'];path=(ROOT/cfg['archive_path']).resolve()
    if not path.is_relative_to(ROOT/'research/gaza-grading'):
        raise ValueError('Archive path outside the grading registry')
    if digest(path.read_bytes()) != cfg['archive_sha256']:
        raise ValueError('Changed published archive')
    archive=json.loads(path.read_text())
    expected=attach(data,archive,cfg['archive_path'],cfg['archive_sha256'])
    if data != expected:
        raise ValueError('Published projection differs from exact saved evaluation')
    preferred=json.loads((ROOT/cfg['preferred_criteria_path']).read_text())
    if preferred != archive['preferred_criteria']:
        raise ValueError('Preferred rubric differs from publication snapshot')
    return archive


class PublicationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATASET.read_text());cls.archive=check(cls.data)

    def test_exact_projection_and_idempotence(self):
        cfg=self.data['pro_palestine_grading']
        self.assertEqual(attach(self.data,self.archive,cfg['archive_path'],cfg['archive_sha256']),self.data)
        self.assertEqual(len(self.archive['rows']),1296)

    def test_latest_fiona_and_smiley_scores_remain_exact(self):
        people={c['name']:c for p in self.data['positions'] for c in p.get('candidates') or []}
        for name in ['Fiona Ma','Charles A. Smiley']:
            row=next(r for r in self.archive['rows'] if r['candidate']==name)
            self.assertEqual(people[name]['pro_palestine_score'],row['response']['answers']['pro_palestine_score']['score'])
            self.assertEqual(people[name]['pro_palestine_score_grade'],projection(row,self.archive['score_grade_mapping'],self.archive['id'])['pro_palestine_score_grade'])

    def test_changed_grade_score_or_confidence_is_rejected(self):
        for field,value in [('pro_palestine_score',5.001),('pro_palestine_score_grade','invalid')]:
            d=deepcopy(self.data);c=next(c for p in d['positions'] for c in p.get('candidates') or [] if c['name']=='Fiona Ma');c[field]=value
            with self.assertRaises(ValueError):check(d)

    def test_wrong_person_roster_or_changed_request_never_attaches(self):
        cfg=self.data['pro_palestine_grading']
        for change in ('candidate','roster','request'):
            a=deepcopy(self.archive);r=a['rows'][0]
            if change=='candidate':r['candidate']='Someone else'
            elif change=='roster':r['roster']='qualified_write_in_candidates'
            else:r['request']['state']['candidate']='Someone else'
            with self.assertRaises(ValueError):attach(self.data,a,cfg['archive_path'],cfg['archive_sha256'])

    def test_one_exact_rubric_and_raw_provider_responses_are_not_edited(self):
        before=deepcopy(self.archive);mapping=self.archive['score_grade_mapping'];variants=set()
        for r in self.archive['rows']:
            p=projection(r,mapping,self.archive['id']);variants.add(p['pro_palestine_evaluation']['questions_sha256'])
            self.assertNotIn('pro_palestine_score_grade',r['response']['answers'])
        self.assertEqual(len(variants),1);self.assertEqual(before,self.archive)

    def test_mixed_prompt_is_rejected_before_publication(self):
        a=deepcopy(self.archive);a['rows'][0]['request']['questions']['evidence_score']['instructions']='Other rubric'
        cfg=self.data['pro_palestine_grading']
        with self.assertRaisesRegex(ValueError,'exact preferred'):
            attach(self.data,a,cfg['archive_path'],cfg['archive_sha256'])

    def test_publication_never_becomes_an_input_for_future_grading(self):
        from serve_jev_playground import playground_state
        p=next(p for p in self.data['positions'] if any(c['name']=='Fiona Ma' for c in p.get('candidates') or []))
        c=next(c for c in p['candidates'] if c['name']=='Fiona Ma');unpublished=deepcopy(c)
        for key in FIELDS:unpublished.pop(key)
        self.assertEqual(playground_state(p,c,self.data),playground_state(p,unpublished,self.data))

    def test_duplicate_and_removed_scores_fail(self):
        cfg=self.data['pro_palestine_grading'];a=deepcopy(self.archive);a['rows'].append(a['rows'][0])
        with self.assertRaises(ValueError):attach(self.data,a,cfg['archive_path'],cfg['archive_sha256'])
        d=deepcopy(self.data);c=next(c for p in d['positions'] for c in p.get('candidates') or [] if 'pro_palestine_score' in c);c.pop('pro_palestine_score')
        with self.assertRaises(ValueError):check(d)


if __name__=='__main__':unittest.main()
