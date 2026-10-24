"""Refresh a shared local-action tracker across the current California roster.

Deterministic HTML/table capture and name shortlisting only. Jev reviews every
proposed identity, attributed meaning and date via research_gaza_gaps. Nothing
is published until its immutable draft is applied with reviewed_updates.py.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
import re
import urllib.request

from ballotpedia_endorsements import Document, digest, dump, save
from endorsement_extract import norm
import research_gaza_gaps as gaza

URL = 'https://ca.cair.com/sfba/ceasefire-tracker/'
PUBLISHER = 'CAIR-SFBA'
VERSION = 'cair-ceasefire-tables-v1'
TITLES = re.compile(r'^(?:Mayor Pro Tempore|Mayor Pro Tem|Vice Mayor|Board President|Vice President|Board Clerk|Board Member|Councilmember|Commissioner|Supervisor|President|Senator|Trustee|Mayor|Chair|Vice Chair|Rep\.)\s+', re.I)


def capture(raw, checked_on):
    packet = gaza.capture(raw, URL, checked_on)
    issue = re.search(r'The below ceasefire tracker provides information about local elected officials.+?Gaza\.', packet['text'])
    if not issue:
        raise ValueError('Missing explicit Gaza issue context for this tracker')
    doc = Document(raw.decode('utf-8', errors='replace'))
    sections = []; heading = None
    for el in doc.root.descendants({'h2', 'table'}):
        if el.tag == 'h2':
            heading = el.text(); continue
        if 'ea-advanced-data-table' not in el.attrs.get('class', '').split():
            continue
        if not heading:
            raise ValueError('Tracker table without a jurisdiction heading')
        date_match = re.search(r' – ([A-Z][a-z]+ \d{1,2}, \d{4})$', heading)
        event_date = datetime.strptime(date_match[1], '%B %d, %Y').date().isoformat() if date_match else None
        if not event_date and heading != 'Congressional Members':
            raise ValueError('Unrecognized tracker heading/date: ' + heading)
        section = {'heading': heading, 'event_date': event_date, 'rows': [], 'holds': []}
        for tr in el.descendants({'tr'}):
            cells = [c.text() for c in tr.descendants({'td'})]
            if not cells:
                continue
            if len(cells) != 2 or not all(cells):
                raise ValueError('Expected a complete two-cell tracker row')
            name = TITLES.sub('', cells[0]).strip()
            # Invisible formatting characters are not name distinctions.
            name = re.sub('[\u200b-\u200f\ufeff]', '', name)
            row = {'id': f'{len(sections)}:{len(section["rows"])}', 'name': name,
                   'source_name': cells[0], 'action': cells[1], 'holds': []}
            if re.search(r'\b(?:Supported|Opposed|Abstained)\b', name, re.I):
                row['holds'].append('Action appears in name cell; malformed source row')
            if cells[1] == 'N/A':
                row['holds'].append('N/A does not establish a position or action')
            if cells[1] in {'Supported amendment', 'Opposed amendment'}:
                row['holds'].append('Amendment subject unspecified in source section')
            section['rows'].append(row)
        if not section['rows']:
            raise ValueError('Empty tracker table; do not treat scrape omissions as no evidence')
        sections.append(section)
    if not sections:
        raise ValueError('No tracker tables; HTML is blocked or text scrape omitted tables')
    by_heading = defaultdict(list); by_roster = defaultdict(list)
    for s in sections:
        by_heading[s['heading']].append(s)
        by_roster[tuple(sorted(norm(r['name']) for r in s['rows']))].append(s)
    for group in by_heading.values():
        if len({tuple(norm(r['name']) for r in s['rows']) for s in group}) > 1:
            for s in group:
                s['holds'].append('Same dated heading attached to incompatible rosters')
    for group in by_roster.values():
        if len({s['heading'].split(' – ')[0] for s in group}) > 1:
            for s in group:
                s['holds'].append('Identical roster under different jurisdictions')
    return {'version': VERSION, 'source': packet, 'issue_context': issue[0], 'sections': sections}


def shortlist(data, source_name):
    """Name overlap is a lead, never a published identity decision."""
    tokens = [t for t in norm(source_name).split() if t not in {'dr', 'jr', 'sr', 'cpa'}]
    out = []
    for p in data['positions']:
        if '/state:ca' not in (p.get('ocd_division_id') or '') and not p.get('counties'):
            continue
        for c in p.get('candidates') or []:
            other = [t for t in norm(c['name']).split() if t not in {'dr', 'jr', 'sr', 'cpa'}]
            if len(tokens) >= 2 and len(other) >= 2 and (
                    set(tokens) <= set(other) or set(other) <= set(tokens) or
                    (tokens[-1] == other[-1] and tokens[0][0] == other[0][0])):
                out.append((p, c))
    return out


def proposals(data, captured, directory):
    packet = captured['source']; claims = []; dispositions = []
    ids = [int(e['id'][3:]) for p in data['positions'] for roster in
           ('candidates', 'filed_candidates_not_confirmed_on_ballot', 'qualified_write_in_candidates')
           for c in p.get(roster) or [] for e in c.get('gaza_evidence') or []]
    next_id = max(ids, default=0) + 1
    for section in captured['sections']:
        # Preserve the complete heading and action row neighborhood for Jev.
        text = packet['text']; start = text.index('## ' + section['heading'])
        end = text.find('\n## ', start + 1)
        context = text[start:end if end != -1 else len(text)]
        for row in section['rows']:
            leads = shortlist(data, row['name'])
            holds = section['holds'] + row['holds']
            disposition = {'row_id': row['id'], 'heading': section['heading'], **row,
                           'leads': [{'position_id': p['id'], 'candidate': c['name']} for p,c in leads]}
            if holds or not leads:
                disposition.update(status='held_source' if holds else 'no_printed_roster_lead', reasons=holds)
                dispositions.append(disposition); continue
            disposition.update(status='pending_jev', claim_indices=[])
            for p, c in leads:
                event_date = section['event_date']
                summary = f"CAIR-SFBA's tracker lists {c['name']}: {row['action']}."
                if not event_date:
                    summary = 'Undated CAIR-SFBA assessment (not a current vote): ' + row['action'] + '.'
                # Keep a full name/action quote. Never shorten away qualifications.
                quote = row['source_name'] + ' | ' + row['action']
                if ' '.join(quote.split()) not in ' '.join(context.split()):
                    # Paragraphs inside cells flush the generic text extractor
                    # before its table separator. Preserve the actual excerpt;
                    # never invent a pipe that does not occur in the packet.
                    quote = row['source_name'] + ' ' + row['action']
                if ' '.join(quote.split()) not in ' '.join(context.split()) or len(quote.split()) > 25 or len(summary) > 240:
                    disposition.setdefault('reasons', []).append('Quote/summary needs manual source review')
                    continue
                record = {'id': f'GE-{next_id:04d}', 'date': event_date or packet['checked_on'],
                          'date_method': 'source_stated' if event_date else 'source_observed',
                          'date_note': ('Tracker section dates the reported local action; not a verified roll-call transcript.' if event_date else
                                        'Inspection date of an undated historical tracker assessment; not the date of a statement, vote, or current position.'),
                          'summary': summary, 'quote': quote, 'dimension': 'actions_votes' if event_date else 'other',
                          'source_kind': 'advocacy_tracker' if event_date else 'voter_guide'}
                next_id += 1
                claim = {'position_id': p['id'], 'candidate': c['name'], 'field': 'gaza_evidence',
                         'capture': str(directory/'packet.json'), 'raw_capture': str(directory/'source.html'),
                         'publisher': PUBLISHER, 'role': 'aggregator', 'record': record,
                         'contexts': [captured['issue_context'], section['heading'], quote],
                         'identity_basis': 'Named historical official in the supplied California local body. Verify the person and jurisdiction against the current candidacy; office may have changed. No name-only assumption.',
                         'date_basis': record['date_note'], 'date_quote': section['heading']}
                disposition['claim_indices'].append(len(claims)); claims.append(claim)
            if not disposition['claim_indices']:
                disposition['status'] = 'held_source'
            dispositions.append(disposition)
    return claims, dispositions


def fetch_html(serper_key=None):
    """Direct fetch, with explicit Serper HTML retrieval for blocked hosts.

    Serper's default text/markdown scraper drops this page's tables. The actual
    includeHtml response is required; search snippets never support a claim.
    """
    from research_endorsements import Fetcher, Blocked
    try:
        raw, mime, final = Fetcher().request(URL)
        capture(raw, datetime.now().date().isoformat())
        return raw, {'method': 'direct HTML', 'final_url': final}
    except (ValueError, OSError, Blocked):
        if not serper_key:
            raise ValueError('Source blocked/incomplete; provide a Serper key for actual HTML retrieval')
    req = urllib.request.Request('https://scrape.serper.dev',
        data=dump({'url': URL, 'includeHtml': True}).encode(),
        headers={'X-API-KEY': serper_key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.load(response)
    raw = result.get('html', '').encode()
    capture(raw, datetime.now().date().isoformat())
    return raw, {'method': 'Serper scrape includeHtml retrieval', 'source_url': URL}


def draft(data, directory, work, key, review_id, checked_on, extra_claims=None, workers=3, identity_bridges=None, model='jev-1.14.0'):
    captured = json.loads((directory/'tracker.json').read_text())
    actual = capture((directory/'source.html').read_bytes(), captured['source']['checked_on'])
    if actual != captured or json.loads((directory/'packet.json').read_text()) != captured['source']:
        raise ValueError('Normalized capture differs from actual source bytes')
    claims, dispositions = proposals(data, captured, directory)
    claims += extra_claims or []
    for claim in claims:
        for bridge in identity_bridges or []:
            if (claim['position_id'], claim['candidate']) == (bridge['position_id'], bridge['candidate']):
                claim['identity_captures'] = bridge['captures']
    # Pre-cache bounded independent requests; build() rechecks all source bytes,
    # consumes the exact same request cache and preserves actual model answers.
    def review(claim):
        return gaza.review_claim(data, claim, gaza.load_packet(claim['capture']), work, key, model=model)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(review, claims))
    result, audit = gaza.build(data, claims, work, key, review_id, checked_on, model=model)
    for row in dispositions:
        for idx in row.get('claim_indices', []):
            decision = result['decisions'][idx]
            row.setdefault('decisions', []).append({'candidate': decision['candidate'], 'position_id': decision['position_id'],
                'action': decision['action'], 'reason': decision['reason'], 'jev_ref': decision['jev_ref']})
        if row['status'] == 'pending_jev':
            row['status'] = 'reviewed'
    audit.update(source_dispositions=dispositions, parser_version=VERSION, model=model,
                 scope='All printed California candidacies; no old done/evidence-presence filter')
    return result, audit


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', type=Path, default=Path('2026-11-03_Bay_Area_Elections.json'))
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('capture'); p.add_argument('--html', type=Path); p.add_argument('--serper-key-file', type=Path)
    p.add_argument('--checked-on', required=True); p.add_argument('--output-dir', type=Path, required=True)
    p = sub.add_parser('draft'); p.add_argument('--capture-dir', type=Path, required=True)
    p.add_argument('--jev-key-file', type=Path, required=True); p.add_argument('--work-dir', type=Path, required=True)
    p.add_argument('--extra-claims', type=Path); p.add_argument('--id', required=True)
    p.add_argument('--identity-bridges', type=Path)
    p.add_argument('--checked-on', required=True); p.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.command == 'capture':
        if args.output_dir.exists():
            raise ValueError('Preserve runs; choose a fresh capture directory')
        if args.html:
            raw = args.html.read_bytes(); retrieval = {'method': 'supplied actual HTML'}
        else:
            raw, retrieval = fetch_html(args.serper_key_file.read_text().strip() if args.serper_key_file else None)
        result = capture(raw, args.checked_on)
        args.output_dir.mkdir(parents=True)
        (args.output_dir/'source.html').write_bytes(raw)
        save(args.output_dir/'packet.json', result['source']); save(args.output_dir/'tracker.json', result)
        save(args.output_dir/'retrieval.json', retrieval)
        print(dump({'sections': len(result['sections']), 'rows': sum(len(s['rows']) for s in result['sections'])}))
    else:
        if args.output.exists() or args.output.with_suffix('.audit.json').exists():
            raise ValueError('Preserve reviews; choose a fresh output')
        r, a = draft(json.loads(args.dataset.read_text()), args.capture_dir, args.work_dir,
            args.jev_key_file.read_text().strip(), args.id, args.checked_on,
            json.loads(args.extra_claims.read_text()) if args.extra_claims else None,
            identity_bridges=json.loads(args.identity_bridges.read_text()) if args.identity_bridges else None)
        save(args.output, r); save(args.output.with_suffix('.audit.json'), a)
        print(dump({'changes': sum(d['action']=='change' for d in r['decisions']), 'decisions': len(r['decisions'])}))


if __name__ == '__main__':
    main()
