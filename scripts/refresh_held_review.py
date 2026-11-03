"""Refresh explanations and selections for an explicitly authorized source batch.

Consumes a complete exact Jev playground run and the portable review history.
Writes only to --work-dir; never changes canonical data, settings or publication.
Paid calls: existing Jev selection policy, Qwen summaries (parallelism 2), and a
factual legislative-consistency audit. Requests, attempts and outputs are kept.
Rerunning resumes successful hash-matching outputs; audit flags require review.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
import threading
import time
import urllib.request
from pathlib import Path

import build_recommendations as rec
import generate_grade_explanations as gen
import grade_gaza as g
from restore_jev_playground import load_review
from publish_jev_grades import projection, candidacy_id
from score_grade import row_grade
from summary_source_policy import policy_for_state
from audit_summary_alignment import request_for, MENTION

ROOT = Path(__file__).resolve().parent.parent
SAFE = ('\n\nWrite factual, descriptive research prose without appeals to a demographic audience, '
        'identity-based appeals or voting instructions. Explain the documented observations and saved assessment. '
        'Preserve substantive contrary evidence and state versus federal powers. Never treat an upload date as a statement date; '
        'when the statement date is unknown, omit the date from prose rather than explaining upload metadata. '
        'Do not list unrelated platform topics or say the platform is silent on the issue. '
        'Distinguish a stated intention from an actual action. Keep recommendation tiers exact: '
        'Ally, supported and Preferred are not automatically formal endorsements. No missing-record disclaimer padding. '
        'A recorded aligned No vote must never be called contrary or negative. '
        'Consider every supplied observation; cover all of them when an evidence audit is requested. Prose must accurately reflect the resulting record. '
        'Rubric descriptions are not independent factual evidence about bill text or candidate actions; '
        'do not turn them into facts absent from the supplied candidate record.')


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-file', type=Path, required=True)
    parser.add_argument('--scope-file', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--jev-key-file', type=Path, required=True)
    parser.add_argument('--lmstudio-url', default=gen.LMSTUDIO_URL)
    parser.add_argument('--additional-races', nargs='*', default=[], help='Explicit additional narrative-only contests; no candidate score calls.')
    parser.add_argument('--only-races', nargs='+', help='Skip candidate generation and refresh only these affected contest IDs.')
    parser.add_argument('--force-races', action='store_true', help='Archive selected existing race outputs before regenerating them.')
    args = parser.parse_args()
    work = args.work_dir; work.mkdir(parents=True, exist_ok=True)
    run = json.loads(args.run_file.read_text())
    scope = json.loads(args.scope_file.read_text())['candidates']
    assert run['status'] == 'complete' and not run['errors']
    assert {(c['position_id'], c['candidate']) for c in scope} == {(r['position_id'], r['candidate']) for r in run['rows']}
    manifest, mapping, old_runs = load_review()
    assert run['score_grade_mapping'] == mapping
    latest = {}
    for _, raw in old_runs:
        old_run = json.loads(raw)
        for original in old_run['rows']:
            row = deepcopy(original)
            row['evaluation'] = {k: old_run.get(k) for k in ('created_at', 'dataset_sha256', 'state_version', 'model')}
            row['evaluation']['run_id'] = old_run['id']
            latest[row['id']] = row
    baseline_path = work/'baseline-latest.json'
    if not baseline_path.exists():
        save(baseline_path, latest)
    baseline = json.loads(baseline_path.read_text())
    for original in run['rows']:
        row = deepcopy(original)
        assert g.digest(g.dump(row['request']).encode()) == row['request_sha256']
        g.validate_response(run['questions'], row['response'])
        row['evaluation'] = {k: run.get(k) for k in ('created_at', 'dataset_sha256', 'state_version', 'model')}
        row['evaluation']['run_id'] = run['id']
        latest[row['id']] = row
    data = json.loads(g.DATASET.read_text())
    assert g.digest(g.dump(data).encode()) == run['dataset_sha256'], 'Source dataset changed after the frozen scoring snapshot; review it before continuing.'
    source_sha = hashlib.sha256(g.DATASET.read_bytes()).hexdigest()
    save(work/'source-dataset.json', data)
    for position in data['positions']:
        for roster in ('candidates','filed_candidates_not_confirmed_on_ballot','qualified_write_in_candidates'):
            for person in position.get(roster) or []:
                cid = candidacy_id(position['id'], person['name'], roster)
                row = latest.get(cid)
                if row:
                    for field in ('pro_palestine_score','pro_palestine_score_grade','pro_palestine_evaluation','pro_palestine_explanation'):
                        person.pop(field, None)
                    person.update(projection(row, mapping, 'local-pr22-held-review'))
    save(work/'overlay-dataset.json', data)
    affected = {row['position_id'] for row in run['rows']} | set(args.additional_races)
    known_positions = {p['id'] for p in data['positions']}
    if not affected <= known_positions:raise ValueError('Unknown additional narrative contest')
    races = [r for r in rec.classify(data, json.loads(rec.OBS.read_text())) if r['position_id'] in affected]
    rec.JEV_KEY = args.jev_key_file.read_text().strip()
    rec.JEV_CACHE = work/'selection-decisions.jsonl'
    races = rec.jev_phase(races)
    plan = {'format':'held-source-refresh-plan/v1','status':'held_for_review','generated_at':stamp(),
            'source_run_id':run['id'],'source_dataset_sha256':source_sha,
            'additional_narrative_only_races':args.additional_races,'races':races}
    save(work/'selection-plan.json', plan)
    selected_races = races
    if args.only_races:
        known = {r['position_id'] for r in races}
        if not set(args.only_races) <= known:raise ValueError('--only-races must be within the frozen affected scope')
        selected_races = [r for r in races if r['position_id'] in args.only_races]
    if args.force_races:
        for race in selected_races:
            path = work/'race-results'/(race['position_id']+'.json')
            if path.exists():
                old = json.loads(path.read_text())
                suffix = old.get('generation_request_sha256') or hashlib.sha256(path.read_bytes()).hexdigest()
                backup = work/'superseded-race-results'/(race['position_id']+'-'+suffix+'.json')
                save(backup, old);path.unlink()
    rec.DATA = work/'overlay-dataset.json'
    bypos = {p['id']:p for p in data['positions']}
    state = {'started_at':stamp(),'status':'running','phase':'candidates','candidate_total':0 if args.only_races else sum(row_grade(r,mapping)!='N/A' for r in run['rows']),
             'race_total':sum(bool(r.get('recommended')) for r in selected_races),'candidate_completed':0,'race_completed':0,
             'candidate_failed':0,'race_failed':0,'active':{},'errors':[],'parallelism':2,'model':gen.LMSTUDIO_MODEL,'source_run_id':run['id']}
    lock = threading.RLock()
    def progress():
        state['updated_at'] = stamp();save(work/'status.json', state)
    def heartbeat():
        while True:
            time.sleep(30)
            with lock:
                if state['status'] != 'running':return
                progress()
    threading.Thread(target=heartbeat, daemon=True).start()
    def begin(kind, id_, label):
        with lock:
            state['active'][id_] = {'kind':kind,'label':label,'started_at':stamp()};progress()
    def finish(kind, id_, error=None):
        with lock:
            state['active'].pop(id_, None)
            state[kind+('_failed' if error else '_completed')] += 1
            if error:state['errors'].append({'kind':kind,'id':id_,'error':str(error)})
            progress()
    def call(prompt, kind, id_, validate):
        body = {'model':gen.LMSTUDIO_MODEL,'reasoning_effort':'medium','temperature':1,'max_tokens':12000,
                'messages':[{'role':'user','content':prompt}]}
        last = None
        previous_attempts = list((work/'calls'/kind/id_).glob('*.request.json'))
        first = max([int(p.name.split('.')[0]) for p in previous_attempts], default=0) + 1
        for attempt in range(first, first+3):
            prefix = work/'calls'/kind/id_/str(attempt)
            save(prefix.with_suffix('.request.json'),body)
            try:
                start = time.monotonic()
                req = urllib.request.Request(args.lmstudio_url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=900) as response:raw=json.load(response)
                save(prefix.with_suffix('.response.json'), raw)
                result = validate(raw['choices'][0]['message']['content'])
                receipt = {'model':raw.get('model'),'usage':raw.get('usage'),'elapsed_seconds':round(time.monotonic()-start,2),
                           'generation_request_sha256':rec.request_hash(body),'attempt':attempt}
                print('COMPLETE',kind,id_,receipt['elapsed_seconds'],flush=True)
                return result, receipt
            except Exception as error:
                last = str(error)
                save(prefix.with_suffix('.error.json'),{'error_type':type(error).__name__,'message':last})
                print('RETRY',kind,id_,attempt,last,flush=True)
                body['messages'][0]['content'] = prompt+'\n\nREPAIR: '+last+'. Preserve source facts and output only the required result.'
                time.sleep(2)
        raise RuntimeError(last)
    def candidate_job(original):
        row = latest[original['id']];id_ = row['id'];grade = row_grade(row,mapping)
        if grade == 'N/A':
            save(work/'not-applicable'/(id_+'.json'),{'candidate_id':id_,'candidate':row['candidate'],'request_sha256':row['request_sha256'],'grade':grade,'reason':'Saved evidence gate; no explanation attached.'})
            return
        begin('candidate',id_,row['candidate']);error=None
        try:
            prompt=gen.build_input(row,grade,gen.PROMPT_PATH.read_text())+SAFE
            path=work/'candidate-results'/(id_+'.json')
            def validate(text):
                value=gen.parse_json(text)
                error=gen.validate(value,row,grade,policy_for_state(row['request']['state'],row['position_id']),gen.summary_inventory(row))
                if error:raise ValueError(error)
                if len(value['summary'].split())>80:raise ValueError('Candidate summary must be at most 80 words (45–80 when substantive, shorter for sparse observations).')
                return value
            if path.exists():
                value=json.loads(path.read_text());assert value['source_prompt_sha256']==hashlib.sha256(prompt.encode()).hexdigest()
                validate(json.dumps(value));return
            result,receipt=call(prompt,'candidates',id_,validate)
            save(path,{'format':'held-grade-explanation/v1','status':'held_for_review','candidate_id':id_,'candidate':row['candidate'],
                       'position_id':row['position_id'],'request_sha256':row['request_sha256'],'grade':grade,'summary':result['summary'],
                       'evidence_audit':result['evidence_audit'],'model':gen.LMSTUDIO_MODEL,'source_prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                       'generated_at':stamp(),**receipt})
        except Exception as e:error=e
        finally:finish('candidate',id_,error)
    progress()
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(candidate_job,row) for row in ([] if args.only_races else run['rows'])]):future.result()
    def race_job(race):
        pid=race['position_id'];begin('race',pid,pid);error=None
        try:
            for person in rec.all_candidates(bypos[pid]):
                cid=person.get('pro_palestine_evaluation',{}).get('candidate_id')
                if cid in {r['id']for r in run['rows']} and person.get('pro_palestine_score_grade')in rec.GRADE_ORDER:
                    assert (work/'candidate-results'/(cid+'.json')).exists(),'Dependent candidate summary failed'
            rubric_context={c['name']:{'request_sha256':latest[c['pro_palestine_evaluation']['candidate_id']]['request_sha256'],'questions':latest[c['pro_palestine_evaluation']['candidate_id']]['request']['questions']}for c in rec.all_candidates(bypos[pid])if c.get('pro_palestine_evaluation')}
            prompt=rec.reason_prompt(race,bypos)+SAFE+'\nSCORING QUESTION CONTEXT PER CANDIDATE (rubric, not additional factual evidence):\n'+json.dumps(rubric_context,ensure_ascii=False)+'\nExplain the recorded comparison without calls to vote. 30–200 words. Do not fault state or local candidates for not casting congressional votes.'
            path=work/'race-results'/(pid+'.json')
            def validate(text):
                text=re.sub(r'\s+',' ',text).strip()
                errors=rec.out_of_policy_endorsers(race,bypos,text)
                if errors:raise ValueError('Remove these out-of-policy endorsement references: '+ '; '.join(errors) + '. Do not repeat these names; they are outside the permitted Palestine-relevant comparison.')
                if not 30<=len(text.split())<=200:raise ValueError('Race paragraph must be 30–200 words.')
                if re.search(r'supplied record|provided record|single data point|record is (?:thin|sparse)',text,re.I):raise ValueError('Remove missing-record disclaimer padding.')
                return text
            if path.exists():
                value=json.loads(path.read_text());assert value['source_prompt_sha256']==hashlib.sha256(prompt.encode()).hexdigest()
                validate(value['text']);return
            text,receipt=call(prompt,'races',pid,validate)
            bindings={c['pro_palestine_evaluation']['candidate_id']:c['pro_palestine_evaluation']['request_sha256'] for c in rec.all_candidates(bypos[pid]) if c.get('pro_palestine_evaluation')}
            save(path,{'format':'held-race-rationale/v1','status':'held_for_review','narrative_context_version':'exact-organization-boundaries-v2','position_id':pid,'recommended':race['recommended'],
                       'text':text,'words':len(text.split()),'model':gen.LMSTUDIO_MODEL,'source_prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                       'generated_at':stamp(),'source_candidate_request_sha256':bindings,**receipt})
        except Exception as e:error=e
        finally:finish('race',pid,error)
    state['phase']='races';progress()
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(race_job,r) for r in selected_races if r.get('recommended')]):future.result()
    state['status']='complete_with_errors' if state['errors'] else 'complete';state['finished_at']=stamp();progress()
    # Source audit is independent of letter scores; flags never silently rewrite text.
    audit_rows=[]
    for kind,field in (('candidate-results','summary'),('race-results','text')):
        for path in sorted((work/kind).glob('*.json')):
            item=json.loads(path.read_text());text=item[field]
            if not MENTION.search(text):continue
            people=[c for c in rec.all_candidates(bypos[item['position_id']]) if kind=='race-results' or c['name']==item['candidate']]
            records=[{'candidate':c['name'],**g.build_state(bypos[item['position_id']],c,data)}for c in people]
            if not any(r.get('congressional_gaza_actions')or r.get('antisemitism_education_policy_evidence')for r in records):continue
            audit_rows.append({'position_id':item['position_id'],'candidate':item.get('candidate'),'paragraph':text,'candidate_records':records,'output_path':str(path.relative_to(work))})
    def audit_one(row):
        response=g.jev_call(work/'alignment-audit',request_for(row),rec.JEV_KEY)
        return {**row,'audit':response['answers']['legislative_consistency']}
    results=[]
    with ThreadPoolExecutor(max_workers=3)as pool:
        for future in as_completed([pool.submit(audit_one,r)for r in audit_rows]):
            results.append(future.result());save(work/'alignment-audit.json',{'rows':results})
    print('FINISHED',json.dumps(state),flush=True)

if __name__=='__main__':main()
