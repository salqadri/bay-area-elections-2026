"""Offline API, snapshot, validation, run isolation and local credential regressions."""
from copy import deepcopy
import http.client
import json
import math
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import grade_gaza as g
import serve_jev_playground as p
import score_grade as sg

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
            ('outside',['San Diego'],'Mayor','confirmed','Outside'),
            ('excluded-local',['Santa Clara'],'Mayor','excluded','Excluded local'),
            ('empty',['Santa Clara'],'Water district','confirmed',None)]:
        data['positions'].append({'id':id_,'counties':county,'government_level':'City or town',
            'office_category':category,'office':category,'jurisdiction':id_+' jurisdiction',
            'district_or_seat':'District 3','partisan':False,'ballot_status':status,
            'election_type':'general','candidates':[{'name':name,'incumbent':True}] if name else []})
    data['positions'][5]['qualified_write_in_candidates']=[{'name':'Local Write In'}]
    data['positions'][5]['filed_candidates_not_confirmed_on_ballot']=[{'name':'Local provisional'}]
    return data


def five_county_fixture():
    data=expanded_fixture()
    for county in ('Contra Costa','San Francisco','San Mateo'):
        data['positions'].append({'id':county,'office':'Mayor','office_category':'Mayor',
            'jurisdiction':county+' city','partisan':False,'counties':[county],
            'ballot_status':'confirmed','candidates':[{'name':'Shared candidate name'}]})
    return data


def baseline(data):
    results=[];decisions={}
    for pos,c,roster in g.candidates(data,'house-all'):
        req={'model':g.MODEL,'state':g.build_state(pos,c,data),'questions':QUESTIONS};ref=g.digest(g.dump(req).encode())
        decisions[ref]={'request':req,'response':response(req)}
        results.append({'position_id':pos['id'],'candidate':c['name'],'party':c['party'],'roster':roster,'request_sha256':ref})
    return {'questions':QUESTIONS,'model':g.MODEL,'run_on':'2026-10-23T10:00:00+00:00','state_version':'house-evidence-v3-focused','dataset_sha256':g.digest(g.dump(data).encode()),'results':results,'decisions':decisions}


