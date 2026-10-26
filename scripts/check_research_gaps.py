"""Offline regressions for new-race image, publisher and Gaza research gaps."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import import_hapac as hapac
import research_gaza_gaps as gaza
import review_endorsement_images as images
from capture_endorsement_images import capture
from publication_reviews import file_sha
from ballotpedia_endorsements import dump, digest, save, MODEL

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())


def target(data, name='Amish Shah'):
    return next((p,c) for p in data['positions'] for c in p.get('candidates') or [] if c['name']==name)


def response(request, accepted=True):
    out={}
    for k,q in request['questions'].items():
        value={'relationship':'current','identity':'match','meaning':'faithful','date':'supported'}[k]
        out[k]={'type':'choice','choice':value,'probabilities':{v:(1. if accepted and v==value else 0.) for v in q['criteria']}}
    return {'model':MODEL,'answers':out}


def mocked_ask(work,state,questions,key):
    req={'model':MODEL,'state':state,'questions':questions};ref=digest(dump(req).encode());r=response(req)
    save(work/'decisions'/(ref+'.json'),{'request':req,'response':r});return r['answers'],ref


class ImageScopeChecks(unittest.TestCase):
    def setUp(self):
        self.data=deepcopy(DATA);self.p,self.c=target(self.data);self.c.pop('endorsement_images',None)
        self.url=self.c['campaign_url'].rstrip('/')+'/endorsements'
        self.raw=('<header><img src="/brand.png"></header><h1>Endorsements</h1><h2>Organizations</h2>'+''.join('<img src="/opaque'+str(i)+'.png" alt="">' for i in range(31))).encode()

    def test_nationwide_queue_publishes_empty_alt_logos_without_name_inference(self):
        packet=capture(self.raw,self.url,'2026-10-23')
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'packet.json';save(f,packet);dp=Path(temp)/'decisions.json';save(dp,images.decisions(packet,file_sha(f),'all-content'))
            queue={'items':[{'status':'ready','capture':str(f),'decisions':str(dp),'candidates':[{'position_id':self.p['id'],'candidate':self.c['name']}]}]}
            review=images.build_queue(self.data,queue,'fixture-house-images','2026-10-23')
            self.assertEqual(len(review['decisions']),31);self.assertFalse(review['outstanding_queue']);self.assertTrue(review['counties'])
            self.assertTrue(all(d['after']['original_alt']=='' and 'endorser' not in d['after'] for d in review['decisions']))

    def test_provisional_nationwide_image_target_keeps_its_roster(self):
        p,c=self.p,self.c;p['filed_candidates_not_confirmed_on_ballot']=p['candidates'];p['candidates']=None
        packet=capture(self.raw,self.url,'2026-10-23');dispositions=images.decisions(packet,'sha','all-content')
        result=images.build_review(self.data,packet,dispositions,'sha',p['id'],c['name'],'fixture-provisional')
        self.assertEqual(len(result['decisions']),31);self.assertIsNone(p['candidates'])

    def test_missing_plan_uses_current_roster_and_published_source_not_old_batch(self):
        plan=images.plan_missing(self.data,True)
        self.assertTrue(any(e['candidates'][0]['candidate']=='Amish Shah' for e in plan['items']))
        self.c['endorsement_images']=[{'source_url':self.url,'image_url':'https://example.org/old.png','checked_on':'2026-10-23'}]
        self.assertFalse(any(e['candidates'][0]['candidate']=='Amish Shah' for e in images.plan_missing(self.data,True)['items']))
        self.c['endorsement_images'][0]['checked_on']='2026-01-01'
        self.assertTrue(any(e['candidates'][0]['candidate']=='Amish Shah' for e in images.plan_missing(self.data,True)['items']))

    def test_actual_shah_capture_retains_all_31_organization_images(self):
        q=json.loads((ROOT/'research/endorsements/image-gaps-2026-10-23/queue.json').read_text())
        row=next(r for r in q['items'] if r['candidates'][0]['candidate']=='Amish Shah')
        p=json.loads(Path(row['capture']).read_text());d=json.loads(Path(row['decisions']).read_text())
        selected=images.selected_images(p,d,file_sha(row['capture']))
        logos=[i for i in p['images'] if i['heading']=='Organizations']
        self.assertEqual(len(logos),31);self.assertTrue(all(i['alt']=='' for i in logos))
        self.assertTrue({i['src'] for i in logos}<={i['src'] for i in selected})

    def test_responsive_lazy_placeholder_uses_actual_supplied_url(self):
        raw=b'<h1>Endorsements</h1><img src="data:image/gif;base64,placeholder" data-src-desktop-1x="//cdn.example.org/opaque.png" alt="">'
        p=capture(raw,self.url,'2026-10-23')
        self.assertFalse(p['unresolved_images']);self.assertEqual(p['images'][0]['src'],'https://cdn.example.org/opaque.png')
        self.assertEqual(p['images'][0]['alt'],'')

    def test_old_review_packets_replay_but_new_captures_use_updated_parser(self):
        from endorsement_images import VERSION
        p=capture(self.raw,self.url,'2026-10-23');self.assertEqual(p['version'],VERSION)
        p['version']='campaign-dom-images-2';d=images.decisions(p,'old-packet-sha','all-content')
        self.assertEqual(len(images.selected_images(p,d,'old-packet-sha')),31)
        with self.assertRaises(ValueError):images.selected_images(p,d,'different-sha')

    def test_capture_rerun_preserves_existing_queue_before_network(self):
        with tempfile.TemporaryDirectory() as temp,patch('research_endorsements.Fetcher.request') as fetch:
            directory=Path(temp)/'run';directory.mkdir()
            queue=directory/'queue.json';original=b'{"items": [], "previous_run": true}\n';queue.write_bytes(original)
            with self.assertRaisesRegex(ValueError,'fresh output directory'):
                images.capture_plan({'items':[{'url':self.url}]},directory,'2026-10-23')
            fetch.assert_not_called();self.assertEqual(queue.read_bytes(),original)


    def test_batch_runner_makes_separate_image_publication_draft(self):
        import run_campaign_endorsement_batch as runner
        with tempfile.TemporaryDirectory() as temp,patch.object(runner,'RUN',Path(temp)),patch.object(runner.subprocess,'run',return_value=Mock(returncode=0)) as run,patch.dict(runner.os.environ,{},clear=True):
            self.assertEqual(runner.main(),0)
            commands=[c.args[0] for c in run.call_args_list]
            self.assertTrue(any('build-queue' in c for c in commands))
            status=json.loads((Path(temp)/'status.json').read_text());self.assertEqual(status['publication'],'not applied')


class PublisherChecks(unittest.TestCase):
    def setUp(self):
        self.raw=b'<h2>Current Endorsements</h2><p>Representatives and Federal Candidates: Amish Shah</p><p>State Legislators and Candidates: Other Person</p><p>Local Officials and Candidates: Another Person</p><p>Previously Endorsed Officials not up for election in 2026: Old Person</p><h3>Representatives and Federal Candidates</h3><h4>Dr. Amish Shah, Arizona 1st Congressional District</h4><p>Candidate for Congress, former state representative.</p><h4>Old Person</h4><p>Old biography.</p>'
        self.packet=hapac.capture(self.raw,'2026-10-23')

    def test_explicit_current_list_not_biographies_controls_matching(self):
        self.assertEqual([c['name'] for c in self.packet['cards']],['Amish Shah','Other Person','Another Person'])
        self.assertNotIn('Old Person',[c['name'] for c in self.packet['cards']])

    def test_missing_or_changed_current_layout_is_held(self):
        with self.assertRaises(ValueError):hapac.capture(b'<h2>Past endorsements</h2>Amish Shah','2026-10-23')
        with self.assertRaises(ValueError):hapac.capture(self.raw.replace(b'Local Officials and Candidates:',b'Local:'),'2026-10-23')

    def test_current_corroboration_is_not_added_twice(self):
        data=deepcopy(DATA);p,c=target(data)
        c['endorsements']=[{'endorser':hapac.PUBLISHER,'relation':'endorsed','phase':'unspecified','url':hapac.URL}]
        with tempfile.TemporaryDirectory() as temp,patch.object(hapac,'ask',side_effect=mocked_ask),patch.object(hapac,'prepare'):
            r,a=hapac.build(data,self.packet,Path(temp),'fixture','fixture-hapac')
        self.assertEqual(r['card_dispositions'][0]['status'],'corroboration');self.assertFalse(any(d['action']=='change' for d in r['decisions']))

    def test_historical_record_does_not_block_explicit_current_renewal(self):
        data=deepcopy(DATA);p,c=target(data);old={'endorser':hapac.PUBLISHER,'relation':'endorsed','phase':'unspecified','url':hapac.URL,'historical':True};c['endorsements']=[old]
        with tempfile.TemporaryDirectory() as temp,patch.object(hapac,'ask',side_effect=mocked_ask),patch.object(hapac,'prepare'):
            r,a=hapac.build(data,self.packet,Path(temp),'fixture','fixture-hapac')
        self.assertEqual(r['card_dispositions'][0]['status'],'added');self.assertEqual(c['endorsements'],[old])

    def test_actual_publisher_capture_accounts_for_every_current_card(self):
        r=json.loads((ROOT/'research/reviews/hapac-current-endorsements-2026-10-23.json').read_text())
        self.assertEqual(len(r['card_dispositions']),17)
        self.assertEqual(next(d for d in r['card_dispositions'] if d.get('candidate')=='Amish Shah')['status'],'added')
        self.assertEqual(next(d for d in r['card_dispositions'] if d.get('candidate')=='Melissa Hernandez')['status'],'corroboration')


class GazaGapChecks(unittest.TestCase):
    def setUp(self):
        self.data=deepcopy(DATA);p,c=target(self.data,'Jay Feely');c.pop('gaza_evidence',None);c.pop('gaza_platform',None)
        self.p,self.c=p,c
        self.url=c['campaign_url'].rstrip('/')+'/issues'
        self.raw=b'<title>Jay Feely for Congress</title><h1>Jay Feely for Congress in Arizona CD-1</h1><p>I will stand unapologetically with Israel and fight to strengthen the U.S.-Israel relationship.</p>'
        self.packet=gaza.capture(self.raw,self.url,'2026-10-23')
        self.claim={'position_id':p['id'],'candidate':c['name'],'field':'gaza_platform','record':{'quote':'I will stand unapologetically with Israel','summary':'Feely pledges to stand with Israel.','scope_note':'Only the recorded campaign issues page was checked.'},'date_basis':'Actual source observation on October 23, 2026, not an announcement date.'}

    def test_divestment_discovery_is_independent_of_gaza_and_current_office(self):
        row=gaza.plan(self.data,['Fiona Ma'],refresh_existing=True)['candidates'][0]
        self.assertIn('"Fiona Ma" Israel divestment',gaza.search_queries(row))
        self.assertIn('"Fiona Ma" Israel BDS boycott bonds investment',gaza.search_queries(row))
        self.assertEqual(row['search_version'],gaza.SEARCH_VERSION)
        for term in ('divestment','divesting','BDS'):
            self.assertTrue(gaza.relevant_lead({'link':'https://example.org/article','title':'Candidate interview','snippet':'Opposes '+term}))
        self.assertFalse(gaza.relevant_lead({'link':'https://example.org','title':'Housing only'}))
        self.assertFalse(gaza.relevant_lead({'link':'http://example.org','title':'Israel divestment'}))

    def test_dated_news_capture_checks_real_publication_metadata(self):
        raw=b'<title>Interview</title><time itemprop="datePublished" datetime="2024-05-16 09:01:00">May 16</time><p>The candidate opposed divestment from Israel in this interview.</p>'
        packet=gaza.capture(raw,'https://example.org/interview','2026-10-23','dated-html')
        self.assertEqual(packet['published_date'],'2024-05-16')
        with self.assertRaisesRegex(ValueError,'datePublished'):
            gaza.capture(raw.replace(b'datePublished',b'dateModified'),'https://example.org/interview','2026-10-23','dated-html')
        claim=deepcopy(self.claim);claim['field']='gaza_evidence';claim['record'].update(date='2026-10-23',date_method='page_metadata')
        with tempfile.TemporaryDirectory() as temp,patch.object(gaza,'ask') as judge:
            with self.assertRaisesRegex(ValueError,'date must match'):
                gaza.review_claim(self.data,claim,{**self.packet,'kind':'dated-html','published_date':'2024-05-16'},Path(temp),'fixture')
            judge.assert_not_called()

    def test_nested_verified_platform_sources_are_not_lost_to_homepage_only_crawl(self):
        rows=gaza.plan(self.data,['Jay Feely'])['candidates'];self.assertEqual(len(rows),1)
        self.assertIn(self.url,rows[0]['direct_source_urls']);self.assertEqual(rows[0]['status'],'needs_source_review')
        old=rows[0]['source_fingerprint'];self.c['campaign_url']+='?changed'
        self.assertNotEqual(gaza.plan(self.data,['Jay Feely'])['candidates'][0]['source_fingerprint'],old)

    def test_empty_old_done_flag_is_not_a_completion_proof(self):
        # The planner consumes current published records, never the old collector stage flags.
        self.assertTrue(gaza.plan(self.data,['Jay Feely'])['candidates'])
        self.c['gaza_evidence']=[{'id':'fixture'}];self.c['gaza_platform']={'status':'statement_found'}
        self.assertFalse(gaza.plan(self.data,['Jay Feely'])['candidates'])

    def test_invented_quote_or_context_fails_before_model(self):
        for k in ('quote','context'):
            c=deepcopy(self.claim)
            if k=='quote':c['record']['quote']='Invented policy statement'
            else:c['context']='Invented source context'
            with tempfile.TemporaryDirectory() as temp,self.assertRaises(ValueError):gaza.review_claim(self.data,c,self.packet,Path(temp),'fixture')

    def test_wrong_campaign_host_is_not_a_primary_platform(self):
        p=deepcopy(self.packet);p['source_url']='https://unrelated.example/statement'
        with tempfile.TemporaryDirectory() as temp,self.assertRaisesRegex(ValueError,'recorded candidate campaign'):
            gaza.review_claim(self.data,self.claim,p,Path(temp),'fixture')

    def test_each_identity_meaning_date_gate_must_pass(self):
        for field in ('identity','meaning','date'):
            def judge(work,state,questions,key):
                r=response({'questions':questions});a=r['answers'][field];a['probabilities'][a['choice']]=.1
                return r['answers'],'fixture'
            with tempfile.TemporaryDirectory() as temp,patch.object(gaza,'ask',side_effect=judge):
                self.assertFalse(gaza.review_claim(self.data,self.claim,self.packet,Path(temp),'fixture')[4])

    def test_packet_rehash_cannot_replace_actual_raw_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            raw=Path(temp)/'raw.html';raw.write_bytes(self.raw);p=deepcopy(self.packet);p['text']+=' changed';p.pop('packet_sha256');p['packet_sha256']=digest(dump(p).encode());f=Path(temp)/'packet.json';save(f,p)
            claim={**self.claim,'capture':str(f),'raw_capture':str(raw)}
            with self.assertRaisesRegex(ValueError,'actual captured source'):
                gaza.build(self.data,[claim],Path(temp),'fixture','fixture-gaza',date.today().isoformat())

    def test_x_author_and_timestamp_binding_and_future_capture(self):
        tid='1711221277787041963';timestamp=((int(tid)>>22)+1288834974657)/1000
        obj={'code':200,'tweet':{'id':tid,'text':'We support Israel and condemn attacks on civilians.','created_timestamp':timestamp,'author':{'screen_name':'DrAmishShah'}}}
        url='https://x.com/DrAmishShah/status/'+tid
        p=gaza.capture(json.dumps(obj).encode(),url,'2026-10-23','x-json');self.assertEqual(p['published_date'],'2023-10-09')
        obj['tweet']['author']['screen_name']='DifferentAuthor'
        with self.assertRaises(ValueError):gaza.capture(json.dumps(obj).encode(),url,'2026-10-23','x-json')
        with self.assertRaises(ValueError):gaza.capture(self.raw,self.url,'2099-01-01')

    def test_collection_failure_remains_pending_and_never_means_no_statement(self):
        with tempfile.TemporaryDirectory() as temp,patch('research_endorsements.Fetcher.request',side_effect=OSError('unavailable')):
            directory=Path(temp)/'run';gaza.collect(self.data,directory,['Jay Feely'],2)
            r=json.loads((directory/'manifest.json').read_text());self.assertEqual(r['publication'],'not applied')
            self.assertEqual(r['candidates'][0]['status'],'pending_claim_review');self.assertTrue(all(s['status']=='unavailable' for s in r['candidates'][0]['sources']))

    def test_actual_review_retains_historical_dates_and_current_platform_separately(self):
        r=json.loads((ROOT/'research/reviews/az01-gaza-gap-recovery-2026-10-23.json').read_text())
        changes=[d for d in r['decisions'] if d['action']=='change'];self.assertEqual(len(changes),6)
        self.assertTrue(any(d['after'].get('date')=='2023-10-09' for d in changes))
        self.assertTrue(any(d['field']=='gaza_platform' and d['after']['checked_on']=='2026-10-23' for d in changes))
        observed=next(d['after'] for d in changes if d['after'].get('date_method')=='source_observed');self.assertEqual(observed['source_kind'],'voter_guide');self.assertIn('not the date',observed['date_note'])

    def test_shared_guide_keeps_each_candidate_source_attribution(self):
        self.data=deepcopy(DATA)
        review=json.loads((ROOT/'research/reviews/az01-gaza-gap-recovery-2026-10-23.json').read_text())
        template=next(d['after'] for d in review['decisions'] if d['after'].get('date_method')=='source_observed')
        raw=b'<title>Fixture guide</title><p>Amish Shah supports Israel. Jay Feely supports Israel.</p>'
        with tempfile.TemporaryDirectory() as temp,patch.object(gaza,'ask',side_effect=mocked_ask):
            directory=Path(temp);rp=directory/'guide.raw';rp.write_bytes(raw);pp=directory/'guide.json'
            save(pp,gaza.capture(raw,'https://guide.example/2026','2026-10-23'))
            claims=[]
            for i,name in enumerate(['Amish Shah','Jay Feely']):
                p,c=target(self.data,name)
                record={**template,'id':'GE-800'+str(i),'quote':name+' supports Israel.',
                        'summary':'The fixture guide reports that '+name+' supports Israel.'}
                claims.append({'position_id':p['id'],'candidate':name,'field':'gaza_evidence','record':record,
                    'capture':str(pp),'raw_capture':str(rp),'publisher':'Fixture guide','role':'aggregator',
                    'identity_basis':'Exact named candidate in this source fixture.',
                    'date_basis':'Observation date of the guide, not the underlying statement date.'})
            result,_=gaza.build(self.data,claims,directory,'fixture','fixture-shared-guide',date.today().isoformat())
            self.assertEqual(len(result['decisions']),2)
            for decision in result['decisions']:
                self.assertEqual(result['sources'][decision['source_key']]['candidate'],decision['candidate'])


if __name__=='__main__':unittest.main()
