"""Offline source, identity, selection and immutable-input regressions."""
from copy import deepcopy
import json
import unittest

import grade_gaza as g
import organization_context as org
import serve_jev_playground as playground
from discover_organization_funding import fetch_transfers, packet


class OrganizationChecks(unittest.TestCase):
    def test_fiona_cjd_campaign_alias_does_not_duplicate_official_support(self):
        data = json.loads(g.DATASET.read_text())
        position, candidate = next((p, c) for p in data['positions']
                                   for c in p.get('candidates') or [] if c['name'] == 'Fiona Ma')
        original = deepcopy(candidate)
        state = g.build_state(position, candidate, data)
        observations = [e for e in state['focused_endorsement_observations']
                        if org.name_key(e['endorser']) in {org.name_key(n) for n in org.CJD_ALIASES}]
        self.assertEqual(observations, [{'endorser': 'California Jewish Democrats',
                                        'relation': 'supported', 'phase': 'unspecified', 'rating': 'Support'}])
        self.assertEqual(candidate, original)
        self.assertTrue(any(e['endorser'] == 'Democrats for Israel California'
                            for e in candidate['endorsements']))

    def test_cjd_normalization_preserves_distinct_phases_history_ratings_and_opposition(self):
        own = {'endorser': 'California Jewish Democrats', 'relation': 'supported',
               'rating': 'Support', 'phase': 'general', 'verification': 'endorser_statement'}
        claim = {'endorser': 'Democrats for Israel California', 'relation': 'endorsed',
                 'phase': 'general', 'verification': 'campaign_claim'}
        distinct = [{**claim, 'rating': 'Strong Support'}, {**claim, 'phase': 'primary'},
                    {**claim, 'historical': True}, {**claim, 'relation': 'opposed'}]
        rows = [own, claim, *distinct, {**own, 'endorser': 'DFI California'}]
        original = deepcopy(rows)
        result = org.normalize_endorsement_observations(rows)
        self.assertEqual(len(result), 5)
        self.assertTrue(all(e['endorser'] == 'California Jewish Democrats' for e in result))
        self.assertTrue(any(e.get('rating') == 'Strong Support' for e in result))
        self.assertTrue(any(e['phase'] == 'primary' for e in result))
        self.assertTrue(any(e.get('historical') for e in result))
        self.assertTrue(any(e['relation'] == 'opposed' for e in result))
        self.assertEqual(rows, original)

    def test_cjd_context_preserves_endorsement_tiers_without_blanket_offsets(self):
        for alias in org.CJD_ALIASES:
            for rating in ('Support', 'Strong Support'):
                with self.subTest(alias=alias, rating=rating):
                    candidate = {'name': 'Example', 'endorsements': [
                        {'endorser': alias, 'relation': 'supported', 'rating': rating},
                        {'endorser': 'CAIR Action', 'relation': 'endorsed', 'phase': 'general'},
                    ]}
                    original = deepcopy(candidate)
                    state = g.build_state({'id': 'test', 'office': 'Assembly'}, candidate, {'codes': {'party': {}}})
                    self.assertNotIn('zionist_endorsement_context', state)
                    self.assertEqual(state['organization_context']['California Jewish Democrats']['relevance'],
                                     org.CJD_ENDORSEMENT_CONTEXT)
                    observations = state['focused_endorsement_observations']
                    self.assertTrue(any(e['endorser'] == 'California Jewish Democrats' and e['rating'] == rating for e in observations))
                    self.assertTrue(any(e['endorser'] == 'CAIR Action' and e['relation'] == 'endorsed'
                                        for e in observations))
                    self.assertIn('CAIR Action', state['organization_context'])
                    self.assertEqual(candidate, original)

    def test_cjd_context_requires_a_current_observation(self):
        for observations in ([], [{'endorser': 'California Jewish Democrats', 'historical': True}]):
            state = {'focused_endorsement_observations': observations}
            org.add_observation_context(state)
            self.assertNotIn('California Jewish Democrats', state.get('organization_context', {}))

    def test_discovery_paginates_and_holds_unreviewed_transfers(self):
        rows = [{'committee_id':'C00799031','recipient_committee_id':'C00000001',
                 'recipient_name':'Unreviewed recipient','disbursement_date':'2026-01-01',
                 'disbursement_amount':100,'memoed_subtotal':False,'sub_id':str(i)} for i in range(100)]
        calls=[]
        def get(params):
            calls.append(deepcopy(params))
            if len(calls)==1:
                return {'results':rows,'pagination':{'last_indexes':{'last_index':'99','last_disbursement_date':'2026-01-01'}}}
            return {'results':[rows[0],{**rows[0],'sub_id':'memo','memoed_subtotal':True},
                               {**rows[0],'sub_id':'negative','disbursement_amount':-100},
                               {**rows[0],'sub_id':'old','disbursement_date':'2023-01-01'}], 'pagination':{}}
        result=fetch_transfers('C00799031','2024-01-01','2026-10-27','unused',get)
        self.assertEqual(len(result),100)
        self.assertEqual(calls[1]['last_index'],'99')
        report=packet(result,{'ie_spenders':{'C00000001':{'name':'Unreviewed recipient'}}},
                      'C00799031','2024-01-01','2026-10-27')
        self.assertEqual(report['status'],'held_for_source_and_jev_review')
        self.assertIsNone(report['recipients']['C00000001']['registered_context'])
        self.assertNotIn('unused',json.dumps(report))
        def repeated(params):
            return {'results':rows,'pagination':{'last_indexes':{'last_index':'99'}}}
        with self.assertRaisesRegex(ValueError,'repeated'):
            fetch_transfers('C00799031','2024-01-01','2026-10-27','unused',repeated)

    def test_registry_is_source_bound_and_jev_reviewed(self):
        registry, entities, _ = org.registry()
        review = json.loads(org.REGISTRY.with_suffix('.review.json').read_text())
        self.assertEqual(review['registry_sha256'], g.digest(g.dump(registry).encode()))
        self.assertEqual(review['request_sha256'], g.digest(g.dump(review['request']).encode()))
        g.validate_response(review['request']['questions'], review['response'])
        self.assertEqual(set(review['response']['answers']), set(entities))
        self.assertTrue(all(a['choice'] == 'supported' for a in review['response']['answers'].values()))
        for source in registry['sources'].values():
            self.assertTrue(source['url'].startswith('https://'))
            if source['kind'] == 'fec_filing':
                receipt, expense = source['receipt'], source['disbursement']
                self.assertEqual(receipt['committee_id'], expense['recipient_committee_id'])
                self.assertEqual(receipt['contributor_id'], expense['committee_id'])
                self.assertEqual(receipt['contribution_receipt_amount'], expense['disbursement_amount'])
                self.assertEqual(receipt['contribution_receipt_date'], expense['disbursement_date'])
                self.assertFalse(receipt['memoed_subtotal'])
                self.assertFalse(expense['memoed_subtotal'])

    def test_known_relevant_spender_below_cap_and_unknown_retained(self):
        items = [{'spender_id': str(i), 'direction': 'for', 'amount': 1000-i} for i in range(14)]
        items += [{'spender_id': 'C00799031', 'direction': 'for', 'amount': 1.23},
                  {'spender_id': 'C00799031', 'direction': 'against', 'amount': 4.56}]
        c = {'independent_expenditures': {'items': items}}
        data = {'ie_spenders': {'C00799031': {'name': "UNITED DEMOCRACY PROJECT ('UDP')"}}}
        before = deepcopy((c, data))
        state = {}; org.add_spending(state, c, data)
        self.assertEqual(len(state['spenders_supporting']), 13)
        self.assertEqual(state['spenders_supporting'][-1]['amount_usd'], 1.23)
        self.assertEqual(state['spenders_opposing'][0]['amount_usd'], 4.56)
        self.assertEqual(state['spenders_supporting'][-1]['organization_context'], 'United Democracy Project')
        self.assertEqual(state['spenders_supporting'][0]['relevance'], 'unestablished')
        self.assertEqual(len(state['organization_context']), 1)
        self.assertEqual((c, data), before)

    def test_committee_ids_not_names_and_no_provider_cross_match(self):
        c = {'independent_expenditures': {'items': [{'spender_id': 'unknown', 'direction':'for','amount':1}]},
             'ca_independent_expenditures': {'items': [{'spender_id':'C00799031','direction':'for','amount':2}]}}
        data = {'ie_spenders': {'unknown': {'name':'United Democracy Project'}},
                'ca_ie_spenders': {'C00799031': {'name':'United Democracy Project'}}}
        state = {}; org.add_spending(state,c,data);org.add_spending(state,c,data,california=True)
        self.assertNotIn('organization_context', state)
        self.assertEqual(state['spenders_supporting'][0]['relevance'], 'unestablished')
        self.assertEqual(state['ca_spenders_supporting'][0]['relevance'], 'unestablished')

    def test_funding_link_is_sufficient_owner_signal_not_earmarking(self):
        state = {}
        for id_ in ('bold-america','edw-action'):
            entity = org.registry()[1][id_]
            org.add_context(state,id_,entity['name'])
            context = state['organization_context'][entity['name']]
            self.assertEqual(context['relationship']['type'], 'received_funding_from')
            self.assertTrue(context['relationship']['documented_date'].startswith('2026'))
            self.assertIn('no candidate-specific earmarking proof is required',context['guide_assessment'])
            self.assertIn('not proof UDP funded a particular ad',context['relevance'])
        self.assertEqual(state['organization_context']['EDW Action Fund']['role'],'hybrid PAC')
        org.add_context(state,'314-action','314 ACTION FUND')
        self.assertEqual(state['organization_context']['314 Action Fund']['relationship']['documented_date'],'2024-05-01')
        org.add_context(state,'palmetto-action','PALMETTO ACTION')
        self.assertEqual(state['organization_context']['Palmetto Action']['relationship']['type'],'funding_reported_by_donor')
        self.assertIn('recipient-side confirmation was not returned',state['organization_context']['Palmetto Action']['relevance'])

    def test_alias_boundaries_ratings_and_absent_entities(self):
        observations = [{'endorser':'VoteForPeace','rating':'Neutral','relation':'neutral','phase':'primary'},
                        {'endorser':'CAIR Action','relation':'preferred','shared':True},
                        {'endorser':'J Street PAC','relation':'endorsed'}]
        state = {'focused_endorsement_observations':deepcopy(observations),
                 'gaza_evidence':['Track AIPAC endorsed this candidate. Unrelated BOLD typography.']}
        org.add_observation_context(state)
        self.assertEqual(state['focused_endorsement_observations'],observations)
        self.assertEqual(set(state['organization_context']),
                         {'Vote for Peace','CAIR Action','JStreetPAC','Track AIPAC / Citizens Against AIPAC Corruption'})
        self.assertIn('not equivalent to AIPAC',state['organization_context']['JStreetPAC']['relevance'])
        self.assertIn('inclusion alone is not endorsement',state['organization_context']['Vote for Peace']['relevance'])
        empty = {}; org.add_observation_context(empty)
        self.assertEqual(empty,{})

    def test_real_candidates_and_shared_builders(self):
        data=json.loads(g.DATASET.read_text())
        p,c,_ = next((p,c,r) for p,c,r in g.candidates(data,'all') if c['name']=='Denise Powell')
        before=deepcopy(c)
        state=g.build_state(p,c,data)
        self.assertEqual(c,before)
        for name in ('BOLD America','EDW Action Fund'):
            self.assertIn(name,state['organization_context'])
            self.assertTrue(any(r.get('organization_context')==name for r in state['spenders_supporting']))
        # CHC BOLD PAC is not BOLD America, despite the similar name.
        chc=next(r for r in state['spenders_supporting'] if r['spender']=='CHC BOLD PAC')
        self.assertEqual(chc['relevance'],'unestablished')
        local=playground.playground_state(p,c,data)
        for field in ('organization_context','spenders_supporting','spenders_opposing'):
            self.assertEqual(local[field],state[field])

    def test_registered_endorser_aliases_enter_focus_without_changing_tiers(self):
        p={'id':'test','office':'Congress'}
        c={'name':'Example','endorsements':[{'endorser':'J Street PAC','relation':'endorsed','phase':'primary'},
                                           {'endorser':'Vote4Peace','relation':'neutral','rating':'Neutral'},
                                           {'endorser':'AIPAC PAC','relation':'endorsed'}]}
        rows=g.focused_endorsements(p,c)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[1]['rating'],'Neutral')


if __name__ == '__main__':
    unittest.main()
