"""Regression checks for context, source identity and owner-defined community meaning."""
from copy import deepcopy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import evidence_context as e
import research_gaza_gaps as g
from candidate_community import community_state
from publish_jev_grades import validate_recommendation_evidence


class ContextChecks(unittest.TestCase):
    def test_official_bill_identity_dates_and_withdrawals(self):
        xml=b'<billStatus><bill><congress>119</congress><type>HR</type><number>3565</number><title>Bill title</title><cosponsors><item><bioguideId>K000389</bioguideId><fullName>Rep. Khanna, Ro</fullName><sponsorshipDate>2025-08-05</sponsorshipDate><sponsorshipWithdrawnDate>2026-01-01</sponsorshipWithdrawnDate></item></cosponsors></bill></billStatus>'
        url='https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr3565.xml'
        packet=e.billstatus_capture(xml,url)
        self.assertIn('"withdrawn_date":"2026-01-01"',packet['text'])
        self.assertIn('Bill title',packet['text'])
        for raw,source in [(xml,url.replace('3565','2411')),(xml,url.replace('govinfo.gov','example.org')),
                           (xml.replace(b'2025-08-05',b'2025-02-30'),url)]:
            with self.assertRaises(ValueError):e.billstatus_capture(raw,source)

    def test_context_binding_cannot_drift_to_another_record_or_person(self):
        record={'id':'GE-9999','summary':'Verified context'}
        candidate={'name':'Person','gaza_evidence':[record]};position={'id':'one'}
        entry={'id':'episode','position_id':'one','candidate':'Person','topic':'Timeline',
               'context':'Initial action, explanation and later action.',
               'bindings':[{'field':'gaza_evidence','id':'GE-9999','sha256':e.fingerprint(record)}]}
        doc={'entries':[entry]};before=deepcopy(candidate)
        self.assertEqual(len(e.contexts(position,candidate,doc)),1)
        self.assertEqual(e.contexts({'id':'other'},candidate,doc),[])
        self.assertEqual(candidate,before)
        candidate['gaza_evidence'][0]['summary']='Changed'
        with self.assertRaisesRegex(ValueError,'Stale'):e.contexts(position,candidate,doc)

    def test_negative_guide_claims_do_not_confuse_no_funding_with_no_support(self):
        self.assertTrue(e.NEGATIVE_BLOCK.search('has not signed block the bombs act'))
        self.assertTrue(e.NEGATIVE_BLOCK.search('no Block the Bombs support'))
        self.assertFalse(e.NEGATIVE_BLOCK.search('Does not currently take AIPAC money. Signed Block the Bombs.'))
        c={'name':'Person','gaza_voting_records':[{'actions':[{'action_id':'a','value':'Sponsor'}]}],
           'gaza_evidence':[{'id':'GE-9999','source_kind':'voter_guide','summary':'No Block the Bombs support.'}]}
        d={'positions':[{'id':'one','candidates':[c]}],'gaza_voting':{'actions':{'a':{'title':'Block the Bombs Act'}}}}
        self.assertEqual(len(e.research_leads(d)),1)
        c['gaza_evidence'][0]['summary']='Does not take AIPAC money. Signed Block the Bombs.'
        self.assertEqual(e.research_leads(d),[])

    def test_followup_queries_include_criticism_explanations_and_primary_sponsorship(self):
        queries=g.search_queries({'candidate':'Person','identity':{'jurisdiction':'Example'}})
        self.assertTrue(any('backlash' in q and 'debate' in q for q in queries))
        self.assertTrue(any('UNRWA' in q and 'explanation' in q for q in queries))
        self.assertTrue(any('Block the Bombs' in q and 'cosponsor' in q for q in queries))

    def test_verified_secondary_x_account_passes_without_allowing_lookalikes(self):
        c={'name':'Person','x_url':'https://x.com/Official','secondary_x_url':'https://x.com/Personal'}
        p={'id':'one','office':'Representative','jurisdiction':'Congress'}
        claim={'candidate':'Person','position_id':'one','field':'gaza_evidence','date_basis':'Verified post timestamp.',
               'record':{'date':'2026-01-16','summary':'Person explains their vote.','quote':'The explanation','date_method':'x_snowflake'}}
        packet={'kind':'x-json','text':'The explanation is a direct statement.','author_url':'https://x.com/Personal',
                'published_date':'2026-01-16','checked_on':'2026-10-27','source_url':'https://x.com/Personal/status/1','title':'Person post'}
        answer={k:{'choice':value,'probabilities':{value:1,'hold':0}} for k,value in [('identity','match'),('meaning','faithful'),('date','supported')]}
        with patch.object(g,'ask',return_value=(answer,'fixture')) as ask:
            self.assertTrue(g.review_claim({'positions':[{**p,'candidates':[c]}]},claim,packet,Path('.'),'',g.MODEL)[4])
            self.assertIn('Verified secondary X profile',ask.call_args.args[1])
            with self.assertRaisesRegex(ValueError,'verified candidate'):
                g.review_claim({'positions':[{**p,'candidates':[c]}]},claim,{**packet,'author_url':'https://x.com/Personal_other'},Path('.'),'',g.MODEL)

    def test_community_is_general_alignment_and_future_na_is_guarded(self):
        state=community_state({'id':'one'},{'name':'Person'}, {('one','Person'):{'part_of_muslim_community':True}})
        self.assertIn('pro-Palestine Muslim community',state['community_alignment_context'])
        row={'candidate':'Person','request':{'state':state}}
        with self.assertRaisesRegex(ValueError,'community alignment'):validate_recommendation_evidence({},row,'N/A')
        validate_recommendation_evidence({},row,'A')
        # The new semantic context cannot silently change immutable old grades.
        validate_recommendation_evidence({},{'candidate':'Person','request':{'state':{'part_of_muslim_community':True}}},'N/A')
        false=community_state({'id':'one'},{'name':'Person'},{('one','Person'):{'part_of_muslim_community':False}})
        self.assertEqual(false,{'part_of_muslim_community':False})

    def test_registered_contexts_and_all_gaza_followups_reach_state(self):
        from grade_gaza import build_state
        data=json.loads((e.ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())
        doc=json.loads(e.REGISTRY.read_text())
        import hashlib
        self.assertEqual(hashlib.sha256((e.ROOT/doc['review_path']).read_bytes()).hexdigest(),doc['review_sha256'])
        for entry in doc['entries']:
            p=next(p for p in data['positions'] if p['id']==entry['position_id'])
            c=next(c for c in p['candidates'] if c['name']==entry['candidate'])
            self.assertIn('reviewed_evidence_context',build_state(p,c,data))
        p={'id':'fixture','office':'Council'};c={'name':'Fixture','gaza_evidence':[{'id':f'GE-{9000+i}','date':'2026-01-01','summary':str(i),'dimension':'other'} for i in range(25)]}
        self.assertEqual(len(build_state(p,c,{'codes':{'party':{}}})['gaza_evidence']),25)

    def test_shared_vote_sequences_apply_beyond_the_sample_without_inventing_explanations(self):
        from grade_gaza import build_state
        data=json.loads((e.ROOT/'2026-11-03_Bay_Area_Elections.json').read_text())
        for name in ['John Garamendi','Sam Liccardo','Ro Khanna']:
            p,c=next((p,c) for p in data['positions'] for c in p.get('candidates') or [] if c['name']==name)
            groups=build_state(p,c,data)['reviewed_evidence_context']
            row=next(g for g in groups if g['topic']=='Related UNRWA legislative actions')
            self.assertIn('2026-01-14',row['context']);self.assertIn('2026-02-03',row['context'])
            self.assertNotIn('snuck',row['context'])
        broken=deepcopy(data)
        broken['gaza_voting']['actions']['119-house-V']['date_label']='2026-01-15'
        with self.assertRaisesRegex(ValueError,'Stale legislative action group'):build_state(p,c,broken)


if __name__=='__main__':unittest.main()
