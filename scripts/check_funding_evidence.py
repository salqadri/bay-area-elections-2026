"""Regression coverage for donor-specific years, scope and immutable evaluations."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from ballotpedia_endorsements import digest, dump
from funding_evidence import model_text, needs_review, organization_receipt, signature, policy
from grade_gaza import build_state
from research_funding_periods import observations, track_jpac_rows

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())


class FundingChecks(unittest.TestCase):
    def test_report_date_cannot_turn_historical_or_unknown_totals_into_recent_funding(self):
        e = {'id':'GE-9999','date':'2026','dimension':'aipac_funding',
             'summary':'Received $47,700 across 2021–2025.'}
        self.assertIsNone(model_text(e, {}))
        self.assertIsNone(model_text(e, {e['id']:{'evidence_sha256':signature(e),'disposition':'hold'}}))
        before = deepcopy(e)
        self.assertTrue(needs_review(e));self.assertEqual(e,before)

    def test_recent_organization_amount_requires_bound_review_and_actual_period(self):
        e={'id':'GE-9999','date':'2026','dimension':'aipac_funding','summary':'PAC gave $500 in 2025.'}
        r={'evidence_sha256':signature(e),'disposition':'organization_since_2024',
           'period':{'start':'2025-01-01','end':'2025-12-31'},'donor_type':'organization',
           'kind':'contribution','model_text':'2025: PAC contributed $500.'}
        self.assertEqual(model_text(e,{e['id']:r}),r['model_text'])
        for change in [{'period':{'start':'2023-01-01','end':'2026-12-31'}},
                       {'period':{'start':'2024-99-01','end':'2026-12-31'}},
                       {'period':{'start':'2026-01-01','end':'2025-12-31'}},
                       {'donor_type':'individual'}, {'donor_type':'mixed'}, {'kind':'unknown'}]:
            self.assertIsNone(model_text(e,{e['id']:{**r,**change}}))
        self.assertIsNone(model_text({**e,'summary':'Changed amount or period.'},{e['id']:r}))

    def test_org_receipts_exclude_individuals_employer_matching_earmarks_and_old_dates(self):
        r={'entity_type':'COM','memoed_subtotal':False,'contribution_receipt_date':'2024-01-01T00:00:00','memo_text':''}
        self.assertTrue(organization_receipt(r))
        for change in [{'entity_type':'IND','contributor_employer':'AIPAC'}, {'entity_type':None},
                       {'memoed_subtotal':True}, {'memoed_subtotal':None}, {'memo_text':'earmarked through PAC'},
                       {'memo_text':'conduit receipt'}, {'contribution_receipt_date':'2023-12-31'},
                       {'contribution_receipt_date':'2026-99-99'}]:
            self.assertFalse(organization_receipt({**r,**change}))

    def test_donor_years_do_not_borrow_next_donors_range_or_analysis_date(self):
        rows=track_jpac_rows('<p>Analyzed 2026</p><table><tr><th>Contributor</th><th>Years</th><th>Total Amount</th><th>Relationship to Israel</th></tr><tr><td>California Jewish PAC</td><td>2021-2023</td><td>$25,700</td><td>PAC</td></tr><tr><td>Individual</td><td>2021-2025</td><td>$7,500</td><td>Person</td></tr></table>')
        self.assertEqual(rows[0]['period'],'2021-2023');self.assertEqual(rows[1]['period'],'2021-2025')
        with self.assertRaises(ValueError):track_jpac_rows('<p>No donor table.</p>')

    def test_haney_public_correction_is_historical_and_absent_from_new_model_input(self):
        p,c=next((p,c) for p in DATA['positions'] for c in p.get('candidates') or [] if c['name']=='Matt Haney')
        original=deepcopy(c);e=next(e for e in c['gaza_evidence'] if e['id']=='GE-0021')
        self.assertEqual(e['date'],'2023');self.assertIn('2021–2023',e['summary']);self.assertNotIn('$47,700',e['summary'])
        state=build_state(p,c,DATA);text=json.dumps(state,ensure_ascii=False)
        self.assertNotIn('$47,700',text);self.assertNotIn('$25,700',text);self.assertNotIn('Robert J. Fisher',text)
        self.assertIn('HEAL Palestine',text);self.assertIn('CAIR Action',text);self.assertIn('Vote for Peace',text)
        self.assertEqual(c,original)

    def test_filtering_precedes_evidence_budget_and_preserves_nonfinancial_statements(self):
        p=deepcopy(DATA['positions'][0]);c=deepcopy(p['candidates'][0])
        c['gaza_evidence']=[{'id':f'GE-{9000+i}','date':'2026','dimension':'aipac_funding','summary':'Old aggregate.'} for i in range(12)]
        c['gaza_evidence'].append({'id':'GE-9998','date':'2026','dimension':'actions_votes','summary':'Called for a ceasefire.'})
        self.assertEqual(build_state(p,c,DATA)['gaza_evidence'],['2026: Called for a ceasefire.'])
        mixed={'id':'GE-9997','date':'2026','dimension':'framing_balance','summary':'Received $500K from a donor in 2016, and criticized the Iran deal.'}
        self.assertTrue(needs_review(mixed));self.assertIsNone(model_text(mixed,{}))

    def test_all_current_observations_have_exact_audit_bindings(self):
        index=policy();seen=set()
        for pid,name,e in observations(DATA):
            row=index[e['id']];seen.add(e['id'])
            self.assertEqual(row['evidence_sha256'],signature(e));self.assertEqual((pid,name),(row['position_id'],row['candidate']))
            self.assertEqual(model_text(e) is not None,row['disposition']!='hold')
        self.assertEqual(seen,set(index))
        decisions=json.loads((ROOT/'research/funding/source-decisions-2026-10-26.json').read_text())['decisions']
        for ref,record in decisions.items():
            self.assertEqual(ref,digest(dump(record['request']).encode()))
            self.assertTrue(all(q['type']=='choice' for q in record['request']['questions'].values()))
        for row in index.values():
            self.assertIn(row['classification_jev_ref'],decisions)
            if row['disposition']!='hold':self.assertIn(row['projection_jev_ref'],decisions)


if __name__=='__main__':unittest.main()
