"""Offline source-scope, evidence binding and cross-source duplicate regressions."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ballotpedia_endorsements as bp
from endorsement_identity import duplicate_record, possible_duplicates

URL = 'https://ballotpedia.org/Example_Candidate'


def page(content, intro='Example Candidate is running for Mayor in 2026.'):
    return ('<html><head><link rel="canonical" href="' + URL + '"></head><body><h1>Example Candidate</h1>'
            '<div class="mw-parser-output"><p>' + intro + '</p>' + content + '</div></body></html>')


def listing(name='Example Union', label=''):
    return '<ul class="H350"><li>' + label + '<a href="/Example_Union">' + name + '</a><sup><a href="https://example.org/source">[1]</a></sup></li></ul>'


def data():
    return {'election': {'date': '2026-11-03', 'counties_in_scope': [{'name': 'Alameda'}]},
            'notes': {'N100': 'Existing fixture note'},
            'positions': [{'id': 'CA2026-999', 'office': 'Mayor', 'jurisdiction': 'Example City',
                           'district_or_seat': 'At-large', 'term': '4 years', 'election_type': 'general',
                           'candidates': [{'name': 'Example Candidate', 'ballotpedia_url': URL}]}]}


def answer(value, others=()):
    return {'type': 'choice', 'choice': value, 'probabilities': {value: 1.0, **{o: 0.0 for o in others}}}


def fixture_response(request):
    answers = {}
    for qid, q in request['questions'].items():
        value = ('match' if qid == 'identity' else 'unspecified' if qid == 'phase' else
                 'distinct' if qid == 'new_entity' else 'endorsed' if qid.startswith('relation') else 'organization' if qid.startswith('kind') else 'unclear')
        answers[qid] = answer(value, set(q['criteria']) - {value})
    return {'model': bp.MODEL, 'answers': answers}


class ParserChecks(unittest.TestCase):
    def entries(self, html):
        parsed = bp.parse_profile(html, URL, 2026)
        return [e for s in parsed['sections'] for e in s['entries']]

    def test_multiple_years_and_unscoped_historical_sections(self):
        html = page('<h2>Elections</h2><h3>2026</h3><h4 id="Endorsements">Endorsements</h4>' + listing('Current Group') +
                    '<h3>2024</h3><h4>Endorsements</h4>' + listing('Older Group') +
                    '<h2>Notable endorsements</h2>' + listing('Career Group'))
        self.assertEqual([e['endorser'] for e in self.entries(html)], ['Current Group'])

    def test_polling_chart_heading_does_not_erase_explicit_year(self):
        html = page('<h2>Elections</h2><h3>2026</h3><h3>Change over time</h3><h4>Endorsements</h4>' + listing())
        self.assertEqual(len(self.entries(html)), 1)

    def test_year_subsections_inside_endorsements(self):
        html = page('<h2>Endorsements</h2><h3>2024</h3>' + listing('Old Group') + '<h3>2026</h3>' + listing('New Group'))
        self.assertEqual([e['endorser'] for e in self.entries(html)], ['New Group'])

    def test_no_year_is_a_hold_not_current_by_default(self):
        parsed = bp.parse_profile(page('<h2>Endorsements</h2>' + listing()), URL, 2026)
        self.assertEqual(parsed['status'], 'no_current_cycle_section')
        self.assertTrue(parsed['excluded_sections'])

    def test_nested_category_list_and_citation_links(self):
        html = page('<h2>Elections</h2><h3>2026</h3><h4>Endorsements</h4><ul><li>Organizations' + listing() + '</li></ul>')
        entries = self.entries(html)
        self.assertEqual([e['endorser'] for e in entries], ['Example Union'])
        self.assertEqual(entries[0]['links'][-1]['url'], 'https://example.org/source')
        self.assertNotIn('[1]', entries[0]['text'])

    def test_table_or_ambiguous_links_are_retained_as_source_holds(self):
        html = page('<h2>Elections</h2><h3>2026</h3><h4>Endorsements</h4><table><tr><td>Example Union</td></tr></table>')
        result = bp.parse_profile(html, URL, 2026)
        self.assertTrue(result['sections'][0]['holds'])
        self.assertEqual(result['sections'][0]['entries'], [])
        html = page('<h2>Elections</h2><h3>2026</h3><h4>Endorsements</h4><ul><li><a href="/A">Group A</a> and <a href="/B">Group B</a></li></ul>')
        self.assertTrue(bp.parse_profile(html, URL, 2026)['sections'][0]['holds'])

    def test_challenge_and_empty_pages_never_establish_absence(self):
        for raw in ['', '<html><script>awsWaf</script></html>', '<h1>Access denied</h1><div class="mw-parser-output"></div>']:
            self.assertEqual(bp.parse_profile(raw, URL, 2026)['status'], 'unavailable')

    def test_row_subheadings_and_category_context_are_preserved(self):
        html = page('<h2>Elections</h2><h3>2026</h3><h4>Endorsements</h4><h5>Primary election</h5>' + listing('Primary Group') +
                    '<h5>General election</h5>' + listing('General Group'))
        rows = self.entries(html)
        self.assertIn('Primary election', rows[0]['heading_path'])
        self.assertIn('General election', rows[1]['heading_path'])
        self.assertNotEqual(bp.phase_questions({'heading_path': rows[0]['heading_path'], 'text': ''}),
                            bp.phase_questions({'heading_path': rows[1]['heading_path'], 'text': ''}))
        html = page('<h2>Elections</h2><h3>2026</h3><h4>Endorsements</h4><ul><li>Opposition' + listing() + '</li></ul>')
        self.assertIn('Opposition', self.entries(html)[0]['category_context'])

    def test_titles_and_party_are_not_invented_as_part_of_name(self):
        html = page('<h2>Elections</h2><h3>2026</h3><h4>Endorsements</h4>' + listing('Jane Doe', 'U.S. Sen. '))
        e = self.entries(html)[0]
        self.assertEqual(e['endorser'], 'Jane Doe')
        self.assertIn('U.S. Sen.', e['text'])

    def test_source_bound_mike_rogers_regression(self):
        fixture = json.loads((bp.ROOT / 'research/endorsements/ballotpedia-fixtures/mike-rogers.json').read_text())
        parsed = bp.parse_profile(fixture['html'], fixture['url'], 2026)
        names = [e['endorser'] for s in parsed['sections'] for e in s['entries']]
        self.assertEqual(names, fixture['expected_names'])
        self.assertEqual(len(names), 12)
        self.assertNotIn('The Detroit News Editorial Board', names)
        self.assertTrue(any('2024' in s['heading_path'] for s in parsed['excluded_sections']))


class IdentityChecks(unittest.TestCase):
    def record(self, **kwargs):
        return {'endorser': 'Donald Trump', 'relation': 'endorsed', 'phase': 'unspecified',
                'url': 'https://campaign.example.org/', **kwargs}

    def test_provisional_local_rosters_stay_outside_publication_scope(self):
        d = data(); p = d['positions'][0]
        p['counties'] = ['Alameda']; p['filed_candidates_not_confirmed_on_ballot'] = p.pop('candidates')
        self.assertFalse(bp.inventory(d)[0]['publication_eligible'])
        p.update(counties=[], government_level='Federal')
        self.assertTrue(bp.inventory(d)[0]['publication_eligible'])

    def test_same_endorser_two_sources_is_one_observation(self):
        old = self.record()
        self.assertIs(duplicate_record(self.record(url=URL), [old]), old)

    def test_explicit_primary_general_and_historical_stay_distinct(self):
        self.assertIsNone(duplicate_record(self.record(phase='primary'), [self.record(phase='general')]))
        self.assertIsNone(duplicate_record(self.record(historical=True), [self.record()]))
        self.assertIsNone(duplicate_record(self.record(relation='opposed'), [self.record()]))
        self.assertIsNone(duplicate_record(self.record(rating='Preferred'), [self.record()]))

    def test_fuzzy_alias_is_only_a_review_lead(self):
        old = self.record(endorser='Example Group')
        incoming = self.record(endorser='Example Group PAC')
        self.assertIsNone(duplicate_record(incoming, [old]))
        self.assertTrue(possible_duplicates(incoming, [old]))

    def test_campaign_attach_uses_the_same_source_independent_guard(self):
        import campaign_endorsements as campaign
        d = data(); d['coverage'] = {}; c = d['positions'][0]['candidates'][0]
        c['endorsements'] = [self.record(url=URL)]
        incoming = self.record()
        from endorsement_extract import uid, norm
        cid = uid('C-', d['positions'][0]['id'], norm(c['name']))
        with tempfile.TemporaryDirectory() as temp:
            src, out = Path(temp) / 'data.json', Path(temp) / 'out.json'
            src.write_text(json.dumps(d))
            with patch.object(campaign, 'export_accepted', return_value={cid: [('fixture', incoming)]}):
                result = campaign.attach(None, src, out)
            self.assertEqual(result['duplicates_skipped'], 1)
            self.assertEqual(json.loads(out.read_text())['positions'][0]['candidates'][0]['endorsements'], c['endorsements'])


class BindingChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.work = Path(self.temp.name)
        self.data = data()
        self.raw = self.work / 'saved.html'
        self.raw.write_text(page('<h2>Elections</h2><h3>2026</h3><h4 id="Endorsements">Endorsements</h4>' + listing()))
        bp.import_capture(self.data, self.work, URL, self.raw, '2026-10-01T20:00:00+00:00')
        bp.extract(self.data, self.work)
        self.row = json.loads((self.work / 'manifest.json').read_text())['candidates'][0]

    def tearDown(self):
        self.temp.cleanup()

    def review(self):
        def mocked_ask(work, state, questions, key):
            req = {'model': bp.MODEL, 'state': state, 'questions': questions}
            sha = bp.digest(bp.dump(req).encode()); response = fixture_response(req)
            bp.save(work / 'decisions' / (sha + '.json'), {'request': req, 'response': response})
            return response['answers'], sha
        with patch.object(bp, 'ask', side_effect=mocked_ask):
            bp.review_packets(self.data, self.work, 'fixture-key')

    def build(self):
        def mocked_ask(work, state, questions, key):
            req = {'model': bp.MODEL, 'state': state, 'questions': questions}
            sha = bp.digest(bp.dump(req).encode()); response = fixture_response(req)
            bp.save(work / 'decisions' / (sha + '.json'), {'request': req, 'response': response})
            return response['answers'], sha
        with patch.object(bp, 'ask', side_effect=mocked_ask):
            return bp.build_review(self.data, self.work, 'fixture-review', '2026-10-22', 'unused')

    def test_raw_or_packet_tampering_cannot_create_an_entry(self):
        packet = json.loads((self.work / self.row['packet']).read_text())
        packet['sections'][0]['entries'][0]['endorser'] = 'Fabricated Group'
        packet.pop('packet_sha256'); packet['packet_sha256'] = bp.digest(bp.dump(packet).encode())
        bp.save(self.work / self.row['packet'], packet)
        row = {**self.row, 'packet_sha256': packet['packet_sha256']}
        with self.assertRaisesRegex(ValueError, 'actual captured'):
            bp.load_packet(row, self.work, self.data)

    def test_wrong_candidacy_binding_and_new_capture_fail_closed(self):
        changed = deepcopy(self.data); changed['positions'][0]['office'] = 'Different office'
        with self.assertRaisesRegex(ValueError, 'binding'):
            bp.load_packet(self.row, self.work, changed)
        source = json.loads(bp.page_path(self.work, URL).read_text()); source['observed_at'] = '2026-10-02T20:00:00+00:00'; bp.save(bp.page_path(self.work, URL), source)
        with self.assertRaisesRegex(ValueError, 'refreshed'):
            bp.load_packet(self.row, self.work, self.data)

    def test_import_rejects_wrong_url_challenge_and_future_date(self):
        for url, stamp in [('https://evil.example.org/profile', '2026-10-01T20:00:00+00:00'), (URL, '2099-01-01T20:00:00+00:00'), (URL, '2026-10-01')]:
            with self.assertRaises(ValueError):
                bp.import_capture(self.data, self.work, url, self.raw, stamp)
        self.raw.write_text(page('body').replace('rel="canonical" href="'+URL, 'rel="canonical" href="https://ballotpedia.org/Other'))
        with self.assertRaisesRegex(ValueError, 'canonical'):
            bp.import_capture(self.data, self.work, URL, self.raw, '2026-10-01T20:00:00+00:00')

    def test_complete_review_is_additive_and_second_draft_deduplicates(self):
        self.review()
        review, audit = self.build()
        self.assertEqual(audit['counts']['added'], 1)
        change = next(d for d in review['decisions'] if d['action'] == 'change')
        self.assertEqual(change['after']['verification'], 'reported')
        self.assertEqual(change['after']['phase'], 'unspecified')
        self.data['positions'][0]['candidates'][0]['endorsements'] = [change['after']]
        _, audit2 = self.build()
        self.assertEqual(audit2['counts']['corroboration'], 1)
        self.assertNotIn('added', audit2['counts'])

    def test_curated_relationship_and_existing_relation_are_not_overridden(self):
        self.review()
        self.data['positions'][0]['candidates'][0]['endorsements'] = [{
            'endorser': 'Example Union', 'relation': 'supported', 'phase': 'unspecified', 'url': 'https://example.org/guide'}]
        review, audit = self.build()
        self.assertEqual(audit['counts']['relationship_conflict_hold'], 1)
        self.assertTrue(all(d['action'] == 'hold' for d in review['decisions']))

    def test_explicit_distinction_cannot_publish_even_if_model_calls_it_endorsed(self):
        self.raw.write_text(page('<h2>Elections</h2><h3>2026</h3><h4>Endorsements</h4>' + listing('Moms Demand Action Gun Sense Candidate Distinction')))
        bp.import_capture(self.data, self.work, URL, self.raw, '2026-10-01T20:00:00+00:00'); bp.extract(self.data, self.work)
        self.review()
        review, audit = self.build()
        self.assertNotIn('added', audit['counts'])
        self.assertIn('distinction', review['decisions'][0]['reason'])

    def test_unavailable_capture_preserves_source_bytes(self):
        source = json.loads(bp.page_path(self.work, URL).read_text()); old = self.work / source['capture']
        before = old.read_bytes()
        with patch.object(bp.urllib.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = OSError('offline fixture')
            result = bp.capture(URL, self.work)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(old.read_bytes(), before)
        bp.extract(self.data, self.work)
        self.assertEqual(json.loads((self.work / 'manifest.json').read_text())['candidates'][0]['status'], 'unavailable')

    def test_missing_model_answer_is_not_cached(self):
        fake = {'model': bp.MODEL, 'answers': {}}
        class Response:
            def __enter__(self):
                from io import BytesIO
                return BytesIO(json.dumps(fake).encode())
            def __exit__(self, *args):
                pass
        with patch.object(bp.urllib.request, 'urlopen', return_value=Response()):
            with self.assertRaisesRegex(ValueError, 'Incomplete Jev'):
                bp.ask(self.work, 'fixture', {'q': bp.choice('Fixture question', {'yes': 'Yes', 'no': 'No'})}, 'fixture')
        self.assertFalse((self.work / 'decisions').exists())

    def test_acronym_overlap_is_checked_beyond_fuzzy_spelling(self):
        self.raw.write_text(page('<h2>Elections</h2><h3>2026</h3><h4>Endorsements</h4>' + listing('Service Employees International Union')))
        bp.import_capture(self.data, self.work, URL, self.raw, '2026-10-01T20:00:00+00:00'); bp.extract(self.data, self.work)
        self.review()
        self.data['positions'][0]['candidates'][0]['endorsements'] = [{
            'endorser': 'SEIU', 'relation': 'endorsed', 'phase': 'unspecified', 'url': 'https://example.org/endorsements'}]
        observed = []
        def screen(work, state, questions, key):
            observed.append(questions['new_entity']['instructions'])
            return {'new_entity': answer('overlap', ['distinct', 'curated', 'unclear'])}, 'fixture-overlap-reference'
        with patch.object(bp, 'ask', side_effect=screen):
            review, audit = bp.build_review(self.data, self.work, 'fixture-review', '2026-10-22', 'unused')
        self.assertIn('SEIU', observed[0])
        self.assertEqual(audit['counts']['entity_overlap_hold'], 1)
        self.assertTrue(all(d['action'] == 'hold' for d in review['decisions']))

    def test_archive_is_portable_immutable_and_omits_raw_html(self):
        self.review()
        review, _ = self.build()
        review_path = self.work / 'review.json'; bp.save(review_path, review)
        target = self.work / 'export'
        result = bp.archive(self.data, self.work, review_path, target)
        self.assertEqual(result['packets'], 1)
        self.assertEqual(result['jev_requests'], 4)
        self.assertFalse(list(target.rglob('*.html')))
        self.assertTrue((target / 'manifest.json').exists())
        with self.assertRaisesRegex(ValueError, 'already exists'):
            bp.archive(self.data, self.work, review_path, target)

    def test_missing_disposition_or_changed_model_answer_is_rejected(self):
        self.review(); path = self.work / 'results' / (self.row['packet_sha256'] + '.json')
        original = json.loads(path.read_text()); changed = deepcopy(original); changed['entries'] = []; bp.save(path, changed)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            bp.build_review(self.data, self.work, 'fixture-review', '2026-10-22', 'unused')
        changed = deepcopy(original); changed['entries'][0]['relationship']['probabilities']['endorsed'] = .5; bp.save(path, changed)
        with self.assertRaisesRegex(ValueError, 'Changed Jev'):
            bp.build_review(self.data, self.work, 'fixture-review', '2026-10-22', 'unused')

    def test_cache_response_requires_actual_selected_probability(self):
        self.assertFalse(bp.accepted(answer('endorsed', ['unclear']) | {'probabilities': {'endorsed': .2, 'unclear': .8}}, {'endorsed'}, .8))
        self.assertFalse(bp.accepted(answer('unclear', ['endorsed']), {'endorsed'}, .8))

    def test_decision_for_different_source_is_not_reusable(self):
        self.review(); path = self.work / 'results' / (self.row['packet_sha256'] + '.json'); result = json.loads(path.read_text())
        item = result['entries'][0]; oldpath = self.work / 'decisions' / (item['identity_ref'] + '.json'); request = json.loads(oldpath.read_text())
        request['request']['questions']['identity']['instructions'] += '\nUse a different source.'
        ref = bp.digest(bp.dump(request['request']).encode()); bp.save(self.work / 'decisions' / (ref + '.json'), request)
        item['identity_ref'] = ref; bp.save(path, result)
        with self.assertRaisesRegex(ValueError, 'request binding'):
            bp.build_review(self.data, self.work, 'fixture-review', '2026-10-22', 'unused')


if __name__ == '__main__':
    unittest.main()
