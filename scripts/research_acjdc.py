"""Draft source-bound ACJDC updates; no searches, scoring or automatic publication.

Use a captured endorsement HTML page and the reviewed questionnaire packet.
Exact names/aliases must match a unique confirmed candidacy. Unknown people,
non-candidate measures and No recommendation are held, never treated as support
or opposition. Applying the resulting review uses reviewed_updates.py.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from endorsement_extract import PageParser, norm
from reviewed_updates import identity

ROOT = Path(__file__).resolve().parent.parent
NAME = 'Alameda County Jewish Democratic Club'
URL = 'https://www.acjdc.org/endorsements'
ALIASES = {norm(k): v for k, v in {
    'Igor Tregub': 'Igor A. Tregub', 'Eryka Mathews-Cain': 'Eryka N Mathews-Cain',
    'Shirley Weber': 'Shirley N. Weber', 'Malia Cohen': 'Malia M. Cohen',
    'Sally Lieber': 'Sally J. Lieber',
}.items()}
CARRY = 'The November 2026 page explicitly carries this primary endorsement forward for candidates who advanced.'


def parse_endorsements(html):
    parser = PageParser(URL); parser.feed(html); parser.flush()
    phase = None; records = []
    for line in parser.lines:
        if line.startswith('## November 2026 General Election Endorsements'):
            phase = 'general'; continue
        if line.startswith('## June 2026 Primary Endorsements'):
            phase = 'primary'; continue
        if line.startswith('### Ballot measures') or line == 'Endorsement Process':
            phase = None; continue
        if not phase or ':' not in line or line.startswith('#'):
            continue
        office, names = line.split(':', 1)
        if re.search(r'measure|proposition', office, re.I):
            continue
        for part in names.split(';'):
            part = part.strip()
            rank = re.search(r'\s*[—–-]\s*#(\d+)$', part)
            name = part[:rank.start()].strip() if rank else part
            records.append({'source_office': office.strip(), 'source_name': name, 'phase': phase,
                            'rank': int(rank[1]) if rank else None,
                            'no_recommendation': name.casefold() == 'no recommendation'})
    return records


def draft(data, html, packet):
    checked = packet['checked_on']
    people = {}
    for p in data['positions']:
        if p.get('ballot_status') != 'confirmed':
            continue
        for c in p.get('candidates') or []:
            people.setdefault(norm(c['name']), []).append((p, c))
    review = {'version': 1, 'id': 'acjdc-questionnaires-2026-11-02',
              'election_date': data['election']['date'], 'reviewed_on': checked,
              'counties': ['Alameda', 'Contra Costa', 'San Francisco', 'San Mateo', 'Santa Clara'],
              'sources': {'endorsements': {'url': URL, 'publisher': NAME, 'role': 'endorser',
                  'checked_on': checked, 'retrieval': 'first_party_html',
                  'content_sha256': hashlib.sha256(html.encode()).hexdigest()}},
              'notes': {}, 'decisions': []}
    audit = {'endorsement_observations': [], 'held': [], 'questionnaires': len(packet['responses'])}
    for row in parse_endorsements(html):
        if row['no_recommendation']:
            audit['held'].append({**row, 'reason': 'No recommendation is not candidate opposition.'}); continue
        label = ALIASES.get(norm(row['source_name']), row['source_name'])
        matches = people.get(norm(label), [])
        if len(matches) != 1:
            audit['held'].append({**row, 'reason': 'No unique confirmed current candidacy.'}); continue
        p, c = matches[0]
        office = packet.get('endorsement_offices', {}).get(norm(row['source_office']))
        if not office or office['position_id'] != p['id'] or office['identity'] != identity(p):
            audit['held'].append({**row, 'reason': 'Source office differs from current candidacy.'}); continue
        before = next((e for e in c.get('endorsements') or []
                       if e['endorser'] == NAME and e['phase'] == row['phase'] and e['url'] == URL), None)
        after = deepcopy(before) if before else {'endorser': NAME, 'kind': 'organization',
            'relation': 'endorsed', 'phase': row['phase'], 'url': URL, 'verification': 'endorser_statement'}
        after['checked_on'] = checked
        after['verification'] = 'endorser_statement'
        if row['phase'] == 'primary':
            after['recommendation_context'] = CARRY
        if row['rank']:
            after['recommendation_rank'] = row['rank']
        audit['endorsement_observations'].append({**row, 'position_id': p['id'], 'candidate': c['name'],
                                                'new_record': before is None})
        if before == after:
            continue
        review['decisions'].append({'id': 'endorsement-'+p['id']+'-'+norm(c['name']).replace(' ', '-')+'-'+row['phase'],
            'action': 'change', 'field': 'endorsements', 'source_key': 'endorsements',
            'position_id': p['id'], 'candidate': c['name'], 'identity': identity(p),
            'before': before, 'after': after, 'reason': 'Current first-party endorsement, with exact phase and rank.',
            'evidence': {'identity_basis': 'Exact full name or reviewed middle-name alias in the current confirmed roster and matching source office.',
                         'date_basis': 'Source inspected on '+checked+'; phase is explicit on the page.',
                         'relationship_basis': 'Named under the club endorsement heading; primary carry-forward and ranked preferences are preserved.'}})
    used_ids = {int(e['id'][3:]) for p in data['positions'] for roster in (
        'candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates')
        for c in p.get(roster) or [] for e in c.get('gaza_evidence') or []}
    next_id = max(used_ids) + 1
    positions = {p['id']: p for p in data['positions']}
    for response in packet['responses']:
        p = positions[response['position_id']]
        c = next(c for c in p['candidates'] if c['name'] == response['candidate'])
        key = response['file_id']
        review['sources'][key] = {'url': response['source_url'], 'publisher': NAME, 'role': 'aggregator',
            'checked_on': checked, 'retrieval': 'google_drive_text_extraction_reviewed_against_questionnaire',
            'content_sha256': response['source_content_sha256']}
        items = [('framing_balance', s) for s in response['israel_summaries']]
        if response['ab715_summary']:
            items.append(('antisemitism_education', response['ab715_summary']))
        for dimension, summary in items:
            existing = next((e for e in c.get('gaza_evidence') or []
                             if e['url'] == response['source_url'] and e['summary'] == summary), None)
            if existing:
                continue
            record = {'id': 'GE-'+str(next_id).zfill(4), 'url': response['source_url'], 'summary': summary,
                'date': response['uploaded_on'], 'dimension': dimension, 'checked_on': checked,
                'source_kind': 'candidate_questionnaire', 'date_method': 'page_metadata',
                'date_note': 'Drive upload metadata dates the '+response['phase']+' questionnaire file, not the actual response. Response date is not stated.'}
            next_id += 1
            review['decisions'].append({'id': record['id'].lower(), 'action': 'change', 'field': 'gaza_evidence',
                'source_key': key, 'position_id': p['id'], 'candidate': c['name'], 'identity': identity(p),
                'before': None, 'after': record, 'reason': 'Candidate-authored questionnaire response; club question preamble is not attributed to the candidate.',
                'evidence': {'identity_basis': 'Questionnaire name and source office matched to this active candidacy; any different source office is explicitly retained in the response summary.',
                    'date_basis': record['date_note'],
                    'issue_basis': 'Reviewed answer to the Israel/BDS or AB 715 topic; no position inferred from an unanswered or inapplicable question.'}})
    return review, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path, required=True)
    parser.add_argument('--responses', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    review, audit = draft(json.loads((ROOT/'2026-11-03_Bay_Area_Elections.json').read_text()),
                          args.html.read_text(), json.loads(args.responses.read_text()))
    for path, value in ((args.output, review), (args.audit, audit)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
    print('Drafted',len(review['decisions']),'changes;',len(audit['held']),'held observations')


if __name__ == '__main__':
    main()
