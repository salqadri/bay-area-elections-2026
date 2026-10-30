#!/usr/bin/env python3
"""Build a static, display-only guide from the published election JSON and plan."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_PLAN = ROOT / 'research/candidate-recommendations/recommendations-2026-10-28-latest.json'
POSITION_FIELDS = ('id', 'counties', 'government_level', 'office_category', 'jurisdiction',
                   'office', 'district_or_seat', 'seats', 'term', 'election_type',
                   'ballot_status', 'candidate_list_status', 'partisan', 'ocd_division_id',
                   'countywide_electorate')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project(dataset, plan):
    """Copy published decisions and text. Never infer a pick or write new prose."""
    publication = dataset.get('pro_palestine_grading', {}).get('publication_id')
    if publication != plan.get('source_score_publication_id'):
        raise ValueError('Recommendation and score publication IDs differ; rebuild the published plan first.')
    scope = {c['name'] for c in dataset['election']['counties_in_scope']}
    by_id = {}
    for race in plan['races']:
        if race['position_id'] in by_id:
            raise ValueError('Duplicate recommendation: ' + race['position_id'])
        by_id[race['position_id']] = race
    positions = []
    for position in dataset['positions']:
        if position['ballot_status'] != 'confirmed' or not scope.intersection(position['counties']):
            continue
        race = by_id.get(position['id'])
        if not race or race['ballot_status'] != position['ballot_status']:
            raise ValueError('Missing or stale recommendation for ' + position['id'])
        printed = position.get('candidates')
        candidates = (printed or []) + (position.get('qualified_write_in_candidates') or [])
        if printed is None and not candidates:
            roster = None
        else:
            # Verify the plan's full roster, including provisional filers, but
            # publish only printed candidates and qualified write-ins.
            plan_candidates = (printed or []) + (position.get('filed_candidates_not_confirmed_on_ballot') or []) + (position.get('qualified_write_in_candidates') or [])
            expected = [(c['name'], c.get('party'), c.get('pro_palestine_score_grade')) for c in plan_candidates]
            actual = [(c['name'], c.get('party'), c.get('grade')) for c in race['roster']]
            if expected != actual:
                raise ValueError('Recommendation roster differs for ' + position['id'])
            roster = []
            for candidate in candidates:
                record = {k: candidate[k] for k in ('name', 'party', 'incumbent') if k in candidate}
                if candidate in (position.get('qualified_write_in_candidates') or []):
                    record['write_in'] = True
                explanation = candidate.get('pro_palestine_explanation') or {}
                evaluation = candidate.get('pro_palestine_evaluation') or {}
                if explanation:
                    for key in ('publication_id', 'candidate_id', 'request_sha256'):
                        if explanation.get(key) != evaluation.get(key):
                            raise ValueError('Stale candidate explanation: ' + candidate['name'])
                    record['blurb'] = explanation.get('summary', '')
                roster.append(record)
        recommended = race.get('recommended')
        if recommended and recommended not in [c['name'] for c in candidates or []]:
            raise ValueError('Recommended candidate is not on the roster: ' + position['id'])
        why = race.get('recommend_reason_text') or race.get('summary') or {}
        if recommended and not why.get('text'):
            raise ValueError('Recommended race is missing its published rationale: ' + position['id'])
        if not recommended and not race.get('recommend_reason'):
            raise ValueError('Race is missing its published no-recommendation reason: ' + position['id'])
        projected = {k: position[k] for k in POSITION_FIELDS if k in position}
        projected['candidates'] = roster
        projected['recommendation'] = {
            'candidate': recommended,
            'reason': why['text'] if recommended else race['recommend_reason'],
        }
        positions.append(projected)
    if len({p['id'] for p in positions}) != len(positions):
        raise ValueError('Duplicate contest IDs')
    if not positions:
        raise ValueError('No confirmed contests in the selected coverage')
    return {
        'format': 'tall-voter-guide/v1',
        'election': dataset['election'],
        'codes': {'party': dataset['codes']['party']},
        'recommendations_date': plan['generated_on'][:10],
        'county_election_urls': dataset.get('address_lookup', {}).get('county_election_urls', {}),
        'positions': positions,
    }


def build(dataset_path, plan_path, output, google_key=''):
    output = output.resolve()
    if HERE.is_relative_to(output) or dataset_path.resolve().is_relative_to(output) or plan_path.resolve().is_relative_to(output):
        raise ValueError('Output must be a separate generated directory, not a directory containing the source inputs.')
    dataset = json.loads(dataset_path.read_text())
    plan = json.loads(plan_path.read_text())
    if sha(dataset_path) != plan['source_dataset_sha256']:
        raise ValueError('The dataset changed after this recommendation plan. Refresh the published plan first; no stale import is allowed.')
    payload = project(dataset, plan)
    # Only an explicit allowlist is published. No source evidence, scores, credentials,
    # research archives or model requests are copied into the Hosting directory.
    staging = output.with_name(output.name + '-staging')
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    payload['source_sha256'] = {'dataset': sha(dataset_path), 'recommendations': sha(plan_path)}
    (staging / 'guide.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    for name in ('app.js', 'ballot-order.js', 'google-autocomplete.js', 'style.css', 'favicon.svg'):
        shutil.copyfile(HERE / name, staging / name)
    shutil.copyfile(ROOT / 'src/address-services.js', staging / 'address-services.js')
    registry = json.loads((ROOT / 'research/california-counties.json').read_text())
    matcher = (ROOT / 'src/address-matcher.js').read_text().replace(
        '__CALIFORNIA_COUNTY_FIPS_JSON__', json.dumps({c['fips']: c['name'] for c in registry['counties']}))
    (staging / 'address-matcher.js').write_text(matcher)
    config = {'googleMapsApiKey': google_key.strip()}
    (staging / 'config.js').write_text('window.TALL_CONFIG = ' + json.dumps(config).replace('<', '\\u003c') + ';\n')
    html = (HERE / 'index.template.html').read_text()
    for name in ('index.html', 'candidates.html'):
        (staging / name).write_text(html)
    (staging / '404.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Page not found · TALL</title><body style="font:18px system-ui;padding:10vw;background:#f7f6ee;color:#173e35"><h1>Let’s get you back to the guide.</h1><p>This page could not be found.</p><a href="/">The TALL Voter Guide →</a></body></html>')
    (staging / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: https://tall-voter-guide.web.app/sitemap.xml\n')
    (staging / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://tall-voter-guide.web.app/</loc></url><url><loc>https://tall-voter-guide.web.app/candidates.html</loc></url></urlset>')
    release = {'publication': dataset['election'].get('publication_version'),
               'source_sha256': payload['source_sha256'], 'contests': len(payload['positions']),
               'candidates': sum(len(p['candidates'] or []) for p in payload['positions']),
               'google_autocomplete_configured': bool(google_key.strip()),
               'files': {p.name: sha(p) for p in sorted(staging.iterdir())}}
    (staging / 'release.json').write_text(json.dumps(release, indent=2) + '\n')
    if output.exists():
        shutil.rmtree(output)
    staging.rename(output)
    print(f"Built The TALL Voter Guide: {release['contests']} contests, {release['candidates']} candidacies; {sum(p.stat().st_size for p in output.iterdir()):,} bytes")
    if not google_key.strip():
        print('Google autocomplete is not configured; manual address lookup remains available.')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT / '2026-11-03_Bay_Area_Elections.json')
    parser.add_argument('--recommendations', type=Path, default=DEFAULT_PLAN)
    parser.add_argument('--output', type=Path, default=HERE / 'dist')
    args = parser.parse_args()
    build(args.dataset, args.recommendations, args.output, os.environ.get('TALL_GOOGLE_MAPS_API_KEY', ''))
