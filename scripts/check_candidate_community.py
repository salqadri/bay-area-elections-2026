"""Offline regressions for explicit community observations and source research."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ballotpedia_endorsements import ROOT, DATASET, save
import candidate_community as c
import grade_gaza as g
import research_candidate_community as r


class CommunityChecks(unittest.TestCase):
    def test_owner_confirmations_bind_to_current_office_and_preserve_ballot_names(self):
        data=json.loads(DATASET.read_text());records=c.load_observations()
        expected={('CA2026-003','Aisha Wahab'),('CA2026-002','Lateefah Simon'),('CA2026-057','Kiran Mohammad'),
                  ('CA2026-056','Kashef Qaadri'),('CA2026-061','Aziz Akbari'),('CA2026-084','Qasim Lodhi'),
                  ('CA2026-174','Kamal Yassin'),('CA2026-123','Seema Badar'),('CA2026-173','Raeena S. Lari'),
                  ('CA2026-142','Jamal Khan'),('US2026-016','Abdul El-Sayed')}
        self.assertEqual(len(expected),11)
        for key in expected:
            self.assertEqual(records[key]['basis'],'owner_confirmation')
            self.assertIs(records[key]['part_of_muslim_community'],True)
        self.assertIn(('CA2026-142','Jamal Khan'),records);self.assertIn(('CA2026-173','Raeena S. Lari'),records)
        self.assertIn(('US2026-016','Abdul El-Sayed'),records)
        self.assertIs(records[('CA2026-301','Boris Lipkin')]['part_of_muslim_community'],False)
        self.assertIs(records[('US2026-093','Shafina Barnett')]['part_of_muslim_community'],True)
        self.assertEqual(sum(record['part_of_muslim_community'] is False for record in records.values()),12)
        self.assertTrue(all('exception' not in record for record in records.values()))
        self.assertEqual(c.check_observations(data),[])
        for p in data['positions']:
            for candidate in p.get('candidates') or []:
                value=g.build_state(p,candidate,data).get('part_of_muslim_community')
                if (p['id'],candidate['name']) in records:self.assertEqual(value,records[(p['id'],candidate['name'])]['part_of_muslim_community'])
                else:self.assertIsNone(value)

    def test_missing_is_unknown_explicit_false_is_not_lost_and_names_do_not_transfer(self):
        p={'id':'race','office':'Council','jurisdiction':'Example City','district_or_seat':'District 1'};candidate={'name':'Known Candidate'}
        record={**p,'position_id':'race','candidate':candidate['name'],'part_of_muslim_community':True}
        records={('race',candidate['name']):record};before=deepcopy(candidate)
        self.assertEqual(c.community_state(p,candidate,records),{'part_of_muslim_community':True});self.assertEqual(candidate,before)
        self.assertEqual(c.community_state(p,{'name':'Other Candidate','endorsements':[{'endorser':'CAIR Action','relation':'endorsed'}]},records),{})
        self.assertEqual(c.community_state({**p,'id':'different'},candidate,records),{})
        record['part_of_muslim_community']=False;self.assertEqual(c.community_state(p,candidate,records),{'part_of_muslim_community':False})
        with self.assertRaises(ValueError):c.community_state({**p,'district_or_seat':'District 2'},candidate,records)

    def test_registry_rejects_duplicates_nonbooleans_and_missing_provenance(self):
        row={'position_id':'race','candidate':'Person','part_of_muslim_community':True,'basis':'owner_confirmation'}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'observations.json'
            for rows in ([row,row],[{**row,'part_of_muslim_community':1}],[{**row,'basis':'name_guess'}],[{**row,'basis':'public_source_jev_review'}]):
                save(path,{'format':'candidate-community-observations/v1','observations':rows})
                with self.assertRaises(ValueError):c.load_observations(path)

    def test_search_inventory_treats_every_unknown_equally_and_skips_owner_search(self):
        data={'positions':[{'id':'one','office':'Mayor','jurisdiction':'Example','candidates':[{'name':'Known'},{'name':'Other'}]},
                           {'id':'two','office':'Council','jurisdiction':'Example','ballot_status':'excluded','candidates':[{'name':'Excluded'}]}]}
        with patch.object(r,'load_observations',return_value={('one','Known'):{'part_of_muslim_community':True}}):rows=r.inventory(data)
        self.assertEqual([x['status'] for x in rows],['already_confirmed','unresearched'])
        self.assertEqual(rows[0]['query'].replace('Known','Other'),rows[1]['query']);self.assertEqual(len(rows),2)

    def test_discovery_is_resumable_no_key_persisted_and_dataset_changes_refused(self):
        data={'positions':[{'id':'one','office':'Mayor','jurisdiction':'Example','candidates':[{'name':'Person'}]}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(r,'search_request',return_value={'organic':[]}) as search:
            work=Path(directory);r.discover(data,work,'SECRET_FIXTURE');r.discover(data,work,'SECRET_FIXTURE')
            self.assertEqual(search.call_count,1)
            self.assertFalse(any('SECRET_FIXTURE' in path.read_text() for path in work.rglob('*.json')))
            changed=deepcopy(data);changed['positions'][0]['candidates'][0]['name']='Changed'
            with self.assertRaises(ValueError):r.discover(changed,work,'SECRET_FIXTURE')

    def test_search_snippets_are_never_capture_evidence_or_boolean_findings(self):
        data={'positions':[{'id':'one','office':'Mayor','jurisdiction':'Example','candidates':[{'name':'Person'}]}]}
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory);r.discover(data,work,'',limit=0);row=r.inventory(data)[0]
            save(work/'searches'/(r.digest(row['query'].encode())+'.json'),{'query':row['query'],'response':{'organic':[{'title':'Muslim candidate Person','link':'https://example.org/person','snippet':'Person is Muslim.'}]}})
            with patch.object(r,'capture_url') as capture, patch.object(r,'ask') as ask:
                self.assertEqual(r.review(data,work,''),{});capture.assert_not_called();ask.assert_not_called()
            self.assertEqual(len(r.source_context({'text':'Header Muslim community. '+'word '*1000}).split()),200)

    def test_source_review_is_required_and_new_leads_invalidate_old_projection(self):
        data={'positions':[{'id':'one','office':'Mayor','jurisdiction':'Example','candidates':[{'name':'Person'}]}]}
        lead={'title':'Person public biography','link':'https://example.org/person','snippet':'Person explicitly says they are Muslim.'}
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory);r.discover(data,work,'',limit=0);row=r.inventory(data)[0]
            save(work/'searches'/(r.digest(row['query'].encode())+'.json'),{'query':row['query'],'response':{'organic':[lead]}})
            def decide(work,state,questions,key):
                if 'explicit_public_affiliation' in questions:
                    return {'explicit_public_affiliation':{'choice':'explicit'},'supporting_source':{'choice':'0'}},'source-fixture'
                return {key:{'choice':'0'} for key in questions},'triage-fixture'
            packet={'url':lead['link'],'requested_url':lead['link'],'checked_on':'2026-10-25','content_sha256':'fixture',
                    'title':lead['title'],'text':'Person is the mayor of Example. Person explicitly identifies as Muslim.','status':'captured'}
            with patch.object(r,'ask',side_effect=decide) as ask, patch.object(r,'capture_url',return_value=packet):
                r.triage(data,work,'');r.review(data,work,'');r.review(data,work,'')
                self.assertEqual(ask.call_count,2)
            reviewed=json.loads((work/'reviews'/(row['id']+'.json')).read_text())
            self.assertEqual(reviewed['status'],'needs_owner_community_confirmation');self.assertNotIn('part_of_muslim_community',reviewed)
            self.assertEqual(r.report(data,work)['rows'][0]['status'],'needs_owner_community_confirmation')
            triage_path=work/'triage'/(row['id']+'.json');triaged=json.loads(triage_path.read_text())
            triaged['leads'][0]['snippet']='Changed source context';save(triage_path,triaged)
            self.assertEqual(r.report(data,work)['rows'][0]['status'],'needs_source_review')
            triaged['answer']['choice']='none';triaged['status']='no_explicit_lead';save(triage_path,triaged)
            self.assertEqual(r.report(data,work)['rows'][0]['status'],'no_explicit_lead')

    def test_unreadable_source_is_held_for_owner_without_model_guess(self):
        data={'positions':[{'id':'one','office':'Mayor','jurisdiction':'Example','candidates':[{'name':'Person'}]}]}
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory);r.discover(data,work,'',limit=0);row=r.inventory(data)[0]
            hit={'title':'Muslim candidate','snippet':'Person biography','link':'https://example.org/person'}
            save(work/'searches'/(r.digest(row['query'].encode())+'.json'),{'query':row['query'],'response':{'organic':[hit]}})
            save(work/'triage'/(row['id']+'.json'),{'answer':{'choice':'0'},'leads':[hit]})
            with patch.object(r,'capture_url',return_value={'status':'source_unavailable'}),patch.object(r,'ask') as ask:
                r.review(data,work,'');ask.assert_not_called()
            reviewed=json.loads((work/'reviews'/(row['id']+'.json')).read_text())
            self.assertEqual(reviewed['status'],'needs_owner_review');self.assertEqual(reviewed['sources'],[])

    def test_discovery_cannot_overwrite_an_explicit_owner_value(self):
        data={'positions':[{'id':'one','office':'Mayor','jurisdiction':'Example','candidates':[{'name':'Person'}]}]}
        record={'position_id':'one','candidate':'Person','part_of_muslim_community':False,'basis':'owner_confirmation'}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'observations.json';save(path,{'format':'candidate-community-observations/v1','observations':[record]})
            before=path.read_bytes();records=c.load_observations(path);work=Path(directory)/'work'
            with patch.object(r,'load_observations',return_value=records),patch.object(r,'ask') as ask,patch.object(r,'search_request') as search:
                r.discover(data,work,'');row=r.inventory(data)[0]
                save(work/'searches'/(r.digest(row['query'].encode())+'.json'),{'query':row['query'],'response':{'organic':[{'title':'Muslim candidate Person','snippet':'Person is Muslim.','link':'https://example.org/person'}]}})
                r.triage(data,work,'');r.review(data,work,'');search.assert_not_called();ask.assert_not_called()
                self.assertIs(r.report(data,work)['rows'][0]['part_of_muslim_community'],False)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(c.community_state(data['positions'][0],data['positions'][0]['candidates'][0],records),{'part_of_muslim_community':False})


if __name__=='__main__':unittest.main()
