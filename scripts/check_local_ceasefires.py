"""Offline checks for shared California action research and refresh coverage."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ballotpedia_endorsements import save, digest, dump
from check_evidence import check_evidence
import research_gaza_gaps as gaps
import research_local_ceasefires as local

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())


def html(heading, rows):
    return ('<title>Ceasefire Tracker</title><p>The below ceasefire tracker provides information about local elected officials’ statements or votes on a ceasefire in the Israeli war on Gaza.</p><h2>'+heading+'</h2>'
            '<table class="ea-advanced-data-table">'+''.join('<tr><td>'+n+'</td><td>'+a+'</td></tr>' for n,a in rows)+'</table>')


class LocalActionChecks(unittest.TestCase):
    def test_full_qualified_row_is_preserved(self):
        raw = html('Santa Clara City Council – December 19, 2023', [
            ('Councilmember Kevin Park', 'Supported Ceasefire Resolution; supported “United Against Hate” Resolution'),
            ('Councilmember Karen Hardy', 'Opposed Ceasefire Resolution; supported “United Against Hate” Resolution')]).encode()
        captured = local.capture(raw, '2026-10-23')
        claims, rows = local.proposals(DATA, captured, Path('/fixture'))
        park = next(c for c in claims if c['candidate']=='Kevin Park')
        self.assertEqual(park['record']['date'], '2023-12-19')
        self.assertIn('United Against Hate', park['record']['quote'])
        self.assertIn('Opposed', next(c for c in claims if c['candidate']=='Karen Hardy')['record']['summary'])

    def test_missing_tables_or_date_fail_closed(self):
        for raw in [b'<title>Tracker</title><p>Ceasefire Tracker has text but no tables. This is an incomplete scrape.</p>',
                    html('Santa Clara City Council – Bad date', [('Kevin Park','Supported ceasefire resolution')]).encode()]:
            with self.assertRaises(ValueError): local.capture(raw, '2026-10-23')

    def test_block_wrapped_cells_use_actual_text_without_inventing_separator(self):
        raw=html('Santa Clara City Council – December 19, 2023', [('Councilmember Kevin Park','Supported ceasefire resolution')])
        raw=raw.replace('<td>','<td><p>').replace('</td>','</p></td>')
        captured=local.capture(raw.encode(),'2026-10-23')
        claims,_=local.proposals(DATA,captured,Path('/fixture'))
        self.assertEqual(len(claims),1);self.assertNotIn('|',claims[0]['record']['quote'])

    def test_duplicate_rosters_and_conflicting_headings_are_held(self):
        rows = [('Councilmember Kevin Park', 'Supported ceasefire resolution')]
        raw = html('Santa Clara City Council – December 19, 2023', rows)+html('Different City Council – January 1, 2024', rows)
        c = local.capture(raw.encode(), '2026-10-23')
        claims, dispositions = local.proposals(DATA, c, Path('/fixture'))
        self.assertFalse(claims); self.assertTrue(all(s['holds'] for s in c['sections']))
        raw = html('Santa Clara City Council – December 19, 2023', rows)+html('Santa Clara City Council – December 19, 2023', [('Another Person','Abstained')])
        c = local.capture(raw.encode(), '2026-10-23');self.assertTrue(all(s['holds'] for s in c['sections']))

    def test_na_malformed_and_unspecified_amendments_are_not_stances(self):
        raw=html('Santa Clara City Council – December 19, 2023', [('Councilmember Kevin Park','N/A'),
            ('Councilmember Tom Cline Opposed','ceasefire resolution'),('Councilmember Karen Hardy','Supported amendment')]).encode()
        c=local.capture(raw,'2026-10-23');claims,_=local.proposals(DATA,c,Path('/fixture'))
        self.assertFalse(claims);self.assertTrue(all(r['holds'] for r in c['sections'][0]['rows']))

    def test_existing_evidence_never_excludes_shared_refresh(self):
        data=deepcopy(DATA)
        for p in data['positions']:
            for c in p.get('candidates') or []:
                if c['name']=='Kevin Park':c['gaza_evidence']=[{'id':'GE-9999'}]
        raw=html('Santa Clara City Council – December 19, 2023',[('Councilmember Kevin Park','Supported ceasefire resolution')]).encode()
        claims,_=local.proposals(data,local.capture(raw,'2026-10-23'),Path('/fixture'))
        self.assertEqual(claims[0]['candidate'],'Kevin Park')
        self.assertFalse(gaps.plan(data,['Kevin Park'])['candidates'])
        self.assertEqual(len(gaps.plan(data,['Kevin Park'],True,'CA')['candidates']),1)
        self.assertFalse(gaps.plan(data,['Kevin Park'],True,'TX')['candidates'])

    def test_jurisdiction_search_and_shared_source_are_explicit_leads(self):
        row=gaps.plan(DATA,['Kevin Park'],True,'CA')['candidates'][0]
        self.assertIn(local.URL,row['direct_source_urls'])
        query=gaps.search_queries(row)[0]
        self.assertIn('Santa Clara',query);self.assertIn('resolution',query)

    def test_undated_congress_assessment_never_receives_a_vote_date(self):
        raw=html('Congressional Members',[('Rep. Kevin Mullin','Has failed to support ceasefire')]).encode()
        claims,_=local.proposals(DATA,local.capture(raw,'2026-10-23'),Path('/fixture'))
        r=claims[0]['record'];self.assertEqual(r['date_method'],'source_observed')
        self.assertEqual(r['source_kind'],'voter_guide');self.assertIn('not a current vote',r['summary'])

    def test_article_body_excludes_comments_and_captures_publication_metadata(self):
        raw=b'<title>Opinion</title><meta property="article:published_time" content="2023-12-26T18:57:54+00:00"><div class="dynamic-entry-content"><p>Kevin Park championed the Gaza ceasefire resolution; the effort was blocked.</p></div><div id="comments">Commenter claims every candidate supported genocide.</div>'
        p=gaps.capture(raw,'https://example.org/story','2026-10-23','article-html')
        self.assertNotIn('Commenter',p['text']);self.assertEqual(p['published_date'],'2023-12-26')
        claim={'position_id':'CA2026-106','candidate':'Kevin Park','field':'gaza_evidence',
               'record':{'quote':'Kevin Park championed','date_method':'page_metadata','date':'2023-12-25'}}
        with tempfile.TemporaryDirectory() as temp,patch.object(gaps,'ask') as ask:
            with self.assertRaisesRegex(ValueError,'publication metadata'):gaps.review_claim(DATA,claim,p,Path(temp),'fixture')
            ask.assert_not_called()

    def test_identity_bridge_requires_actual_source_bytes_and_substring(self):
        raw=b'<title>Kevin Park</title><p>Kevin Park serves on Santa Clara City Council and is running for Mayor.</p>'
        p=gaps.capture(raw,'https://example.org/biography','2026-10-23')
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);(temp/'raw.html').write_bytes(raw);save(temp/'packet.json',p)
            claim={'position_id':'CA2026-106','candidate':'Kevin Park','field':'gaza_evidence',
                   'record':{'quote':'Kevin Park serves'},'identity_captures':[{'capture':str(temp/'packet.json'),'raw_capture':str(temp/'raw.html'),'context':'Invented identity biography'}]}
            with self.assertRaisesRegex(ValueError,'Identity context absent'):gaps.review_claim(DATA,claim,p,temp,'fixture')

    def test_excerpt_join_marker_cannot_become_an_invented_source_quote(self):
        raw=b'<title>Source</title><p>Kevin Park supported a ceasefire resolution.</p><p>The attempt to introduce the resolution was blocked.</p>'
        p=gaps.capture(raw,'https://example.org/story','2026-10-23')
        claim={'position_id':'CA2026-106','candidate':'Kevin Park','field':'gaza_evidence',
               'contexts':['Kevin Park supported a ceasefire resolution.','The attempt to introduce the resolution was blocked.'],
               'record':{'quote':'[separate source excerpt]'}}
        with tempfile.TemporaryDirectory() as temp,self.assertRaisesRegex(ValueError,'absent from actual'):
            gaps.review_claim(DATA,claim,p,Path(temp),'fixture')

    def test_repeated_actions_keep_distinct_dates_without_duplicate_same_event(self):
        base={'id':'GE-99998','date':'2023-10-25','url':local.URL,'quote':'Supported ceasefire resolution','summary':'Tracker reports support for a ceasefire resolution.','checked_on':'2026-10-23','dimension':'actions_votes','source_kind':'advocacy_tracker','date_method':'source_stated'}
        d={'positions':[{'id':'fixture','candidates':[{'name':'Fixture Person','gaza_evidence':[base,{**base,'id':'GE-99999','date':'2024-04-30'}]}]}]}
        self.assertFalse(check_evidence(d,[]))
        d['positions'][0]['candidates'][0]['gaza_evidence'][1]['date']=base['date']
        self.assertTrue(any('duplicate source' in e for e in check_evidence(d,[])))
        for e in d['positions'][0]['candidates'][0]['gaza_evidence']:
            e['source_kind']='x_post'
        d['positions'][0]['candidates'][0]['gaza_evidence'][1]['date']='2024-04-30'
        self.assertTrue(any('duplicate source' in e for e in check_evidence(d,[])))

    def test_actual_source_has_a_disposition_for_every_row_and_real_model_bindings(self):
        source=json.loads((ROOT/'research/gaza-sources/cair-ceasefire-tracker-2026-10-23.json').read_text())
        audit=json.loads((ROOT/'research/reviews/cair-local-ceasefire-evidence-2026-10-23.audit.json').read_text())
        row_ids={r['id'] for s in source['sections'] for r in s['rows']}
        self.assertEqual(len(source['sections']),33);self.assertEqual(len(row_ids),214)
        self.assertEqual(row_ids,{r['row_id'] for r in audit['source_dispositions']})
        for ref,decision in audit['model_decisions'].items():
            self.assertEqual(ref,digest(dump(decision['request']).encode()))
            self.assertEqual(decision['request']['model'],'jev-1.14.0')
            self.assertEqual(decision['response']['model'],'jev-1.14.0')

    def test_kevin_records_preserve_source_roles_dates_and_failed_outcome(self):
        c=next(c for p in DATA['positions'] for c in p.get('candidates') or [] if c['name']=='Kevin Park')
        rows=[e for e in c['gaza_evidence'] if e['url'] in {local.URL,'https://www.svvoice.com/op-ed-we-will-prevail-inshaallah-opinion/'}]
        self.assertEqual(len(rows),2)
        tracker=next(r for r in rows if r['source_kind']=='advocacy_tracker')
        opinion=next(r for r in rows if r['source_kind']=='opinion')
        self.assertEqual(tracker['date'],'2023-12-19');self.assertIn('United Against Hate',tracker['quote'])
        self.assertEqual(opinion['date'],'2023-12-26');self.assertIn('blocked',opinion['summary'])
        self.assertIn('Sameena Usman',opinion['summary'])


if __name__=='__main__': unittest.main()
