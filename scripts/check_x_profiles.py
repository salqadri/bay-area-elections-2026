"""Offline regressions for campaign self-link recovery and exact additive reviews."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import research_x_profiles as x


def dataset():
    # Use a valid real dataset but remove links only inside each isolated fixture.
    d = json.loads(x.DATASET.read_text())
    for p in d['positions']:
        for c in p.get('candidates') or []:
            if c['name'] == 'Xavier Becerra':
                c.pop('x_url', None); c.pop('secondary_x_url', None)
    return d


def packet(row, handles=('SampleCandidate',)):
    html = '<html><head><title>Xavier Becerra for California Governor</title></head><body>' + ('Xavier Becerra for California Governor. ' * 8)
    html += '<footer>' + ''.join('<a aria-label="Follow on X" href="https://x.com/'+h+'">X</a>' for h in handles) + '</footer></body></html>'
    return {'url': row['campaign_url'], 'observed_at': '2026-10-22T17:00:00+00:00', 'status': 'captured',
            'final_url': row['campaign_url'], 'content_sha256': x.digest(html.encode()),
            **x.CampaignHTML(html, row['campaign_url']).packet()}


def fake_decide(request):
    answers = {}
    for qid, q in request['questions'].items():
        selected = 'match' if qid == 'identity' else 'self'
        answers[qid] = {'type': 'choice', 'choice': selected,
                       'probabilities': {k: float(k == selected) for k in q['criteria']}}
    return {'model': x.MODEL, 'answers': answers}


class URLChecks(unittest.TestCase):
    def test_legacy_and_tracking_profile_urls_normalize(self):
        self.assertEqual(x.profile('http://www.twitter.com/XavierBecerra/?lang=en#bio'), 'https://x.com/XavierBecerra')
        self.assertEqual(x.profile('https://mobile.twitter.com/A'), 'https://x.com/A')

    def test_posts_shares_reserved_paths_and_spoof_hosts_are_not_profiles(self):
        for url in ('https://x.com/intent/tweet?url=x', 'https://x.com/search', 'https://x.com/i',
                    'https://x.com/Example/status/123', 'https://x.com.evil.test/Example',
                    'https://evil.test/?u=https://x.com/Example', 'https://x.com@evil.test/Example',
                    'https://user@x.com/Example', 'https://x.com/way_too_long_handle_123', 'javascript:alert(1)'):
            self.assertIsNone(x.profile(url), url)

    def test_only_real_anchors_are_collected_not_scripts_or_plain_text(self):
        h = '<html><title>Test</title><script>"https://x.com/Fake"; <a href="https://x.com/Fake2">A</a></script><p>https://x.com/Plain</p><footer><a href="https://twitter.com/Real?lang=en">Follow</a></footer></html>'
        p = x.CampaignHTML(h, 'https://example.test').packet()
        self.assertEqual([a['url'] for a in p['anchors']], ['https://x.com/Real'])
        self.assertIn('footer', p['anchors'][0]['ancestors'])
        self.assertNotIn('Fake', p['text'])


class ReviewChecks(unittest.TestCase):
    def setUp(self):
        self.data = dataset()
        self.row = next(r for r in x.inventory(self.data) if r['candidate'] == 'Xavier Becerra')
        self.packet = packet(self.row)

    def artifact(self):
        cached = {}
        def decide(req):
            response = fake_decide(req); cached[x.digest(x.dump(req).encode())] = {'request': req, 'response': response}; return response
        outcomes = x.evaluate(self.data, {self.packet['url']: self.packet}, decide)
        return {'format': x.POLICY, 'id': 'fixture-x-profiles', 'reviewed_on': '2026-10-22',
                'election_date': self.data['election']['date'], 'publication_version': '2026-10-22.4',
                'base_dataset_sha256': x.digest(x.dump(self.data).encode()), 'packets': {self.packet['url']: self.packet},
                'decisions': cached, 'outcomes': outcomes}

    def test_source_binding_change_rejected(self):
        p = deepcopy(self.packet); p['url'] = 'https://other.test'
        with self.assertRaisesRegex(ValueError, 'binding'):
            x.classify(self.row, p, fake_decide)

    def test_identity_and_ownership_thresholds_hold_ambiguous_observations(self):
        for qid in ('identity', 'account0'):
            def decide(req):
                r = fake_decide(req); a = r['answers'][qid]; a['probabilities'][a['choice']] = .8; return r
            self.assertIn('hold', x.classify(self.row, self.packet, decide)['status'])

    def test_missing_and_wrong_model_decisions_rejected(self):
        for bad in ({'model': x.MODEL, 'answers': {}}, {'model': 'other', 'answers': {}}):
            with self.assertRaises(ValueError):
                x.classify(self.row, self.packet, lambda req: bad)

    def test_endorser_link_does_not_publish_when_model_classifies_other(self):
        def decide(req):
            r = fake_decide(req); r['answers']['account0'] = {'type': 'choice', 'choice': 'other', 'probabilities': {'self': 0., 'other': 1., 'unclear': 0.}}; return r
        self.assertEqual(x.classify(self.row, self.packet, decide)['status'], 'ownership_hold')

    def test_multiple_self_accounts_held(self):
        self.assertEqual(x.classify(self.row, packet(self.row, ('FirstAccount', 'SecondAccount')), fake_decide)['status'], 'multiple_accounts_hold')

    def test_repeated_same_handle_case_variants_count_once(self):
        r = x.classify(self.row, packet(self.row, ('ExampleAccount', 'exampleaccount')), fake_decide)
        self.assertEqual(r['status'], 'proposed')

    def test_existing_secondary_not_duplicated_as_primary(self):
        row = {**self.row, 'secondary_x_url': 'https://x.com/samplecandidate'}
        self.assertEqual(x.classify(row, self.packet, fake_decide)['status'], 'ownership_hold')

    def test_unavailable_and_no_link_have_distinct_nonabsence_statuses(self):
        self.assertEqual(x.classify(self.row, {**self.packet, 'status': 'unavailable'}, fake_decide)['status'], 'unavailable')
        self.assertEqual(x.classify(self.row, {**self.packet, 'anchors': []}, fake_decide)['status'], 'no_profile_link_in_capture')

    def test_unknown_campaign_and_uncollected_sites_remain_explicit(self):
        out = x.evaluate(self.data, {}, fake_decide)
        self.assertTrue(any(r['status'] == 'no_recorded_campaign_site' for r in out))
        self.assertTrue(any(r['status'] == 'not_collected' for r in out))

    def test_all_eligible_offices_included_local_provisional_excluded(self):
        rows = x.inventory(self.data)
        self.assertIn('Governor', {r['identity']['office'] for r in rows})
        self.assertTrue(any(r['identity']['office'] == 'City Council Member' for r in rows))
        self.assertTrue(all(x.eligible(p, 'filed_candidates_not_confirmed_on_ballot') is False for p in self.data['positions'] if p.get('counties')))

    def test_collision_with_another_candidate_held(self):
        other = next(c for p in self.data['positions'] for c in p.get('candidates') or [] if c.get('x_url'))
        other['x_url'] = 'https://x.com/SampleCandidate'
        out = x.evaluate(self.data, {self.packet['url']: self.packet}, fake_decide)
        self.assertEqual(next(r for r in out if r['candidate'] == 'Xavier Becerra')['status'], 'collision_hold')

    def test_apply_additive_preserves_every_other_field_and_is_idempotent(self):
        a = self.artifact(); result = x.apply_review(self.data, a)
        c = next(c for p in result['positions'] for c in p.get('candidates') or [] if c['name'] == 'Xavier Becerra')
        self.assertEqual(c['x_url'], 'https://x.com/SampleCandidate')
        new_source = c['source_ids'].pop(); c.pop('x_url'); result['sources'].pop(new_source)
        result['coverage'] = self.data['coverage']; result['election'] = self.data['election']
        self.assertEqual(result, self.data)
        result = x.apply_review(self.data, a); a['after_dataset_sha256'] = x.digest(x.dump(result).encode())
        self.assertEqual(x.apply_review(result, a), result)

    def test_stale_dataset_and_changed_decisions_fail_closed(self):
        a = self.artifact(); changed = deepcopy(self.data); changed['election']['publication_version'] = '2026-10-22.99'
        with self.assertRaisesRegex(ValueError, 'Stale'):
            x.apply_review(changed, a)
        next(r for r in a['outcomes'] if r['status'] == 'proposed')['x_url'] = 'https://x.com/Invented'
        with self.assertRaisesRegex(ValueError, 'Changed proposed'):
            x.apply_review(self.data, a)

    def test_changed_packet_or_model_probability_cannot_authorize_publication(self):
        for which in ('packet', 'response'):
            a = self.artifact()
            if which == 'packet':
                a['packets'][self.packet['url']]['text'] += ' altered'
            else:
                r = next(iter(a['decisions'].values()))['response']; r['answers']['account0']['probabilities']['self'] = .1
            with self.assertRaises((KeyError, ValueError)):
                x.apply_review(self.data, a)

    def test_future_capture_fails(self):
        a = self.artifact(); a['packets'][self.packet['url']]['observed_at'] = '2099-01-01T00:00:00+00:00'
        with self.assertRaisesRegex(ValueError, 'future source'):
            x.apply_review(self.data, a)

    def test_profile_metadata_wrong_handle_and_empty_success_are_unavailable(self):
        from io import BytesIO
        for raw in (b'', b'[]', b'{"code":200,"user":{"screen_name":"OtherPerson"}}'):
            with tempfile.TemporaryDirectory() as temp:
                with patch.object(x.urllib.request, 'urlopen', return_value=BytesIO(raw)):
                    result = x.capture_profile('https://x.com/SampleCandidate', Path(temp))
                self.assertEqual(result['status'], 'unavailable')

    def test_offline_profile_service_does_not_prevent_campaign_self_link_review(self):
        p = deepcopy(self.packet); p['profiles'] = {'https://x.com/SampleCandidate': {'status': 'unavailable'}}
        self.assertEqual(x.classify(self.row, p, fake_decide)['status'], 'proposed')


    def test_http_failure_does_not_erase_raw_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp); raw = work / 'captures' / 'retained.html'; raw.parent.mkdir(); raw.write_text('original')
            with patch.object(x.urllib.request, 'urlopen', side_effect=OSError('offline')):
                result = x.capture('https://example.test', work)
            self.assertEqual(result['status'], 'unavailable'); self.assertEqual(raw.read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
