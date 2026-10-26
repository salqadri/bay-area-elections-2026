"""Offline API, snapshot, validation, run isolation and local credential regressions."""
from copy import deepcopy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

import grade_gaza as g
import serve_jev_playground as p

QUESTIONS = {'verdict': {'type': 'choice', 'instructions': 'Example', 'criteria': {'A':'One','F':'Two'}},
             'rating': {'type':'score','criteria':['Low','High']}, 'claim': {'type':'noul'}}


def response(request):
    answers = {}
    for key, q in request['questions'].items():
        if q['type'] == 'choice':
            keys = list(q['criteria']); answers[key] = {'type':'choice','choice':keys[0],'confidence':0.12,
                'probabilities':{k:1.0/len(keys) for k in keys}}
        elif q['type'] == 'score':
            n=len(q['criteria']);answers[key]={'type':'score','score':0.,'confidence':0.,'legend':{str(i):v for i,v in enumerate(q['criteria'])},'probabilities':{str(i):float(i==0) for i in range(n)}}
        else:
            answers[key]={'type':'noul','noul':.47}
    return {'model':'jev-fixture','answers':answers,'usage':{'input_tokens':1,'output_tokens':1}}


def fixture():
    ps=[]
    for id_,district,name,category,status in [('CA-17','CD-17','Alice','U.S. House','confirmed'),('CA-1','CD-1','Bob','U.S. House','confirmed'),('TX-35','CD-35','Chris','U.S. House','confirmed'),('CA-9','CD-9','Excluded','U.S. House','excluded'),('CA-S','Statewide','Senator','U.S. Senate','confirmed')]:
        ps.append({'id':id_,'office_category':category,'office':'United States Representative','jurisdiction':'Congress',
            'district_or_seat':district,'ocd_division_id':'ocd-division/country:us/state:'+id_[:2].lower(),
            'ballot_status':status,'candidates':[{'name':name,'party':'D'}]})
    return {'election':{'publication_version':'2026-10-23.1'},'codes':{'party':{'D':'Democratic Party'}},'positions':ps}


def expanded_fixture():
    data=fixture();data['positions'][0]['counties']=['Alameda','Santa Clara']
    for id_,county,category,status,name in [('AL-local',['Alameda'],'Mayor','confirmed','Local Alex'),
            ('SC-local',['Santa Clara'],'School district','confirmed','Local Alex'),
            ('shared',['Alameda','Santa Clara'],'Statewide executive','confirmed','Governor'),
            ('outside',['San Mateo'],'Mayor','confirmed','Outside'),
            ('excluded-local',['Santa Clara'],'Mayor','excluded','Excluded local'),
            ('empty',['Santa Clara'],'Water district','confirmed',None)]:
        data['positions'].append({'id':id_,'counties':county,'government_level':'City or town',
            'office_category':category,'office':category,'jurisdiction':id_+' jurisdiction',
            'district_or_seat':'District 3','partisan':False,'ballot_status':status,
            'election_type':'general','candidates':[{'name':name,'incumbent':True}] if name else []})
    data['positions'][5]['qualified_write_in_candidates']=[{'name':'Local Write In'}]
    data['positions'][5]['filed_candidates_not_confirmed_on_ballot']=[{'name':'Local provisional'}]
    return data


def baseline(data):
    results=[];decisions={}
    for pos,c,roster in g.candidates(data,'house-all'):
        req={'model':g.MODEL,'state':g.build_state(pos,c,data),'questions':QUESTIONS};ref=g.digest(g.dump(req).encode())
        decisions[ref]={'request':req,'response':response(req)}
        results.append({'position_id':pos['id'],'candidate':c['name'],'party':c['party'],'roster':roster,'request_sha256':ref})
    return {'questions':QUESTIONS,'model':g.MODEL,'run_on':'2026-10-23T10:00:00+00:00','state_version':'house-evidence-v3-focused','dataset_sha256':g.digest(g.dump(data).encode()),'results':results,'decisions':decisions}


