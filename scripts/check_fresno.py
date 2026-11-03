"""County expansion, provenance and scope regressions. No network/model calls."""
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import build_recommendations as rec
from serve_jev_playground import RunManager
from restore_jev_playground import restore,load_review
from score_grade import row_grade

ROOT=Path(__file__).resolve().parent.parent
FRESNO=ROOT/'research/fresno'
sys.path.insert(0,str(FRESNO))
import parse_proof
import apply_fresno


def load_module(name,file):
    spec=importlib.util.spec_from_file_location(name,FRESNO/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class FresnoChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(rec.DATA.read_text())
        cls.manifest=json.loads((FRESNO/'import-manifest.json').read_text())
        cls.baseline=json.loads((FRESNO/'review-2026-11-03/baseline-recommendations.json').read_text())
        cls.plan=json.loads(rec.PLAN.read_text())

    def test_source_parses_reproduce_every_qualified_roster(self):
        for text,parsed,on,count in [('proof.txt','proof-parsed.json',True,106),('not-on-ballot.txt','not-on-ballot-parsed.json',False,114)]:
            actual=parse_proof.parse((FRESNO/text).read_text())
            self.assertEqual(actual,json.loads((FRESNO/parsed).read_text()))
            parse_proof.validate(actual,on_ballot=on)
            self.assertEqual(len(actual),count)

    def test_truncated_parser_input_cannot_overwrite_output_even_under_optimization(self):
        source='NONPARTISAN OFFICES CITY CITY OF FRESNO Council Member\n5000 Fresno City Council\n42 City of Fresno 1 2 2 ON BALLOT\nDANA JONES\nTeacher\nQualified Date: 01/01/2026\n'
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder);(path/'input.txt').write_text(source);(path/'output.json').write_text('unchanged')
            result=subprocess.run([sys.executable,'-O',str(FRESNO/'parse_proof.py'),'--input',str(path/'input.txt'),'--output',str(path/'output.json')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('qualified counts',result.stderr)
            self.assertEqual((path/'output.json').read_text(),'unchanged')

    def test_incumbents_match_middle_names_and_initials_without_ambiguity(self):
        for printed,inc in [('ARLAN L. HARRELL','Arlan L Harrell Appointed to Vacancy'),('MICHELE CANTWELL-COPHER','Michele Enid Cantwell-Copher Elected')]:
            candidate={'name':printed,'incumbent_flag':False}
            self.assertTrue(apply_fresno.is_incumbent(candidate,{'incumbents':[inc],'candidates':[candidate]}))
        candidates=[{'name':name,'incumbent_flag':False}for name in ['John A. Smith','John B. Smith']]
        self.assertFalse(apply_fresno.is_incumbent(candidates[0],{'incumbents':['John Smith Elected'],'candidates':candidates}))
        for item in json.loads((FRESNO/'review-2026-11-03/incumbent-corrections.json').read_text()):
            pos=next(p for p in self.data['positions']if p['id']==item['position_id'])
            self.assertTrue(next(c for field in ['candidates','filed_candidates_not_confirmed_on_ballot']for c in pos.get(field)or[]if c['name']==item['candidate'])['incumbent'])

    def test_all_confirmed_contests_have_plan_rows_including_writein_only_huron(self):
        plan={r['position_id']:r for r in self.plan['races']}
        self.assertTrue({p['id']for p in self.data['positions']if p['ballot_status']=='confirmed'}<=set(plan))
        row=plan['CA2026-480'];self.assertEqual(row['roster'],[])
        self.assertIsNone(row['recommended']);self.assertEqual(row['category'],rec.CAT_NO_INFO)

    def test_expansion_preserves_choices_and_prose_without_implicit_regeneration(self):
        replay=rec.extend_county_plan(self.baseline,self.data,self.manifest['added_positions'])
        current={r['position_id']:r for r in replay['races']}
        for old in self.baseline['races']:
            new=current[old['position_id']]
            for field in ('recommended','summary','recommend_reason_text','recommend_reason','release_choice_review','jev'):
                self.assertEqual(old.get(field),new.get(field),(old['position_id'],field))
        # An explicit owner-approved refresh is a new maintained plan. County
        # extension must preserve it too, rather than restore an older baseline.
        accepted=rec.extend_county_plan(self.plan,self.data,[])
        self.assertEqual(accepted['races'],self.plan['races'])
        changed=deepcopy(self.data)
        person=next(c for p in changed['positions']if p['id']=='CA2026-047'for c in p['candidates']if c['name']=='Tracy Jensen')
        person['pro_palestine_score_grade']='F'
        with self.assertRaisesRegex(ValueError,'changes existing'):rec.extend_county_plan(self.baseline,changed,self.manifest['added_positions'])

    def test_regular_revalidation_recognizes_owner_approved_release_choices(self):
        historical=rec.extend_county_plan(self.baseline,self.data,self.manifest['added_positions'])
        for plan in (historical,self.plan):
            updated,audit=rec.revalidate_plan(plan,self.data)
            self.assertEqual(audit['changed_choices'],[])
            self.assertEqual([r.get('recommended')for r in updated['races']],[r.get('recommended')for r in plan['races']])

    def test_approved_refresh_and_manual_correction_keep_provider_output_auditable(self):
        receipt=json.loads((FRESNO/'review-2026-11-03/review-receipt.json').read_text())['owner_approved_refresh']
        raw=(ROOT/receipt['path']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),receipt['sha256'])
        review=json.loads(raw);current={r['position_id']:r for r in self.plan['races']}
        self.assertEqual(sum(bool(r.get('recommended'))for r in self.plan['races']),review['selected_races'])
        for entry in review['approved_existing_races']:
            row=current[entry['position_id']]
            serialized=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            self.assertEqual(hashlib.sha256(serialized).hexdigest(),entry['row_sha256'])
        cache=[json.loads(line)for line in rec.REASON_CACHE.read_text().splitlines()if line.strip()]
        edited=current['CA2026-003']['summary'];meta=edited['editorial_correction']
        self.assertIn('In Congress, she voted No on defunding universities',edited['text'])
        self.assertNotIn('As a state senator she voted No',edited['text'])
        original=next(row for row in cache if row['position_id']=='CA2026-003'
                      and hashlib.sha256(row['text'].encode()).hexdigest()==meta['original_text_sha256'])
        self.assertEqual(edited['text'],original['text'].replace(meta['replacements'][0]['before'],meta['replacements'][0]['after']))
        self.assertEqual(edited['prompt_sha256'],original['prompt_sha256'])
        self.assertIn('factual editorial correction',edited['model'])
        self.assertEqual([row for row in cache if row['position_id']=='CA2026-003'][-1],edited)

    def test_archives_keep_old_evaluations_and_new_raw_answers_exact(self):
        receipt=json.loads((FRESNO/'review-2026-11-03/review-receipt.json').read_text())
        for file,sha in receipt['immutable_baselines'].items():self.assertEqual(hashlib.sha256((ROOT/file).read_bytes()).hexdigest(),sha)
        old=json.loads((ROOT/'research/gaza-grading/published-2026-11-03-final.json').read_text())
        current=json.loads((ROOT/self.data['pro_palestine_grading']['archive_path']).read_text());rows={r['id']:r for r in current['rows']}
        self.assertTrue(all(rows[r['id']]==r for r in old['rows']))
        source=json.loads((ROOT/'research/gaza-grading/fresno-county-2026-11-03/run.json').read_text())
        for row in source['rows']:
            for key in ('request','request_sha256','response','finished_at'):self.assertEqual(rows[row['id']][key],row[key])
            self.assertEqual(row_grade(rows[row['id']],current['score_grade_mapping']),'N/A')

    def test_reviewed_batch_history_can_be_opened_and_has_no_future_placeholder(self):
        entry=next(e for e in load_review()[0]['runs']if '/fresno-county-'in e['path'])
        run=json.loads((ROOT/entry['path']).read_text())
        self.assertRegex(run['id'],r'^\d{8}T\d{6}Z-[a-f0-9]{8}$')
        last=max(datetime.fromisoformat(r['finished_at'].replace('Z','+00:00'))for r in run['rows'])
        self.assertEqual(datetime.fromisoformat(run['created_at'].replace('Z','+00:00')),last)
        source=json.loads((ROOT/'research/gaza-grading/fresno-county-2026-11-03/run.json').read_text())
        registration=load_module('fresno_registration_replay','register-fresno-run.py')
        self.assertEqual(registration.make_run({r['id']:r for r in source['rows']},{'latest':source},source['questions']),run)
        with tempfile.TemporaryDirectory()as folder:
            restore(work=folder);manager=RunManager(work=folder)
            self.assertEqual(manager.get(run['id'])['completed'],222)

    def test_grading_scripts_import_without_a_machine_specific_secret_file(self):
        load_module('fresno_grading','jev-fresno-run.py')
        load_module('fresno_registration','register-fresno-run.py')
        load_module('fresno_publication','merge-publish-fresno.py')


if __name__=='__main__':unittest.main()