class ValidationChecks(unittest.TestCase):
    def test_default_grade_boundaries_are_inclusive_without_rounding(self):
        self.assertEqual(sg.DEFAULT_MAPPING['upper_bounds'][3],3.2)
        self.assertEqual(sg.score_grade(3.2),'C')
        self.assertEqual(sg.score_grade(3.21),'B')
        self.assertEqual(sg.score_grade(0), 'F')
        for i, upper in enumerate(sg.DEFAULT_MAPPING['upper_bounds']):
            self.assertEqual(sg.score_grade(upper), 'FEDCB'[i])
            self.assertEqual(sg.score_grade(math.nextafter(upper, math.inf)), 'EDCBA'[i])
        self.assertEqual(sg.score_grade(5), 'A')
        for value in (None, True, '2', -0.1, 5.1, float('nan'), float('inf')):
            self.assertIsNone(sg.score_grade(value))

    def test_reviewed_fiona_ma_divestment_evidence_reaches_generated_state(self):
        data=json.loads((g.ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())
        p,c=next((p,c) for p in data['positions'] for c in p.get('candidates') or [] if c['name']=='Fiona Ma')
        state=g.build_state(p,c,data)
        self.assertTrue(any('2024-05-16' in item and 'opposed divestment from Israel' in item
                            for item in state['gaza_evidence']))

    def test_evidence_score_suppresses_only_below_ten_percent(self):
        row={'status':'complete','request':{'questions':{
            'pro_palestine_score':{'type':'score','criteria':list('012345')},
            'evidence_score':{'type':'score','criteria':['none','concrete']}}},
            'response':{'answers':{'pro_palestine_score':{'type':'score','score':1.77,'confidence':0},
                                  'evidence_score':{'type':'score','score':0,'confidence':1}}}}
        for value in (0, .05, .099999, .1, 1):
            row['response']['answers']['evidence_score']['score']=value
            original=deepcopy(row)
            self.assertEqual(sg.row_grade(row), 'N/A' if value < .1 else 'D')
            self.assertEqual(sg.present_run({'rows':[row]},sg.DEFAULT_MAPPING)['rows'][0]['response'], original['response'])
            self.assertEqual(row,original)
        for value in (None, True, '0', -.1, 1.1, float('nan')):
            row['response']['answers']['evidence_score']['score']=value
            self.assertEqual(sg.row_grade(row),'D')
        row['response']['answers']['evidence_score']['score']=0
        row['request']['questions']['evidence_score']['criteria'].append('other scale')
        self.assertEqual(sg.row_grade(row),'D')
        del row['request']['questions']['evidence_score']
        self.assertEqual(sg.row_grade(row),'D')
        row['response']['answers']['pro_palestine_score']['score']=None
        self.assertIsNone(sg.row_grade(row))

    def test_custom_grade_mapping_validation_and_input_preservation(self):
        mapping={'upper_bounds':[.1,.5,1,2,4.9]}
        self.assertEqual(sg.score_grade(2.5,mapping),'B')
        for invalid in ({},[],{'upper_bounds':[1,2,3,4]}, {'upper_bounds':[0,1,2,3,4]},
                        {'upper_bounds':[1,2,2,3,4]}, {'upper_bounds':[1,2,3,4,5]},
                        {'upper_bounds':[False,1,2,3,4]}, {'upper_bounds':[1,2,3,4,'4.5']},
                        {'upper_bounds':[1,2,3,4,float('nan')]}, {**mapping,'extra':1}):
            with self.assertRaises(ValueError):sg.validate_mapping(invalid)
        q={'pro_palestine_score':{'type':'score','criteria':list('012345')}}
        row={'status':'complete','request':{'questions':q},'response':{'answers':{'pro_palestine_score':{'type':'score','score':2.5,'confidence':0}}}}
        before=deepcopy(row);projected=sg.present_run({'rows':[row]},mapping)
        self.assertEqual(projected['rows'][0]['pro_palestine_score_grade'],'B')
        self.assertEqual(row,before);self.assertIs(projected['rows'][0]['request'],row['request'])
        row['status']='queued';self.assertIsNone(sg.row_grade(row))
        row['status']='complete';q['pro_palestine_score']['criteria'].pop();self.assertIsNone(sg.row_grade(row))

    def test_vote_for_peace_neutral_is_context_only_exact_candidacy_and_source(self):
        data=fixture();pos=data['positions'][0];pos['id']='CA2026-014';c=pos['candidates'][0];c['name']='Xavier Becerra'
        before=deepcopy(c);state=g.build_state(pos,c,data);records=state['focused_endorsement_observations']
        self.assertEqual(c,before);self.assertEqual(len(records),1)
        self.assertEqual((records[0]['relation'],records[0]['rating']),('neutral','Neutral'))
        self.assertNotIn('url',records[0]);self.assertNotIn('source_label',records[0])
        pos['id']='other-race';self.assertNotIn('focused_endorsement_observations',g.build_state(pos,c,data))
        pos['id']='CA2026-014';c['endorsements']=[{'endorser':'VoteForPeace','relation':'opposed','phase':'general','url':'https://example.test/new'}]
        records=g.build_state(pos,c,data)['focused_endorsement_observations'];self.assertEqual(len(records),1)
        self.assertEqual(records[0]['relation'],'opposed');self.assertNotIn('rating',records[0])

    def test_vote_for_peace_exact_labels_and_primary_phase_are_retained(self):
        review=json.loads((g.ROOT/'research/endorsements/peace-guides-2026-10-09.json').read_text())
        for finding in review['findings']:
            e=finding['record']
            if e['endorser']!='Vote for Peace':continue
            c={'name':finding['candidate'],'endorsements':[deepcopy(e)]};pos={'id':finding['position_id']}
            records=g.focused_endorsements(pos,c);self.assertEqual(len(records),1)
            card=next(card for card in review['vote_for_peace_cards'] if card.get('candidate')==c['name'] and card.get('position_id')==pos['id'] and card['phase']==e['phase'])
            self.assertEqual(records[0]['source_label'],card['source_label'])
            for key in ('relation','rating','phase','url','checked_on'):
                if key in e:self.assertEqual(records[0][key],e[key])
            c['endorsements'][0]['checked_on']='2026-10-25'
            self.assertEqual(g.focused_endorsements(pos,c)[0]['checked_on'],'2026-10-25')

    def test_cli_grade_adds_derived_result_without_modifying_provider_decision(self):
        criteria={'id':'fixture','questions':{'pro_palestine_score':{'type':'score','criteria':list('012345')}}}
        plan=g.plan(fixture(),criteria,'house-all');plan['state_version']='exact-planned-evidence-version'
        def call(work,request,key,force=False):
            out=response(request);out['answers']['pro_palestine_score']['score']=2.5;return out
        with tempfile.TemporaryDirectory() as directory, patch.object(g,'jev_call',side_effect=call):
            work=Path(directory);g.grade(work,plan,criteria,'FIXTURE',score_grade_mapping={'upper_bounds':[.1,.5,1,2,4.9]})
            batch=json.loads((work/'results.json').read_text())
        self.assertEqual(batch['state_version'],plan['state_version'])
        self.assertTrue(all(r['pro_palestine_score_grade']=='B' for r in batch['results']))
        for decision in batch['decisions'].values():
            self.assertEqual(decision['request']['questions'],criteria['questions'])
            self.assertNotIn('pro_palestine_score_grade',decision['response']['answers'])

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
        self.assertEqual(len(current['candidates']),10);self.assertEqual(len(current['races']),9)
        self.assertEqual(sum(c['candidate']=='Alice' for c in current['candidates']),1)
        self.assertEqual(sum(c['candidate']=='Governor' for c in current['candidates']),1)
        self.assertFalse({'Excluded','Excluded local'} & {c['candidate'] for c in current['candidates']})
        self.assertTrue({'Outside','Senator'} <= {c['candidate'] for c in current['candidates']})
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
        self.assertEqual(state['jurisdiction'],'AL-local jurisdiction');self.assertIn('Mayor',state['office'])
        self.assertEqual(state['state'],'CA');self.assertEqual(state['party'],'Nonpartisan');self.assertTrue(state['incumbent'])
        self.assertIn('District 3',state['office']);self.assertNotIn('counties',state);self.assertNotIn('district_or_seat',state)
        self.assertEqual(next(r for r in p.snapshot(data)['races'] if r['id']==pos['id'])['counties'],['Alameda'])
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
        self.assertEqual(rows[0],{**c['endorsements'][0],'source':'unverified'});self.assertNotIn('endorsements_and_recommendations',state)

    def test_compact_identity_keeps_false_observations_and_retention_context(self):
        data=expanded_fixture();data['election']['date']='2026-11-03'
        pos=data['positions'][5];candidate=pos['candidates'][0];pos['election_type']='retention'
        with patch.object(g,'community_state',return_value={'part_of_muslim_community':False}):
            state=p.playground_state(pos,candidate,data)
        self.assertIs(state['part_of_muslim_community'],False)
        self.assertEqual(state['election_type'],'retention');self.assertEqual(state['election_date'],'2026-11-03')
        self.assertEqual(state['party'],'Nonpartisan');self.assertTrue(state['incumbent'])
        self.assertFalse(set(state)&{'counties','office_category','government_level','district_or_seat','partisan'})

    def test_cair_action_focus_preserves_preference_opposition_and_joint_flags(self):
        data=fixture();pos=data['positions'][0];candidate=pos['candidates'][0]
        for relation,extra in [('preferred',{}),('opposed',{}),('endorsed',{'shared':True})]:
            candidate['endorsements']=[{'endorser':'CAIR Action','relation':relation,'phase':'general',**extra}]
            record=g.build_state(pos,candidate,data)['focused_endorsement_observations'][0]
            self.assertEqual(record['relation'],relation);self.assertEqual(record.get('shared'),extra.get('shared'))

    def test_comparison_metadata_preserves_cair_sources_and_is_bound_to_the_candidacy(self):
        data=expanded_fixture()
        records=[{'endorser':'CAIR Action','relation':'preferred','phase':'general','url':'https://example.test/guide#page=2','checked_on':'2026-10-23'},
                 {'endorser':'CAIR Action','relation':'endorsed','phase':'primary','historical':True,'shared':True},
                 {'endorser':'CAIR SFBA','relation':'endorsed','phase':'general'}]
        data['positions'][5]['candidates'][0]['endorsements']=deepcopy(records)
        current=p.snapshot(data)
        first=next(c for c in current['candidates'] if c['position_id']=='AL-local' and c['roster']=='candidates')
        second=next(c for c in current['candidates'] if c['position_id']=='SC-local')
        self.assertEqual(first['candidate'],second['candidate'])
        self.assertEqual(first['cair_action'],records[:2]);self.assertEqual(second['cair_action'],[])
        self.assertEqual(first['cair_action'][0]['url'],'https://example.test/guide#page=2')
        self.assertEqual(data['positions'][5]['candidates'][0]['endorsements'],records)

    def test_congressional_actions_resolve_titles_and_keep_actual_response(self):
        data=fixture();pos=data['positions'][0];c=pos['candidates'][0]
        data['gaza_voting']={'actions':{'119-A':{'title':'Actual action','kind':'sponsorship','date_label':'2025'}}}
        c['gaza_voting_records']=[{'congress':119,'sheet_title':'119th House','actions':[{'action_id':'119-A','value':'Not sponsoring','assessment':'positive','assessment_basis':'sheet_dropdown'}]}]
        a=g.build_state(pos,c,data)['congressional_gaza_actions'][0]
        self.assertEqual(a,{'title':'Actual action','kind':'sponsorship','date':'2025','response':'Not sponsoring','alignment':'aligned'})

    def test_legislative_date_fixture_parity_and_cutoff(self):
        from legislative_actions import action_date, CUTOFF
        cases=json.loads((g.ROOT/'research/gaza-records/action-date-fixtures.json').read_text())
        for case in cases:
            with self.subTest(case=case['input']):
                parsed=action_date(case['input'])
                self.assertEqual(parsed,case['expected'])
                self.assertEqual(bool(parsed['start'] and parsed['start']>=CUTOFF),case['eligible_for_jev'])

    def test_legislative_scope_is_per_action_not_congress_and_preserves_assessments(self):
        data=fixture();pos=data['positions'][0];c=pos['candidates'][0]
        data['gaza_voting']={'actions':{
            'old':{'title':'Historical action in current tab','date_label':'2011-07-07'},
            'before':{'date_label':'2023-11-30'},'boundary':{'date_label':'2023-12-01'},
            'new':{'date_label':'2026-09-03'},'period':{'date_label':'2025-2027'},
            'straddles':{'date_label':'2023-2025'},'undated':{}}}
        for name,metadata in data['gaza_voting']['actions'].items():metadata.setdefault('title',name)
        c['gaza_voting_records']=[{'congress':119,'sheet_title':'119th House','actions':[
            {'action_id':name,'value':value,'assessment':assessment,'assessment_basis':'sheet_dropdown'}
            for name,value,assessment in [('old','Yes','negative'),('before','Yes','negative'),('boundary','No','positive'),
                                          ('period','Not sponsoring','negative'),('straddles','Sponsor','positive'),
                                          ('undated','Yes','positive')]]},
            {'congress':118,'sheet_title':'118th House','actions':[{'action_id':'new','value':'Not voting','assessment':'neutral'}]}]
        before=deepcopy(c)
        state=g.build_state(pos,c,data);rows=state['congressional_gaza_actions']
        self.assertEqual([r['title'] for r in rows],['new','boundary','period'])
        self.assertEqual(rows[0]['alignment'],'neutral')
        self.assertEqual(rows[1]['response'],'No');self.assertEqual(rows[1]['alignment'],'aligned')
        self.assertEqual(rows[2]['alignment'],'not_aligned');self.assertEqual(rows[2]['date'],'2025-2027')
        self.assertIn('anti-Zionist',state['congressional_gaza_context'])
        self.assertEqual(c,before)

    def test_garamendi_state_carries_every_retained_sheet_assessment_without_inferring_votes(self):
        data=json.loads(g.DATASET.read_text())
        pos,c=next((p,c) for p in data['positions'] for c in p.get('candidates') or [] if c['name']=='John Garamendi')
        rows=g.build_state(pos,c,data)['congressional_gaza_actions']
        from legislative_actions import ALIGNMENT, action_date
        registry=data['gaza_voting']['actions']
        for row in rows:
            matches=[a for record in c['gaza_voting_records'] for a in record['actions']
                     if registry[a['action_id']]['title']==row['title'] and registry[a['action_id']].get('date_label')==row['date']
                     and a['value']==row['response'] and ALIGNMENT[a['assessment']]==row['alignment']]
            self.assertTrue(matches)
            self.assertFalse(set(row)&{'action_id','congress','source_tab','date_precision','sheet_assessment','assessment_basis'})
        ihra=next(r for r in rows if 'Codify IHRA' in r['title'])
        self.assertEqual((ihra['response'],ihra['alignment']),('No','aligned'))
        dated=[r['date'] for r in rows if action_date({'date_label':r['date']})['precision']=='day']
        self.assertEqual(dated,sorted(dated,reverse=True));self.assertTrue(all(v>='2023-12-01' for v in dated))
        self.assertFalse(any(r['date']=='2023-2025' for r in rows))

    def test_identical_linked_actions_collapse_but_conflicts_and_notes_remain(self):
        from legislative_actions import jev_actions
        data={'gaza_voting':{'actions':{'a':{'title':'A bill','kind':'roll_call_vote','date_label':'2026-01-01','source_url':'https://example.org/roll1'},
                                      'b':{'title':'A bill','kind':'roll_call_vote','date_label':'2026-01-01','source_url':'https://example.org/roll2'}}}}
        first={'action_id':'a','value':'No','assessment':'positive'}
        candidate={'gaza_voting_records':[{'actions':[first,dict(first),{**first,'assessment':'negative'},
                                                 {**first,'note':'Member explanation matters.'},{**first,'action_id':'b'}]}]}
        before=deepcopy(candidate);rows=jev_actions(candidate,data)
        self.assertEqual(len(rows),4);self.assertEqual(rows[0]['kind'],'vote')
        self.assertEqual([r['alignment'] for r in rows],['aligned','not_aligned','aligned','aligned'])
        self.assertEqual(rows[2]['note'],'Member explanation matters.');self.assertEqual(candidate,before)

    def test_compact_endorsements_keep_qualifiers_and_recommendation_bindings(self):
        source=[{'endorser':'CAIR Action','relation':'preferred','phase':'primary','historical':True,'shared':True,
                 'rating':'Preferred','source_label':'Preferred','verification':'campaign_claim','url':'https://example.org/guide','checked_on':'2026-10-26'}]
        before=deepcopy(source);row=g.compact_endorsements(source)[0]
        self.assertEqual(row,{'endorser':'CAIR Action','relation':'preferred','phase':'primary','historical':True,
                              'shared':True,'rating':'Preferred','source':'campaign claim'})
        self.assertEqual(source,before)
        data=json.loads(g.DATASET.read_text())
        from publish_jev_grades import validate_recommendation_evidence
        for pos in data['positions']:
            for candidate in pos.get('candidates') or []:
                state=g.build_state(pos,candidate,data)
                validate_recommendation_evidence(candidate,{'candidate':candidate['name'],'request':{'state':state}},'A')



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
        self.assertEqual(b['baseline']['questions'],QUESTIONS)
        self.assertEqual(b['questions'],json.loads(p.DEFAULT_CRITERIA.read_text())['questions'])
        self.assertNotIn('SECRET_FIXTURE',json.dumps(b));self.assertNotIn('accepted',json.dumps(b));self.assertEqual(b['baseline']['rows'][0]['response']['answers']['verdict']['confidence'],.12)

    def test_mapping_persists_and_projects_existing_results_without_rewriting_history(self):
        m=self.manager();q={'pro_palestine_score':{'type':'score','criteria':list('012345')}}
        done=self.wait(m,m.start(q)['id']);path=m.work/'runs'/done['id']/'run.json';original=path.read_bytes()
        mapping={'upper_bounds':[.1,.2,.3,.4,.5]};m.set_score_grade_mapping(mapping)
        restarted=p.RunManager(self.path,m.work,baseline=self.base)
        self.assertEqual(restarted.bootstrap()['score_grade_mapping'],mapping)
        self.assertEqual(restarted.present(done)['rows'][0]['pro_palestine_score_grade'],'F')
        self.assertEqual(m.present(m.get(done['id'],0))['changes'][0]['pro_palestine_score_grade'],'F')
        delta=m.get(done['id'],0);m.set_score_grade_mapping(sg.DEFAULT_MAPPING)
        self.assertEqual(m.present(delta)['score_grade_mapping'],mapping)
        self.assertEqual(path.read_bytes(),original)
        self.assertNotIn('pro_palestine_score_grade',json.loads(original)['rows'][0]['response']['answers'])

    def test_five_county_catalog_counts_and_bay_batch_do_not_include_national_peers(self):
        g.save(self.path,five_county_fixture());calls=[]
        def call(work,req,key,force):calls.append(deepcopy(req));return response(req)
        m=self.manager(call);current=m.current()
        self.assertEqual(current['bay_area_counties'],['Alameda','Contra Costa','San Francisco','San Mateo','Santa Clara'])
        self.assertEqual(current['scope_counts']['all']['candidates'],13)
        self.assertEqual(current['scope_counts']['bay-area']['candidates'],9)
        done=self.wait(m,m.start(QUESTIONS,scope='bay-area')['id'])
        self.assertEqual(done['scope'],'bay-area');self.assertEqual(len(done['rows']),9)
        self.assertEqual(len(calls),9)
        race_lookup={r['id']:r for r in current['races']}
        self.assertTrue(all(p.COUNTIES.intersection(race_lookup[r['position_id']]['counties']) for r in done['rows']))
        self.assertNotIn('Bob',{r['candidate'] for r in done['rows']})
        self.assertNotIn('Chris',{r['candidate'] for r in done['rows']})
        self.assertEqual(sum(r['candidate']=='Alice' for r in done['rows']),1)  # shared county race once
        self.assertEqual(sum(r['candidate']=='Shared candidate name' for r in done['rows']),3)  # distinct candidacies
        self.assertEqual({r['roster'] for r in done['rows']},
                         {'candidates','qualified_write_in_candidates','filed_candidates_not_confirmed_on_ballot'})
        self.assertEqual(m.history()[0]['scope'],'bay-area')
        self.assertTrue(all(r['request']['questions']==QUESTIONS for r in done['rows']))
        self.assertTrue(all(r['response']['answers']['verdict']['confidence']==.12 for r in done['rows']))
        self.assertEqual(len(self.wait(m,m.start(QUESTIONS)['id'])['rows']),13)

    def test_invalid_or_empty_batch_scope_makes_no_model_calls(self):
        calls=[]
        m=self.manager(lambda *args,**kwargs:calls.append(True))
        for scope in ('unknown',None,[],{},123,'candidate'):
            with self.assertRaises(ValueError):m.start(QUESTIONS,scope=scope)
        with self.assertRaises(ValueError):m.start(QUESTIONS,scope='bay-area')  # fixture has no county membership
        with self.assertRaises(ValueError):m.start(QUESTIONS,m.current()['candidates'][0]['id'],scope='bay-area')
        self.assertFalse(calls);self.assertEqual(m.history(),[])

    def test_expanded_roster_keeps_original_house_baseline_and_local_inputs_are_ungraded(self):
        g.save(self.path,expanded_fixture());bootstrap=self.manager().bootstrap()
        self.assertEqual(len(bootstrap['snapshot']['candidates']),10)
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
        all_done=self.wait(m,m.start(q)['id']);self.assertEqual(len(all_done['rows']),10)
        self.assertEqual(len(calls),11);self.assertTrue(all(c['questions']==q for c in calls))
        self.assertEqual(one['state_version'],p.STATE_VERSION)

    def test_fresh_run_retains_low_confidence_and_arbitrary_questions_without_cutoffs(self):
        calls=[]
        def call(work,req,key,force):calls.append((deepcopy(req),force));return response(req)
        m=self.manager(call);r=m.start(QUESTIONS);done=self.wait(m,r['id'])
        self.assertEqual(done['status'],'complete');self.assertEqual(done['completed'],4);self.assertEqual(len(calls),4)
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
        self.assertEqual(all_done['scope'],'all');self.assertEqual(len(all_done['rows']),4)
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

    def test_latest_cair_metadata_can_refresh_without_rewriting_saved_model_inputs(self):
        old={'endorser':'CAIR Action','relation':'opposed','phase':'general','url':'https://example.test/old'}
        self.data['positions'][0]['candidates'][0]['endorsements']=[old];g.save(self.path,self.data)
        m=self.manager();id_=m.current()['candidates'][0]['id']
        saved=self.wait(m,m.start(QUESTIONS,id_)['id'])
        path=m.work/'runs'/saved['id']/'run.json';before=path.read_bytes()
        new={**old,'relation':'preferred','url':'https://example.test/new'}
        self.data['positions'][0]['candidates'][0]['endorsements']=[new];g.save(self.path,self.data)
        row=next(r for r in m.latest()['rows'] if r['id']==id_)
        self.assertEqual(row['cair_action'],[new])
        self.assertEqual(row['request'],saved['rows'][0]['request'])
        self.assertEqual(row['request_sha256'],saved['rows'][0]['request_sha256'])
        self.assertEqual(row['request']['state']['focused_endorsement_observations'][0]['relation'],'opposed')
        self.assertEqual(m.get(saved['id']),saved);self.assertEqual(path.read_bytes(),before)

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
        m=self.manager(call);r=self.wait(m,m.start(QUESTIONS)['id']);self.assertEqual(r['completed'],4);self.assertEqual(r['errors'],1)
        self.assertNotIn('SECRET_FIXTURE',json.dumps(r));self.assertEqual(sum(row['status']=='complete' for row in r['rows']),3)

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
        self.assertEqual(len(delta['changes']),4);self.assertTrue(all('request' not in r for r in delta['changes']))
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
            mapping={'upper_bounds':[.1,.5,1,2,4.9]}
            self.assertEqual(request('POST','/api/score-grade-mapping',json.dumps(mapping),headers)[0],200)
            self.assertEqual(json.loads(request('GET','/api/bootstrap')[1])['score_grade_mapping'],mapping)
            self.assertEqual(request('POST','/api/score-grade-mapping','{"upper_bounds":[1,2,2,3,4]}',headers)[0],400)
            self.assertEqual(request('POST','/api/score-grade-mapping',json.dumps(mapping),{'Content-Type':'application/json'})[0],403)
            self.assertEqual(request('POST','/api/runs',json.dumps({'questions':QUESTIONS,'key':'SECRET_FIXTURE'}),headers)[0],400)
            status,body=request('POST','/api/runs',json.dumps({'questions':QUESTIONS}),headers);self.assertEqual(status,202);id_=json.loads(body)['id'];self.wait(m,id_)
            self.assertNotIn(b'SECRET_FIXTURE',request('GET','/api/runs/'+id_)[1])
            selected=m.current()['candidates'][0]['id']
            for candidate_id in (None,'',[],123,'stale'):
                self.assertEqual(request('POST','/api/runs',json.dumps({'questions':QUESTIONS,'candidate_id':candidate_id}),headers)[0],400)
            status,body=request('POST','/api/runs',json.dumps({'questions':QUESTIONS,'candidate_id':selected}),headers)
            self.assertEqual(status,202);single=self.wait(m,json.loads(body)['id']);self.assertEqual(len(single['rows']),1)
            self.assertEqual(single['rows'][0]['id'],selected)
            for scope in (None,{},[],123,'unknown'):
                self.assertEqual(request('POST','/api/runs',json.dumps({'questions':QUESTIONS,'scope':scope}),headers)[0],400)
            self.assertEqual(request('POST','/api/runs',json.dumps({'questions':QUESTIONS,'candidate_id':selected,'scope':'bay-area'}),headers)[0],400)
            g.save(self.path,five_county_fixture())
            status,body=request('POST','/api/runs',json.dumps({'questions':QUESTIONS,'scope':'bay-area'}),headers)
            self.assertEqual(status,202);bay=self.wait(m,json.loads(body)['id'])
            self.assertEqual(bay['scope'],'bay-area');self.assertEqual(len(bay['rows']),9)
        finally:server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