class ValidationChecks(unittest.TestCase):
    def test_questions_allow_renamed_added_score_choice_noul(self):
        self.assertEqual(g.validate_questions(QUESTIONS),QUESTIONS)
        self.assertEqual(g.validate_response(QUESTIONS,response({'questions':QUESTIONS}))['answers']['rating']['confidence'],0.)

    def test_invalid_questions_fail_before_model_call(self):
        for q in ([],{}, {'q':{'type':'box'}},{'q':{'type':'score','criteria':[]}},{'q':{'type':'choice','criteria':[]}}, {'q':{'type':'noul','criteria':{'maybe':'x'}}}):
            with self.assertRaises(ValueError):g.validate_questions(q)

    def test_missing_wrong_type_and_invalid_probability_answers_fail(self):
        for mutate in (lambda r:r['answers'].pop('rating'),lambda r:r['answers']['rating'].update(type='choice'),lambda r:r['answers']['rating'].update(confidence=float('nan')),lambda r:r['answers']['verdict'].update(choice='unrequested')):
            r=response({'questions':QUESTIONS});mutate(r)
            with self.assertRaises(ValueError):g.validate_response(QUESTIONS,r)

    def test_all_house_scope_includes_ca_and_national_excludes_other_offices_cancelled(self):
        self.assertEqual([c['name'] for _,c,_ in g.candidates(fixture(),'house-all')],['Alice','Bob','Chris'])

    def test_qualified_write_ins_are_included_without_promoting_their_roster(self):
        data=fixture();data['positions'][0]['qualified_write_in_candidates']=[{'name':'Write In','party':'D'}]
        rows=g.candidates(data,'house-all')
        self.assertEqual(len(rows),4)
        self.assertEqual(next(r for p,c,r in rows if c['name']=='Write In'),'qualified_write_in_candidates')

    def test_playground_union_adds_every_county_office_and_deduplicates_shared_races(self):
        current=p.snapshot(expanded_fixture())
        self.assertEqual(len(current['candidates']),8);self.assertEqual(len(current['races']),7)
        self.assertEqual(sum(c['candidate']=='Alice' for c in current['candidates']),1)
        self.assertEqual(sum(c['candidate']=='Governor' for c in current['candidates']),1)
        self.assertFalse({'Outside','Excluded local','Senator'} & {c['candidate'] for c in current['candidates']})
        local=[c for c in current['candidates'] if c['candidate']=='Local Alex']
        self.assertEqual(len({c['id'] for c in local}),2)  # distinct races never collapse by name
        self.assertEqual({c['roster'] for c in current['candidates']},
                         {'candidates','qualified_write_in_candidates','filed_candidates_not_confirmed_on_ballot'})
        self.assertIn('empty',{r['id'] for r in current['races']})
        self.assertEqual(next(c for c in current['candidates'] if c['candidate']=='Local Write In')['state']['candidate_roster'],'qualified_write_in_candidates')

    def test_local_input_identifies_jurisdiction_and_keeps_cal_access_separate_from_fec(self):
        data=expanded_fixture();pos=data['positions'][5];candidate=pos['candidates'][0]
        candidate['ca_independent_expenditures']={'items':[{'spender_id':'1','direction':'for','amount':1234},
            {'spender_id':'2','direction':'against','amount':4321}]}
        candidate['independent_expenditures']={'items':[{'spender_id':'1','direction':'for','amount':500}]}
        data['ca_ie_spenders']={'1':{'name':'California support'},'2':{'name':'California oppose'}}
        data['ie_spenders']={'1':{'name':'Federal committee'}}
        state=p.playground_state(pos,candidate,data)
        self.assertEqual(state['jurisdiction'],'AL-local jurisdiction');self.assertEqual(state['office_category'],'Mayor')
        self.assertEqual(state['state'],'CA');self.assertEqual(state['party'],'Nonpartisan');self.assertTrue(state['incumbent'])
        self.assertEqual(state['counties'],['Alameda']);self.assertEqual(state['district_or_seat'],'District 3')
        self.assertEqual(state['ca_spenders_supporting'],['California support $1,234'])
        self.assertEqual(state['ca_spenders_opposing'],['California oppose $4,321'])
        self.assertEqual(state['spenders_supporting'],['Federal committee $500'])

    def test_focus_includes_owner_names_and_preserves_relationship_context(self):
        data=fixture();pos=data['positions'][0];c=pos['candidates'][0]
        c['endorsements']=[{'endorser':'Hindu American PAC','relation':'supported','phase':'primary','historical':True,'rating':'Ally'},
                          {'endorser':'Vote for Peace','relation':'preferred','phase':'general'},
                          {'endorser':'Track AIPAC / Citizens Against AIPAC Corruption','relation':'endorsed','phase':'unspecified'},
                          {'endorser':'Local Teachers Union','relation':'endorsed','phase':'general'},
                          {'endorser':'California Jewish Democrats','relation':'supported','phase':'general'},
                          {'endorser':'Peace Officers Research Association of California','relation':'endorsed','phase':'general'}]
        state=g.build_state(pos,c,data);rows=state['focused_endorsement_observations'];self.assertEqual(len(rows),3)
        self.assertEqual(rows[0],c['endorsements'][0]);self.assertNotIn('endorsements_and_recommendations',state)

    def test_cair_action_focus_preserves_preference_opposition_and_joint_flags(self):
        data=fixture();pos=data['positions'][0];candidate=pos['candidates'][0]
        for relation,extra in [('preferred',{}),('opposed',{}),('endorsed',{'shared':True})]:
            candidate['endorsements']=[{'endorser':'CAIR Action','relation':relation,'phase':'general',**extra}]
            record=g.build_state(pos,candidate,data)['focused_endorsement_observations'][0]
            self.assertEqual(record['relation'],relation);self.assertEqual(record.get('shared'),extra.get('shared'))

    def test_congressional_actions_resolve_titles_and_keep_actual_response(self):
        data=fixture();pos=data['positions'][0];c=pos['candidates'][0]
        data['gaza_voting']={'actions':{'119-A':{'title':'Actual action','kind':'sponsorship','date_label':'2025'}}}
        c['gaza_voting_records']=[{'congress':119,'actions':[{'action_id':'119-A','value':'Not sponsoring'}]}]
        a=g.build_state(pos,c,data)['congressional_gaza_actions'][0]
        self.assertEqual(a,{'congress':119,'title':'Actual action','kind':'sponsorship','date':'2025','response':'Not sponsoring'})


class RunChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.data=fixture()
        self.path=self.root/'data.json';g.save(self.path,self.data);self.base=self.root/'baseline.json';g.save(self.base,baseline(self.data))
        self.managers=[]
    def tearDown(self):
        for m in self.managers:
            end=time.monotonic()+5
            while m.active and time.monotonic()<end:time.sleep(.01)
        self.temp.cleanup()
    def manager(self,transport=None,key='SECRET_FIXTURE',workers=3):
        m=p.RunManager(self.path,self.root/('work'+str(len(self.managers))),key,self.base,transport or (lambda work,req,key,force:response(req)),workers)
        self.managers.append(m);return m
    def wait(self,m,id_):
        end=time.monotonic()+5
        while m.get(id_)['status'] in {'running','cancelling'} and time.monotonic()<end:time.sleep(.01)
        return m.get(id_)

    def test_default_is_stored_all_answers_with_no_threshold_flag(self):
        b=self.manager().bootstrap();self.assertEqual(len(b['baseline']['rows']),3)
        self.assertNotIn('SECRET_FIXTURE',json.dumps(b));self.assertNotIn('accepted',json.dumps(b));self.assertEqual(b['baseline']['rows'][0]['response']['answers']['verdict']['confidence'],.12)

    def test_expanded_roster_keeps_original_house_baseline_and_local_inputs_are_ungraded(self):
        g.save(self.path,expanded_fixture());bootstrap=self.manager().bootstrap()
        self.assertEqual(len(bootstrap['snapshot']['candidates']),8)
        self.assertEqual(len(bootstrap['baseline']['rows']),3)
        original=json.loads(self.base.read_text())
        for row in bootstrap['baseline']['rows']:
            self.assertEqual(row['request'],original['decisions'][row['request_sha256']]['request'])
            self.assertNotIn('jurisdiction',row['request']['state'])
        self.assertNotEqual(bootstrap['baseline']['state_version'],bootstrap['snapshot']['state_version'])

    def test_single_local_and_full_expanded_runs_use_the_same_edited_questions(self):
        data=expanded_fixture();g.save(self.path,data);calls=[]
        def call(work,req,key,force):calls.append(deepcopy(req));return response(req)
        m=self.manager(call);local=next(c for c in m.current()['candidates'] if c['position_id']=='SC-local')
        q={'local_or_federal':{'type':'noul','instructions':'Use the candidate office context.'}}
        one=self.wait(m,m.start(q,local['id'])['id'])
        self.assertEqual(len(calls),1);self.assertEqual(one['rows'][0]['request']['state']['jurisdiction'],'SC-local jurisdiction')
        self.assertEqual(one['rows'][0]['request']['questions'],q)
        all_done=self.wait(m,m.start(q)['id']);self.assertEqual(len(all_done['rows']),8)
        self.assertEqual(len(calls),9);self.assertTrue(all(c['questions']==q for c in calls))
        self.assertEqual(one['state_version'],p.STATE_VERSION)

    def test_fresh_run_retains_low_confidence_and_arbitrary_questions_without_cutoffs(self):
        calls=[]
        def call(work,req,key,force):calls.append((deepcopy(req),force));return response(req)
        m=self.manager(call);r=m.start(QUESTIONS);done=self.wait(m,r['id'])
        self.assertEqual(done['status'],'complete');self.assertEqual(done['completed'],3);self.assertEqual(len(calls),3)
        self.assertTrue(all(force for _,force in calls));self.assertNotIn('accepted',json.dumps(done))
        self.assertTrue(all(row['response']['answers']['rating']['confidence']==0. for row in done['rows']))

    def test_selected_run_calls_exactly_one_candidate_with_current_data_and_edited_questions(self):
        calls=[]
        def call(work,req,key,force):calls.append((deepcopy(req),force));return response(req)
        m=self.manager(call);selected=m.current()['candidates'][1]
        updated=deepcopy(self.data);updated['positions'][1]['candidates'][0]['party']='R';g.save(self.path,updated)
        questions=deepcopy(QUESTIONS);questions['verdict']['instructions']='Edited single example'
        done=self.wait(m,m.start(questions,selected['id'])['id'])
        self.assertEqual(done['scope'],'candidate');self.assertEqual(len(done['rows']),1)
        self.assertEqual(done['completed'],1);self.assertEqual(len(calls),1)
        self.assertEqual(done['rows'][0]['id'],selected['id']);self.assertEqual(calls[0][0]['state']['candidate'],'Bob')
        self.assertEqual(done['rows'][0]['party'],'R');self.assertEqual(calls[0][0]['questions'],questions);self.assertTrue(calls[0][1])
        self.assertEqual(done['rows'][0]['request_sha256'],g.digest(g.dump(calls[0][0]).encode()))
        self.assertEqual(m.history()[0]['candidate'],'Bob');self.assertEqual(m.history()[0]['total'],1)
        single=deepcopy(done)
        all_done=self.wait(m,m.start(QUESTIONS)['id'])
        self.assertEqual(all_done['scope'],'all');self.assertEqual(len(all_done['rows']),3)
        self.assertEqual(m.get(single['id']),single)

    def test_selected_repeats_are_fresh_and_freeze_each_prompt(self):
        calls=[]
        def call(work,req,key,force):calls.append(deepcopy(req));return response(req)
        m=self.manager(call);id_=m.current()['candidates'][0]['id'];q=deepcopy(QUESTIONS)
        first=self.wait(m,m.start(q,id_)['id']);q['verdict']['instructions']='Iteration two'
        second=self.wait(m,m.start(q,id_)['id']);third=self.wait(m,m.start(q,id_)['id'])
        self.assertEqual(len(calls),3);self.assertNotEqual(first['id'],second['id']);self.assertNotEqual(second['id'],third['id'])
        self.assertEqual(m.get(first['id'])['questions'],QUESTIONS);self.assertEqual(second['questions'],q)
        self.assertEqual(second['rows'][0]['request_sha256'],third['rows'][0]['request_sha256'])

    def test_latest_retains_each_candidate_across_iterations_and_restart(self):
        m=self.manager();ids=[c['id'] for c in m.current()['candidates']]
        questions=deepcopy(QUESTIONS);questions['verdict']['instructions']='Alice iteration'
        first=self.wait(m,m.start(questions,ids[0])['id'])
        second=self.wait(m,m.start(QUESTIONS,ids[1])['id'])
        latest=m.latest();rows={row['id']:row for row in latest['rows']}
        for saved in (first,second):
            original=saved['rows'][0];row=rows[original['id']]
            self.assertEqual(row['request'],original['request'])
            self.assertEqual(row['response'],original['response'])
            self.assertEqual(row['request_sha256'],original['request_sha256'])
            self.assertEqual(row['evaluation']['run_id'],saved['id'])
        self.assertEqual(rows[ids[2]]['evaluation']['run_id'],m.bootstrap()['baseline']['id'])
        changed=deepcopy(QUESTIONS);changed['verdict']['instructions']='Alice iteration two'
        third=self.wait(m,m.start(changed,ids[0])['id'])
        restarted=p.RunManager(self.path,m.work,'',self.base)
        rows={row['id']:row for row in restarted.bootstrap()['latest']['rows']}
        self.assertEqual(rows[ids[0]]['evaluation']['run_id'],third['id'])
        self.assertEqual(rows[ids[0]]['request']['questions'],changed)
        self.assertEqual(rows[ids[1]]['evaluation']['run_id'],second['id'])
        self.assertEqual(m.get(first['id']),first)  # projection never modifies stored requests
        self.assertNotIn('SECRET_FIXTURE',json.dumps(restarted.latest()))

    def test_latest_keeps_previous_answers_during_retries_and_after_failure(self):
        m=self.manager();id_=m.current()['candidates'][0]['id']
        first=self.wait(m,m.start(QUESTIONS,id_)['id']);release=threading.Event()
        def failed(*args,**kwargs):
            release.wait(2);raise RuntimeError('SECRET_FIXTURE provider body')
        m.transport=failed
        pending=m.start(QUESTIONS,id_)
        row=next(row for row in m.latest()['rows'] if row['id']==id_)
        self.assertEqual(row['evaluation']['run_id'],first['id'])
        self.assertEqual(row['latest_attempt']['status'],'queued')
        self.assertEqual(m.latest()['active_run']['id'],pending['id'])
        release.set();self.wait(m,pending['id'])
        latest=m.latest();row=next(row for row in latest['rows'] if row['id']==id_)
        self.assertEqual(row['evaluation']['run_id'],first['id'])
        self.assertEqual(row['latest_attempt']['status'],'error')
        self.assertEqual(row['latest_attempt']['run_id'],pending['id'])
        self.assertNotIn('SECRET_FIXTURE',json.dumps(latest));self.assertIsNone(latest['active_run'])

    def test_latest_orders_by_evaluation_time_not_filename_or_file_modification(self):
        m=self.manager();id_=m.current()['candidates'][0]['id']
        first=self.wait(m,m.start(QUESTIONS,id_)['id'])
        second=self.wait(m,m.start(QUESTIONS,id_)['id'])
        first['created_at']='2026-10-25T01:00:00+00:00'
        first['rows'][0]['finished_at']='2026-10-25T06:00:00+00:00'
        second['created_at']='2026-10-25T02:00:00+00:00'
        second['rows'][0]['finished_at']='2026-10-25T05:00:00+00:00'
        g.save(m.work/'runs'/first['id']/'run.json',first)
        g.save(m.work/'runs'/second['id']/'run.json',second)
        restarted=p.RunManager(self.path,m.work,'',self.base)
        row=next(row for row in restarted.latest()['rows'] if row['id']==id_)
        self.assertEqual(row['evaluation']['run_id'],first['id'])

    def test_latest_ungraded_and_interrupted_candidates_are_not_fabricated_answers(self):
        g.save(self.path,expanded_fixture());m=self.manager();current=m.current()
        local=next(c for c in current['candidates'] if c['position_id']=='SC-local')
        row=next(row for row in m.latest()['rows'] if row['id']==local['id'])
        self.assertEqual(row['status'],'preview');self.assertNotIn('response',row)
        release=threading.Event()
        m.transport=lambda work,req,key,force:(release.wait(2),response(req))[1]
        pending=m.start(QUESTIONS,local['id'])
        restarted=p.RunManager(self.path,m.work,'',self.base)
        row=next(row for row in restarted.latest()['rows'] if row['id']==local['id'])
        self.assertEqual(row['status'],'interrupted');self.assertNotIn('response',row)
        self.assertIsNone(restarted.latest()['active_run'])
        release.set();self.wait(m,pending['id'])
        data=expanded_fixture();data['positions'][6]['ballot_status']='excluded';g.save(self.path,data)
        self.assertNotIn(local['id'],{row['id'] for row in m.latest()['rows']})
        self.assertEqual(m.get(pending['id'])['rows'][0]['id'],local['id'])

    def test_unknown_invalid_or_removed_selection_never_calls_provider(self):
        calls=[]
        def call(*args,**kwargs):calls.append(True);return {}
        m=self.manager(call);selected=m.current()['candidates'][0]['id']
        data=deepcopy(self.data);data['positions'][0]['ballot_status']='excluded';g.save(self.path,data)
        for id_ in ('unknown',selected,'',{},[],123):
            with self.assertRaises(ValueError):m.start(QUESTIONS,id_)
        self.assertFalse(calls);self.assertIsNone(m.active);self.assertEqual(m.history(),[])

    def test_one_failure_is_explicit_and_does_not_discard_other_answers_or_leak_secrets(self):
        def call(work,req,key,force):
            if req['state']['candidate']=='Bob':raise RuntimeError('SECRET_FIXTURE provider body')
            return response(req)
        m=self.manager(call);r=self.wait(m,m.start(QUESTIONS)['id']);self.assertEqual(r['completed'],3);self.assertEqual(r['errors'],1)
        self.assertNotIn('SECRET_FIXTURE',json.dumps(r));self.assertEqual(sum(row['status']=='complete' for row in r['rows']),2)

    def test_job_freezes_questions_and_dataset_before_network(self):
        release=threading.Event()
        def call(work,req,key,force):release.wait(2);return response(req)
        m=self.manager(call);q=deepcopy(QUESTIONS);initial=m.start(q)
        q['verdict']['instructions']='Changed later';data=deepcopy(self.data);data['positions'][0]['candidates'][0]['name']='New name';g.save(self.path,data)
        release.set();done=self.wait(m,initial['id']);self.assertEqual(done['questions'],QUESTIONS)
        self.assertEqual(done['rows'][0]['request']['state']['candidate'],'Alice')
        self.assertNotEqual(done['dataset_sha256'],m.current()['dataset_sha256'])

    def test_stop_prevents_queued_calls_and_does_not_mix_prior_results(self):
        release=threading.Event();started=threading.Event();calls=[]
        def call(work,req,key,force):calls.append(req);started.set();release.wait(2);return response(req)
        m=self.manager(call,workers=1);run=m.start(QUESTIONS);started.wait(1);m.cancel(run['id']);release.set();done=self.wait(m,run['id'])
        self.assertEqual(done['status'],'cancelled');self.assertEqual(len(calls),1)
        self.assertTrue(any(row['status']=='cancelled' and 'response' not in row for row in done['rows']))
        cancelled=next(row for row in done['rows'] if row['status']=='cancelled')
        row=next(row for row in m.latest()['rows'] if row['id']==cancelled['id'])
        self.assertEqual(row['status'],'complete')  # older baseline retained, not relabeled as new
        self.assertEqual(row['latest_attempt']['status'],'cancelled')
        self.assertNotEqual(row['evaluation']['run_id'],done['id'])

    def test_active_run_rejects_overlap_and_auth_failure_is_fatal(self):
        gate=threading.Event()
        def slow(work,req,key,force):gate.wait(2);return response(req)
        m=self.manager(slow);run=m.start(QUESTIONS)
        with self.assertRaises(RuntimeError):m.start(QUESTIONS)
        gate.set();self.wait(m,run['id'])
        def auth(*args,**kwargs):raise PermissionError('bad key')
        m2=self.manager(auth);self.assertEqual(self.wait(m2,m2.start(QUESTIONS)['id'])['status'],'error')

    def test_deltas_bind_run_and_preserve_full_request_in_download(self):
        m=self.manager();done=self.wait(m,m.start(QUESTIONS)['id']);delta=m.get(done['id'],0)
        self.assertEqual(len(delta['changes']),3);self.assertTrue(all('request' not in r for r in delta['changes']))
        self.assertTrue(all('request' in r for r in done['rows']))
        self.assertEqual(m.get(done['id'],done['revision'])['changes'],[])

    def test_runs_survive_restart_and_missing_key_can_still_review_baseline(self):
        m=self.manager();done=self.wait(m,m.start(QUESTIONS)['id'])
        other=p.RunManager(self.path,m.work,'',self.base);self.assertEqual(other.get(done['id'])['rows'],done['rows'])
        self.assertFalse(other.bootstrap()['key_configured'])
        with self.assertRaises(PermissionError):other.start(QUESTIONS)

    def test_http_same_origin_host_json_and_static_allowlist(self):
        m=self.manager();server=p.ThreadingHTTPServer(('127.0.0.1',0),p.handler_for(m));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(method,path,body=None,headers=None):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port);c.request(method,path,body,headers or {});r=c.getresponse();status=r.status;b=r.read();c.close();return status,b
        try:
            self.assertEqual(request('GET','/api/bootstrap')[0],200)
            self.assertEqual(request('GET','/api/snapshot')[0],200)
            status,body=request('GET','/api/latest');self.assertEqual(status,200)
            self.assertEqual(json.loads(body)['scope'],'latest')
            self.assertNotIn(b'SECRET_FIXTURE',body)
            self.assertEqual(request('GET','/../jev-key')[0],404)
            self.assertEqual(request('GET','/api/bootstrap',headers={'Host':'evil.test'})[0],403)
            self.assertEqual(request('POST','/api/runs','{}',{'Content-Type':'application/json'})[0],403)
            self.assertEqual(request('POST','/api/runs','{}',{'Content-Type':'application/json','Origin':'https://evil.test'})[0],403)
            origin='http://127.0.0.1:'+str(server.server_port)
            headers={'Content-Type':'application/json','Origin':origin}
            self.assertEqual(request('POST','/api/runs',json.dumps({'questions':QUESTIONS,'key':'SECRET_FIXTURE'}),headers)[0],400)
            status,body=request('POST','/api/runs',json.dumps({'questions':QUESTIONS}),headers);self.assertEqual(status,202);id_=json.loads(body)['id'];self.wait(m,id_)
            self.assertNotIn(b'SECRET_FIXTURE',request('GET','/api/runs/'+id_)[1])
            selected=m.current()['candidates'][0]['id']
            for candidate_id in (None,'',[],123,'stale'):
                self.assertEqual(request('POST','/api/runs',json.dumps({'questions':QUESTIONS,'candidate_id':candidate_id}),headers)[0],400)
            status,body=request('POST','/api/runs',json.dumps({'questions':QUESTIONS,'candidate_id':selected}),headers)
            self.assertEqual(status,202);single=self.wait(m,json.loads(body)['id']);self.assertEqual(len(single['rows']),1)
            self.assertEqual(single['rows'][0]['id'],selected)
        finally:server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
