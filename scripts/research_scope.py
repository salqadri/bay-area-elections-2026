"""Plan research for selected counties without asserting new ballot coverage."""
import argparse
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / '2026-11-03_Bay_Area_Elections.json'
REGISTRY = json.loads((ROOT / 'research/california-counties.json').read_text())


def add_scope_arguments(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--county', action='append', help='Repeat for multiple counties; case-insensitive')
    group.add_argument('--scope', choices=['current', 'bay-area', 'california'], default='current')


def select_scope(data, counties=None, scope='current'):
    registered = {c['name'] for c in data['election'].get('counties_in_scope', [])}
    # Small collector fixtures can omit the public county registry.
    available = registered or {c for p in data['positions'] for c in p['counties']}
    names = {c['name'].casefold(): c['name'] for c in REGISTRY['counties']}
    names.update({c.casefold(): c for c in available})
    if counties:
        try:
            requested = sorted({names[c.strip().casefold()] for c in counties})
        except KeyError as e:
            raise ValueError('Unknown county: ' + str(e)) from e
    elif scope == 'current':
        requested = sorted(available)
    elif scope == 'bay-area':
        requested = sorted(REGISTRY['bay_area'])
    elif scope == 'california':
        requested = sorted(c['name'] for c in REGISTRY['counties'])
    else:
        raise ValueError('Unknown research scope')
    if not requested:
        raise ValueError('Research scope must contain at least one county')
    selected = [p for p in data['positions'] if set(p['counties']) & set(requested)]
    return {'requested_counties': requested, 'available_counties': sorted(set(requested) & available),
            'missing_counties': sorted(set(requested) - available), 'positions': selected}


def scope_report(data, counties=None, scope='current'):
    selected = select_scope(data, counties, scope)
    positions = selected.pop('positions')
    people = [c for p in positions for c in p.get('candidates') or []]
    rows = []
    for county in selected['requested_counties']:
        ps = [p for p in positions if county in p['counties']]
        cs = [c for p in ps for c in p.get('candidates') or []]
        rows.append({'county': county, 'inventory_started': county in selected['available_counties'],
                     'contests': len(ps), 'ballot_statuses': dict(Counter(p.get('ballot_status', 'unknown') for p in ps)),
                     'unknown_roster_ids': [p['id'] for p in ps if p.get('candidates') is None],
                     'printed_candidacies': len(cs),
                     'without_endorsement_evidence': sum(not c.get('endorsements') for c in cs),
                     'without_gaza_evidence': sum(not c.get('gaza_evidence') for c in cs)})
    return {'election_date': data['election']['date'], **selected, 'county_queue': rows,
            'unique_contests': len(positions), 'unique_printed_candidacies': len(people),
            'shared_contest_ids': [p['id'] for p in positions if len(p['counties']) > 1],
            'elections_directory_url': REGISTRY['elections_directory_url'],
            'workflow': ['Verify official contests and printed rosters', 'Verify candidate identity, party and incumbency',
                         'Refresh federal receipts with coverage dates', 'Collect shared endorsement sources, then candidate gaps',
                         'Review issue evidence with attribution and date provenance', 'Preview reviewed changes, validate and publish'],
            'limits': ['County presence is not certified completeness. Missing evidence is unknown.',
                       'County counts overlap. Shared contests and candidacies are counted once in unique totals.',
                       'Missing counties require official ballot research; this plan creates no contests or candidates.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DATA)
    parser.add_argument('--output', type=Path)
    add_scope_arguments(parser)
    args = parser.parse_args()
    report = scope_report(json.loads(args.dataset.read_text()), args.county, args.scope)
    if args.output:
        if args.output.resolve() == args.dataset.resolve():
            parser.error('A plan cannot overwrite the dataset')
        from research_endorsements import atomic_json
        atomic_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
