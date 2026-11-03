#!/usr/bin/env python3
"""Attach a registered Fresno run, preserving prior archives and recommendations.

No model calls. Existing output archives cannot be overwritten. Register the
saved batch first, then use a new publication and earlier-summary output path.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from grade_gaza import digest,dump,validate_response
from publish_jev_grades import attach,DATASET
from build_recommendations import extend_county_plan,PLAN


def build_archive(final,run,criteria,publication_id,criteria_path):
    rows=deepcopy(final['rows'])
    have={r['id']for r in rows}
    archive=deepcopy(final)
    sha=digest(dump(criteria['questions']).encode())
    if not any(v['questions_sha256']==sha for v in archive['question_variants']):
        archive['question_variants'].append({'criteria_path':criteria_path,'criteria':criteria,'questions_sha256':sha})
    for original in run['rows']:
        if original['id']in have:raise ValueError('Fresno run would replace an existing candidacy')
        if original['status']!='complete' or original['request']['questions']!=criteria['questions']:
            raise ValueError('Incomplete result or question drift')
        if digest(dump(original['request']).encode())!=original['request_sha256']:
            raise ValueError('Request hash mismatch')
        validate_response(criteria['questions'],original['response'])
        row=deepcopy(original)
        row['evaluation']={k:run[k]for k in ('dataset_sha256','state_version','model')}
        row['evaluation']['run_id']=run['id']
        rows.append(row);have.add(row['id'])
        archive['candidate_question_variants'][row['id']]=sha
    archive.update(id=publication_id,published_on=final['published_on'],rows=rows,
                   preferred_criteria=criteria,preferred_criteria_path=criteria_path)
    return archive


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--run',type=Path,default=ROOT/'research/gaza-grading/fresno-county-2026-11-03/reviewed-run.json')
    cli.add_argument('--output',type=Path,default=ROOT/'research/gaza-grading/published-2026-11-03-fresno-reviewed.json')
    cli.add_argument('--earlier-output',type=Path,default=ROOT/'research/gaza-grading/earlier-summaries-2026-11-03-fresno.json')
    cli.add_argument('--publication-id',default='jev-2026-11-03-fresno-reviewed')
    args=cli.parse_args()
    args.run=args.run.resolve();args.output=args.output.resolve();args.earlier_output=args.earlier_output.resolve()
    for path in (args.output,args.earlier_output):
        if path.exists():raise SystemExit('Preserve existing archive: '+str(path))
        if not path.resolve().is_relative_to(ROOT/'research/gaza-grading'):raise SystemExit('Store archives under research/gaza-grading')
    data=json.loads(DATASET.read_text());final=json.loads((ROOT/'research/gaza-grading/published-2026-11-03-final.json').read_text())
    path='research/gaza-grading/criteria-pro-palestine-v11.json';criteria=json.loads((ROOT/path).read_text())
    archive=build_archive(final,json.loads(args.run.read_text()),criteria,args.publication_id,path)
    raw=(json.dumps(archive,ensure_ascii=False,indent=1)+'\n').encode()
    proposed=attach(data,archive,str(args.output.relative_to(ROOT)),digest(raw))
    earlier=None
    if data['pro_palestine_grading'].get('previous_explanations'):
        earlier=json.loads((ROOT/data['pro_palestine_grading']['previous_explanations']['archive_path']).read_text())
        earlier['current_publication_id']=archive['id']
        earlier_raw=(json.dumps(earlier,ensure_ascii=False,indent=2)+'\n').encode()
        proposed['pro_palestine_grading']['previous_explanations']={'archive_path':str(args.earlier_output.relative_to(ROOT)),'archive_sha256':digest(earlier_raw)}
    added=json.loads((ROOT/'research/fresno/import-manifest.json').read_text())['added_positions']
    plan=extend_county_plan(json.loads(PLAN.read_text()),proposed,added)
    args.output.write_bytes(raw)
    if earlier:args.earlier_output.write_bytes(earlier_raw)
    old_data,old_plan=DATASET.read_bytes(),PLAN.read_bytes()
    try:
        DATASET.write_text(json.dumps(proposed,ensure_ascii=False,indent=1)+'\n')
        PLAN.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
    except BaseException:
        DATASET.write_bytes(old_data);PLAN.write_bytes(old_plan);raise
    print('Attached',len(archive['rows']),'exact evaluations; prior choices/prose retained')


if __name__=='__main__':main()
