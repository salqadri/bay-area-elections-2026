"""Offline scope and source-shape checks for local candidate enrichment.

Identity/stance judgments remain source-reviewed model decisions. An actual
Ballotpedia Person infobox establishes the page's profile format mechanically;
it does not establish that the person matches a candidate.
"""
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse
import json
from pathlib import Path
import re


def local_positions(data, county, include_county_courts=True):
    return [p for p in data['positions']
            if county in p.get('counties', []) and p['ballot_status'] == 'confirmed'
            and (p['government_level'] in {'County', 'City or town'}
                 or (p['office_category'] == 'County board of education'
                     and county.lower() in p['jurisdiction'].lower())
                 or (include_county_courts and p['office_category'] == 'Superior Court'
                     and county.lower() in p['jurisdiction'].lower()))]


class _ProfileShape(HTMLParser):
    def __init__(self):
        super().__init__()
        self.person = False

    def handle_starttag(self, tag, attrs):
        classes = set((dict(attrs).get('class') or '').split())
        if tag in {'div', 'table'} and {'infobox', 'person'} <= classes:
            self.person = True


def ballotpedia_profile_shape(raw_html, url):
    """Reject election/endorsement directories even when they mention the name."""
    parsed = urlsplit(url)
    path = unquote(parsed.path).lower()
    if (parsed.scheme != 'https' or parsed.hostname not in {'ballotpedia.org', 'www.ballotpedia.org'}
            or re.search(r'/(?:endorsements_|category:|special:)|_elections(?:_|,)|/main_page', path)):
        return False
    parser = _ProfileShape()
    parser.feed(raw_html)
    return parser.person


def accepted_link(record, decision, raw_html):
    """Keep identity at .90; verify URL role using the relevant source contract.

    Ballotpedia profile format is an HTML fact. Other website/account ownership
    requires the separate source-role decision at .90. No stance is inferred.
    """
    answers = decision['response']['answers']
    identity, role = answers['identity'], answers['link']
    if identity.get('choice') != 'match' or identity['probabilities'].get('match', 0) < .90:
        return False
    if role.get('choice') != 'supported':
        return False
    if record['field'] == 'ballotpedia_url':
        return ballotpedia_profile_shape(raw_html, record['url'])
    return role['probabilities'].get('supported', 0) >= .90


def inventory(data, county):
    """Plan every named on-ballot local candidacy, including unresearched ones.

    A roster proves ballot appearance. It is never evidence that research or
    enrichment has been completed. These queries are discovery leads only.
    """
    rows = []
    for position in local_positions(data, county):
        for candidate in position.get('candidates') or []:
            name = candidate['name']
            place = position['jurisdiction']
            rows.append({'position_id': position['id'], 'candidate': name,
                         'office': position['office'], 'jurisdiction': place,
                         'district_or_seat': position.get('district_or_seat'),
                         'queries': [
                             f'"{name}" "{place}" 2026 campaign',
                             f'"{name}" California (Gaza OR Palestine OR Israel OR ceasefire OR divestment)',
                             f'"{name}" (endorsements OR "CAIR Action" OR "Vote for Peace")',
                             f'"{name}" ("AB 715" OR IHRA OR antisemitism)',
                         ],
                         'recorded_links': {field: candidate[field] for field in
                                            ('ballotpedia_url', 'campaign_url', 'x_url') if candidate.get(field)}})
    return {'version': 1, 'county': county, 'candidates': rows,
            'unnamed_contests': [p['id'] for p in local_positions(data, county) if not p.get('candidates')]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Plan local candidate research without network or model calls.')
    parser.add_argument('--county', required=True)
    parser.add_argument('--dataset', type=Path, default=Path(__file__).resolve().parent.parent / '2026-11-03_Bay_Area_Elections.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(json.loads(args.dataset.read_text()), args.county)
    if not result['candidates']:
        raise SystemExit('No confirmed local candidates for this county; verify the official roster first.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(len(result['candidates']), 'named local candidacies planned; no source research performed.')
