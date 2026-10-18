"""Offline regressions for image evidence, stale review gates and external image URLs."""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import campaign_endorsements as campaign
from capture_endorsement_images import capture
from endorsement_images import images_from_html, VERSION, validate_published_images
from endorsement_extract import candidates_from_data, uid, norm
from publication_reviews import file_sha
from review_endorsement_images import decisions, selected_images, build_review, build_queue, export_ledger

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())




class ImageResearchChecks(unittest.TestCase):
    def test_dom_context_does_not_use_offsets_in_stripped_text(self):
        html = '<div data-layout="' + ('x' * 1000) + '"></div><section><h2>Endorsements</h2><article><img src="/ag-bonta.jpg"><p>Rob Bonta</p></article><article><img src="/unknown.png"><p>Other card</p></article></section>'
        images = images_from_html(html, 'https://example.org/endorsements')
        self.assertEqual(images[0]['nearby'], 'Rob Bonta')
        self.assertEqual(images[0]['heading'], 'Endorsements')
        self.assertNotIn('Other card', images[0]['nearby'])
        self.assertEqual(images[0]['alt'], '')
        self.assertEqual(images[0]['filename'], 'ag-bonta.jpg')

    def test_logo_only_pages_do_not_require_forty_readable_characters(self):
        from unittest.mock import Mock
        fetcher=Mock()
        fetcher.request.return_value=(b'<h1>Endorsements</h1><img src="/opaque.png" alt="">','text/html','https://example.org/endorsements')
        page=campaign.fetch_page_with_images(fetcher,'https://example.org/endorsements')
        self.assertEqual(len(page['images']),1)
        self.assertTrue(page['text_limited'])
        self.assertEqual(page['image_parser_version'],VERSION)

    def test_unknown_logos_lazy_loading_and_large_inventories_survive(self):
        html = '<h1>Endorsements</h1>' + ''.join(f'<img data-src="/{i}.png" alt="">' for i in range(160))
        packet = capture(html.encode(), 'https://example.org/endorsements', '2026-10-17')
        self.assertEqual(len(packet['images']), 160)
        review = decisions(packet, 'capture-hash', 'all-content')
        self.assertEqual(len(selected_images(packet, review, 'capture-hash')), 160)
        self.assertTrue(all(i['alt'] == '' for i in packet['images']))

    def test_review_requires_all_items_and_exact_capture(self):
        packet = capture(b'<img src="/one.png"><img src="/two.png"><img src="data:image/png,123">', 'https://example.org/endorsements', '2026-10-17')
        review = decisions(packet, 'capture-hash', 'all-content')
        with self.assertRaisesRegex(ValueError, 'unresolved_reason'):
            selected_images(packet, review, 'capture-hash')
        review['unresolved_reason'] = 'Inline image needs separate browser review; no absence inference.'
        self.assertEqual(len(selected_images(packet, review, 'capture-hash')), 2)
        with self.assertRaisesRegex(ValueError, 'Stale'):
            selected_images(packet, review, 'different-hash')
        review['items'].pop()
        with self.assertRaisesRegex(ValueError, 'Every inventory'):
            selected_images(packet, review, 'capture-hash')

    def test_filename_proposals_and_legacy_decisions_cannot_publish(self):
        db = campaign.connect(':memory:')
        db.execute('INSERT INTO proposals VALUES(?,?,?,?,?,?)', ('F-old','K-site','C-person',json.dumps({'endorser':'ag bonta'}),'filename_gate','2026-10-11'))
        db.execute('INSERT INTO decisions VALUES(?,?,?,?,?)', ('F-old','accept','old filename decision','old reviewer','2026-10-11'))
        self.assertEqual(campaign.export_accepted(db), {})
        self.assertNotIn('endorsements', campaign.propose_logos(db))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'review.json'; path.write_text(json.dumps([{'proposal_id':'F-old','action':'accept','reason':'Not sufficient source evidence','reviewed_by':'fixture'}]))
            with self.assertRaisesRegex(ValueError,'unverified-gate'):
                campaign.apply_review(db,path)
        db.close()

    def test_exact_page_name_quote_and_capture_bindings(self):
        db = campaign.connect(':memory:')
        row = next(iter(candidates_from_data(DATA).values()))
        key='K-fixture'; url='https://example.org/endorsements'
        db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?)',(key,'https://example.org/',json.dumps([row['id']]),'crawled',None,'2026-10-17'))
        packet=capture(b'<h1>Endorsements</h1><p>Rob Bonta endorses this candidate.</p><img src="/misleading.jpg" alt="Imaginary Union">',url,'2026-10-17')
        page={'text':packet['text'],'images':packet['images'],'image_parser_version':VERSION}
        db.execute('INSERT INTO pages VALUES(?,?,?,?,?)',(key,url,'sha-current','2026-10-17T12:00:00Z',json.dumps(page)))
        result={'_extractor_version':VERSION,'endorsements':[
            {'endorser':'Rob Bonta','quote':'Rob Bonta endorses this candidate.','source_url':url},
            {'endorser':'Imaginary Union','quote':'Imaginary Union','source_url':url},
            {'endorser':'Rob Bonta','quote':'Rob Bonta endorses this candidate.','source_url':'https://example.org/about'},
            {'endorser':'Gun Sense Candidate','quote':'Gun Sense Candidate distinction','source_url':url}]}
        db.execute('INSERT INTO results VALUES(?,?,?,?)',(key,'fixture',json.dumps(result),'2026-10-17'))
        report=campaign.propose(db); self.assertEqual(report['proposed'],1);self.assertEqual(report['held'],3)
        p=db.execute('SELECT * FROM proposals').fetchone();record=json.loads(p['record_json'])
        self.assertEqual(record['url'],url);self.assertEqual(record['checked_on'],'2026-10-17')
        db.execute('INSERT INTO decisions VALUES(?,?,?,?,?)',(p['proposal_id'],'accept','Explicit page-local assertion reviewed','fixture','2026-10-17'))
        self.assertTrue(campaign.export_accepted(db))
        db.execute("UPDATE pages SET sha='sha-images-changed'")
        self.assertEqual(campaign.export_accepted(db),{})
        db.close()

    def test_refresh_reuses_observation_when_dom_index_moves(self):
        position, person = next((p,c) for p in DATA['positions'] for c in p.get('candidates') or [] if c.get('campaign_url'))
        url = person['campaign_url'].rstrip('/') + '/endorsements'
        packet = capture(b'<h1>Endorsements</h1><img src="/unknown.png">',url,'2026-10-17')
        review = decisions(packet,'first','all-content')
        first = build_review(DATA, packet, review, 'first', position['id'], person['name'], 'test-image-refresh')
        data = deepcopy(DATA)
        target = next(c for p in data['positions'] if p['id']==position['id'] for c in p['candidates'] if c['name']==person['name'])
        before = first['decisions'][0]['after']; target['endorsement_images']=[before]
        packet = capture(b'<img src="/new.png"><h1>Endorsements</h1><img src="/unknown.png">',url,'2026-10-17')
        review = decisions(packet,'second','all-content')
        refreshed = build_review(data, packet, review, 'second', position['id'], person['name'], 'test-image-refresh')
        existing_change = next(d for d in refreshed['decisions'] if d['after']['image_url'].endswith('/unknown.png'))
        self.assertEqual(existing_change['before'], before)
        self.assertEqual(existing_change['after']['id'], before['id'])
        self.assertEqual(sum(d['before'] is None for d in refreshed['decisions']), 1,
                         'DOM reordering updates the prior capture rather than adding a duplicate')
        self.assertFalse(campaign.contains_text('Joanne Lee endorses', 'Anne Lee'))

    def test_batch_queue_preserves_unknown_images_and_reports_unavailable_sites(self):
        row = next(c for c in candidates_from_data(DATA).values() if c.get('campaign_url'))
        url = row['campaign_url'].rstrip('/') + '/endorsements'
        packet = capture(b'<nav><img src="/opaque.png"></nav><h1>Endorsements</h1><img src="/opaque.png" alt="">',url,'2026-10-17')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); db_path=root/'campaign.sqlite3'; db=campaign.connect(db_path)
            db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?)',('K-fixture',row['campaign_url'],json.dumps([row['id']]),'crawled',None,'2026-10-17'))
            page={'text':packet['text'],'images':packet['images'],'image_parser_version':VERSION,'source_sha256':packet['source_sha256']}
            db.execute('INSERT INTO pages VALUES(?,?,?,?,?)',('K-fixture',url,'source-hash','2026-10-17T12:00:00Z',json.dumps(page)))
            db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?)',('K-unavailable','https://unavailable.example.org/','[]','blocked','Fixture source unavailable','2026-10-17'))
            db.commit();db.close()
            report=export_ledger(db_path,root/'packets',DATA)
            self.assertEqual(report['items'],2);self.assertEqual(report['ready'],1)
            queue=json.loads(Path(report['queue']).read_text())
            update=build_queue(DATA,queue,'test-image-batch','2026-10-17')
            self.assertEqual(len(update['outstanding_queue']),1)
            self.assertEqual(len(update['decisions']),1)
            self.assertEqual(update['decisions'][0]['after']['original_alt'],'')
            self.assertTrue(update['decisions'][0]['after']['image_url'].endswith('/opaque.png'))
            self.assertNotIn('endorser',update['decisions'][0]['after'])

    def test_jev_entry_prompt_and_legacy_cache_migration(self):
        from jev_review_proposals import q_instructions, ensure_state_table, CRITERIA
        import sqlite3
        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE jev_triage(proposal_id TEXT PRIMARY KEY, site_key TEXT, choice TEXT, p_endorse REAL, reviewed_at TEXT)')
        ensure_state_table(db)
        self.assertTrue({'model','policy_version','answer_json'} <= {r[1] for r in db.execute('PRAGMA table_info(jev_triage)')})
        prompt = q_instructions({'url':'https://example.org/endorsements','endorser':'Example Group','quote':'Example Group endorses'},'Actual captured context')
        self.assertIn('specific proposed identity and exact quote',prompt)
        self.assertTrue({'distinction','unclear','other_relationship'} <= set(CRITERIA))
        db.close()

    def test_jev_main_cache_and_stale_source_export(self):
        import contextlib, io
        import jev_review_proposals as jev
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); db_path=path/'campaign.sqlite3';db=campaign.connect(db_path)
            row=next(c for c in candidates_from_data(DATA).values() if c.get('campaign_url'))
            url=row['campaign_url'].rstrip('/')+'/endorsements'
            packet=capture(b'<h1>Endorsements</h1><p>Rob Bonta endorses this candidate.</p>',url,'2026-10-17')
            page={'text':packet['text'],'images':[],'image_parser_version':VERSION}
            db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?)',('K-test',row['campaign_url'],json.dumps([row['id']]),'crawled',None,'2026-10-17'))
            db.execute('INSERT INTO pages VALUES(?,?,?,?,?)',('K-test',url,'snapshot','2026-10-17T12:00:00Z',json.dumps(page)))
            result={'_extractor_version':VERSION,'endorsements':[{'endorser':'Rob Bonta','quote':'Rob Bonta endorses this candidate.','source_url':url}]}
            db.execute('INSERT INTO results VALUES(?,?,?,?)',('K-test','fixture',json.dumps(result),'2026-10-17'));db.commit()
            campaign.propose(db);db.close()
            output=path/'new-directory'/'decisions.json'
            def answer(state,questions,key):
                return {'model':jev.MODEL,'answers':{qid:{'choice':'endorsement','probabilities':{'endorsement':.9}} for qid in questions}}
            with patch.object(jev,'DEFAULT_DB',db_path), patch.object(jev.sys,'argv',['jev','--out',str(output)]), patch.dict(jev.os.environ,{'TYPESAFE_API_KEY':'invented-fixture-key'}), patch.object(jev.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
                with patch.object(jev,'post',side_effect=answer) as provider:
                    jev.main();self.assertEqual(provider.call_count,1)
                    jev.main();self.assertEqual(provider.call_count,1,'Unchanged source/model/policy must reuse cache')
                self.assertEqual(len(json.loads(output.read_text())),1)
                db=campaign.connect(db_path);db.execute("UPDATE pages SET sha='changed-images'");db.commit();db.close()
                with patch.object(jev,'post') as provider:
                    jev.main();self.assertFalse(provider.called)
                self.assertEqual(json.loads(output.read_text()),[],'Cached classifier answers cannot export against stale evidence')

    def test_complete_committed_source_dispositions_and_external_urls(self):
        base=ROOT/'research/endorsements/image-captures-2026-10-17'
        expected={'wiener':(131,50),'panetta-endorsements':(35,23),'pellerin-endorsements':(26,20),'chan-endorsements':(129,83)}
        for name,(total,included) in expected.items():
            path=base/(name+'.json');packet=json.loads(path.read_text())
            review=json.loads((base/(name+'-decisions.json')).read_text())
            self.assertEqual(len(packet['images']),total)
            self.assertEqual(len(selected_images(packet,review,file_sha(path))),included)
        self.assertFalse(validate_published_images(DATA, ROOT))
        from schema_validation import check, SCHEMA
        records = [r for p in DATA['positions'] for c in p.get('candidates') or [] for r in c.get('endorsement_images', [])]
        for record in records:
            self.assertTrue(record['image_url'].startswith('https://'))
            self.assertFalse({'asset_path', 'image_sha256'} & record.keys())
        self.assertTrue(check({**records[0], 'asset_path': 'assets/copied.png'}, SCHEMA['$defs']['endorsementImage']))
        wiener=next(c for p in DATA['positions'] for c in p.get('candidates') or [] if c['name']=='Scott Wiener')
        self.assertEqual(len(wiener['endorsement_images']),50)
        self.assertFalse({'ag bonta','Asm Grayson','meeno Monique Limon added'} & {r['endorser'] for r in wiener['endorsements']})
        self.assertEqual(sum(r.get('verification')=='campaign_claim' and r['url']=='https://www.scottwiener.com/endorsements' for r in wiener['endorsements']),53)


if __name__ == '__main__':
    unittest.main()
