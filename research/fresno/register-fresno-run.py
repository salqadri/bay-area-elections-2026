#!/usr/bin/env python3
"""Register saved Fresno results without provider calls or invented future times.

The reconstructed batch envelope uses the last saved completion time. Individual
request/response payloads and completion dates remain exact. Existing outputs
are immutable; select new paths when registering another batch.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from grade_gaza import dump, digest, validate_questions, validate_response


def make_run(fresh, boot, questions):
    validate_questions(questions)
    rows=[]
    for tid in sorted(fresh):
        row=fresh[tid]
        if row['id'] != tid or row.get('status') != 'complete' or row['request']['questions'] != questions:
            raise ValueError('Candidate or question identity drift')
        if digest(dump(row['request']).encode()) != row['request_sha256']:
            raise ValueError('Saved request hash drift')
        validate_response(questions,row['response'])
        if not row.get('finished_at'):raise ValueError('Missing actual candidate completion date')
        rows.append(deepcopy(row))
    if not rows:raise ValueError('Cannot register an empty batch')
    last=max(datetime.fromisoformat(r['finished_at'].replace('Z','+00:00')) for r in rows)
    if last.tzinfo is None:raise ValueError('Completion dates require a timezone')
    stamp=last.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_id=stamp+'-'+digest(dump(rows).encode())[:8]
    return {'format':'jev-playground-run/v1','id':run_id,'created_at':last.isoformat(),
            'finished_at':last.isoformat(),'model':'jev-latest','questions':questions,
            'scope':'source-refresh','dataset_sha256':boot['latest']['dataset_sha256'],
            'state_version':boot['latest']['state_version'],'races':boot['latest']['races'],
            'rows':rows,'status':'complete','revision':len(rows),'completed':len(rows),'errors':0,
            'time_basis':'Review envelope uses the last saved result completion time; an exact execution start time is not available. Original per-candidate completion dates, requests and responses are unchanged.'}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--input',type=Path,default=ROOT/'.research/jev-playground-fresno/done-ids.json')
    cli.add_argument('--bootstrap',type=Path,default=ROOT/'.research/jev-playground-fresno/bootstrap-fresno.json')
    cli.add_argument('--output',type=Path,default=ROOT/'research/gaza-grading/fresno-county-2026-11-03/reviewed-run.json')
    args=cli.parse_args()
    if args.output.exists():raise SystemExit('Preserve the existing run; use a new output path')
    questions=json.loads((ROOT/'research/gaza-grading/criteria-pro-palestine-v11.json').read_text())['questions']
    run=make_run(json.loads(args.input.read_text()),json.loads(args.bootstrap.read_text()),questions)
    manifest_path=ROOT/'research/gaza-grading/playground-review-2026-10-30/manifest.json'
    manifest=json.loads(manifest_path.read_text())
    path=str(args.output.resolve().relative_to(ROOT))
    if any(e['path']==path or e['run_id']==run['id'] for e in manifest['runs']):
        raise SystemExit('Manifest already registers this run')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(run,ensure_ascii=False,indent=1)+'\n')
    manifest['runs'].append({'path':path,'run_id':run['id'],'sha256':digest(args.output.read_bytes()),'candidates':len(run['rows'])})
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Registered',run['id'],len(run['rows']),'saved results')


if __name__=='__main__':main()
