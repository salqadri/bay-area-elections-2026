#!/usr/bin/env python3
"""Capture the public Palestine tracker and preview reviewed candidate attachments.

Standard library only. Source contents are data, never executable instructions.
XLSX supplies values/links/notes; rendered HTML supplies current dropdown colors
which Google omits from XLSX and effectiveFormat. Nothing writes election data.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import tempfile
import unicodedata
import urllib.request
import zipfile
from html.parser import HTMLParser
from io import BytesIO
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = '1VU1y_jSb2hanU2MrLsjRx8tujB-C--UAQ2EahaTXGUo'
SOURCE_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit'
EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL_NS = '{http://schemas.openxmlformats.org/package/2006/relationships}'
TABS = {
    '119th House': dict(gid=1984730710, rows=218, columns=83, header_rows=4, first=3, last=4, location=5, start=10, end=73, congress=119, chamber='House'),
    '119th Senate': dict(gid=1260635943, rows=51, columns=43, header_rows=4, first=3, last=4, location=5, start=9, end=31, congress=119, chamber='Senate'),
    '118th House': dict(gid=1289123714, rows=213, columns=97, header_rows=2, first=2, last=3, location=4, start=9, end=57, congress=118, chamber='House'),
    '118th Senate': dict(gid=0, rows=53, columns=30, header_rows=2, first=2, last=3, location=4, start=7, end=20, congress=118, chamber='Senate'),
}
PALETTE = {
    '#d4edbc': 'positive', '#11734b': 'positive', '#00ff00': 'positive',
    '#b7e1cd': 'positive', '#d9ead3': 'positive',
    '#ffcfc9': 'negative', '#b10202': 'negative', '#ff0000': 'negative', '#f4cccc': 'negative', '#f5caca': 'negative',
    '#ffe5a0': 'neutral', '#fff2cc': 'neutral', '#e8eaed': 'neutral',
    '#b7b7b7': 'neutral', '#d9d9d9': 'neutral', '#999999': 'neutral',
}
SCOPE_NOTE = ('Source-selected legislative actions and letters/statements from the tracker’s four 118th/119th Congress tabs; '
              'these tabs include earlier dated actions and are not a complete congressional roll-call history. '
              'The same historical action can appear in multiple tabs; counts are source entries, not unique votes. '
              'The tracker describes its creators as anti-Zionist DSA comrades and mainly covers Democratic-caucus members. '
              'Positive/negative colors reproduce that source’s assessment, not this site’s verdict. '
              'A blank, not elected, not voting or not on committee entry does not establish a position. '
              'Sponsorships, petitions, letters and statements are labeled separately from votes. '
              'Spreadsheet grades, ranks, composite scores, endorsements and funding totals are not imported as votes or USCPR grades.')


def fail(message):
    raise ValueError(message)


def col_name(number):
    result = ''
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def coordinates(ref):
    match = re.fullmatch(r'([A-Z]+)([1-9][0-9]*)', ref.replace('$', ''))
    if not match:
        fail(f'Invalid cell reference: {ref!r}')
    number = 0
    for char in match[1]:
        number = number * 26 + ord(char) - 64
    return number, int(match[2])


def in_ranges(ref, ranges):
    column, row = coordinates(ref)
    return in_boxes(column, row, range_boxes(ranges))


def range_boxes(ranges):
    result = []
    for item in ranges.split():
        a, _, b = item.partition(':')
        left, top = coordinates(a)
        right, bottom = coordinates(b or a)
        result.append((left, top, right, bottom))
    return result


def in_boxes(column, row, boxes):
    for left, top, right, bottom in boxes:
        if left <= column <= right and top <= row <= bottom:
            return True
    return False


def text_content(node):
    return ''.join(x.text or '' for x in node.iter(f'{{{NS["s"]}}}t')) if node is not None else ''


def color(fill):
    if fill is None:
        return None
    element = fill.find('s:patternFill', NS)
    if element is None or element.get('patternType') != 'solid':
        return None
    fg = element.find('s:fgColor', NS)
    rgb = fg.get('rgb', '') if fg is not None else ''
    if fg is not None and fg.get('theme') == '0' and not fg.get('tint'):
        return '#ffffff'  # Google export's light/background theme color.
    if not re.fullmatch(r'[0-9A-Fa-f]{8}', rgb):
        fail('Unsupported non-RGB source fill; review the source before refreshing')
    return '#' + rgb[-6:].lower()


def parse_xlsx(raw):
    if len(raw) > 20_000_000 or not raw.startswith(b'PK'):
        fail('Source is not a bounded XLSX file (login/error pages are rejected)')
    try:
        archive = zipfile.ZipFile(BytesIO(raw))
        if sum(x.file_size for x in archive.infolist()) > 80_000_000:
            fail('Expanded workbook exceeds size limit')
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        relationships = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        paths = {r.get('Id'): posixpath.normpath(posixpath.join('xl', r.get('Target'))) for r in relationships}
        shared = ET.fromstring(archive.read('xl/sharedStrings.xml'))
        strings = [text_content(x) for x in shared]
        styles = ET.fromstring(archive.read('xl/styles.xml'))
        fills = [color(x) for x in styles.find('s:fills', NS)]
        cell_styles = [fills[int(x.get('fillId', 0))] for x in styles.find('s:cellXfs', NS)]
        dxfs = [color(x.find('s:fill', NS)) for x in styles.find('s:dxfs', NS)]
        result = {}
        for sheet in workbook.findall('s:sheets/s:sheet', NS):
            title = sheet.get('name')
            if title not in TABS:
                continue
            path = paths[sheet.get(f'{{{NS["r"]}}}id')]
            root = ET.fromstring(archive.read(path))
            relpath = posixpath.join(posixpath.dirname(path), '_rels', posixpath.basename(path) + '.rels')
            rels = ET.fromstring(archive.read(relpath)) if relpath in archive.namelist() else []
            targets = {x.get('Id'): x for x in rels}
            links, comments = {}, {}
            for link in root.findall('s:hyperlinks/s:hyperlink', NS):
                relationship = targets.get(link.get(f'{{{NS["r"]}}}id'))
                if relationship is not None:
                    target = relationship.get('Target', '')
                    if target.startswith(('https://', 'http://')):
                        links[link.get('ref')] = target
            for relationship in rels:
                if relationship.get('Type', '').endswith('/comments'):
                    comment_path = posixpath.normpath(posixpath.join(posixpath.dirname(path), relationship.get('Target')))
                    for comment in ET.fromstring(archive.read(comment_path)).findall('s:commentList/s:comment', NS):
                        comments[comment.get('ref')] = text_content(comment)
            cells = {}
            for cell in root.findall('s:sheetData/s:row/s:c', NS):
                value = cell.find('s:v', NS)
                raw_value = value.text if value is not None and value.text is not None else ''
                if cell.get('t') == 's':
                    raw_value = strings[int(raw_value)]
                elif cell.get('t') == 'inlineStr':
                    raw_value = text_content(cell.find('s:is', NS))
                cells[cell.get('r')] = {'value': raw_value, 'color': cell_styles[int(cell.get('s', 0))],
                                       'numeric': cell.get('t') not in ('s', 'inlineStr', 'str', 'b', 'e') and raw_value != ''}
            rules = []
            for conditional in root.findall('s:conditionalFormatting', NS):
                for rule in conditional:
                    rules.append({'ranges': conditional.get('sqref'), 'boxes': range_boxes(conditional.get('sqref')), 'type': rule.get('type'),
                                  'operator': rule.get('operator'), 'priority': int(rule.get('priority')),
                                  'formulas': [x.text for x in rule.findall('s:formula', NS)],
                                  'text': rule.get('text'), 'color': dxfs[int(rule.get('dxfId'))] if rule.get('dxfId') else None})
            result[title] = {'cells': cells, 'links': links, 'comments': comments,
                             'rules': sorted(rules, key=lambda x: x['priority']),
                             'hidden': sheet.get('state') == 'hidden'}
        if set(result) != set(TABS):
            fail('Required House/Senate tabs are missing or renamed')
        return result
    except (KeyError, IndexError, ET.ParseError, zipfile.BadZipFile) as exc:
        fail(f'Malformed workbook: {type(exc).__name__}')


class ChipParser(HTMLParser):
    """Read the static Google grid without trusting scripts or embedded instructions."""
    def __init__(self, gid):
        super().__init__(convert_charrefs=True)
        self.gid, self.row, self.column, self.cell = str(gid), None, 0, None
        self.cells = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr':
            self.row, self.column = None, 0
        if tag == 'th':
            match = re.fullmatch(re.escape(self.gid) + r'R([0-9]+)', attrs.get('id', ''))
            if match:
                self.row = int(match[1]) + 1
        if tag == 'td' and self.row is not None:
            if 'freezebar-cell' in attrs.get('class', '').split():
                return
            self.column += 1
            self.cell = {'ref': col_name(self.column) + str(self.row), 'text': '', 'colors': set()}
            self.column += int(attrs.get('colspan', '1')) - 1
        if self.cell is not None:
            for found in re.findall(r'background-color\s*:\s*(#[0-9a-fA-F]{6})', attrs.get('style', '')):
                self.cell['colors'].add(found.lower())

    def handle_data(self, data):
        if self.cell is not None:
            self.cell['text'] += data

    def handle_endtag(self, tag):
        if tag == 'td' and self.cell is not None:
            self.cells[self.cell['ref']] = self.cell
            self.cell = None


def normalized(value):
    return re.sub(r'\s+', ' ', value.replace('\u200b', '').replace('\xa0', ' ')).strip()


def effective_color(sheet, ref):
    cell = sheet['cells'].get(ref, {'value': '', 'color': None, 'numeric': False})
    column, row = coordinates(ref)
    for rule in sheet['rules']:
        if not in_boxes(column, row, rule.get('boxes') or range_boxes(rule['ranges'])):
            continue
        # Spreadsheet color scales do not color textual votes. Numeric action
        # values require review instead of an approximate gradient calculation.
        if rule['type'] == 'colorScale':
            if cell['numeric']:
                fail(f'Numeric action cell {ref} needs color-scale review')
            continue
        matched = False
        if rule['type'] == 'cellIs' and rule['operator'] == 'equal' and len(rule['formulas']) == 1:
            formula = rule['formulas'][0]
            if not (formula.startswith('"') and formula.endswith('"')):
                fail(f'Unsupported conditional formula at {ref}')
            matched = cell['value'].casefold() == formula[1:-1].replace('""', '"').casefold()
        elif rule['type'] == 'containsText':
            matched = (rule['text'] or '').casefold() in cell['value'].casefold()
        else:
            fail(f'Unsupported conditional formatting at {ref}: {rule["type"]}')
        if matched and rule['color']:
            return rule['color'], 'sheet_conditional_format'
    return cell['color'], 'sheet_fill' if cell['color'] else 'none'


def kind_for(title, column):
    if title == '119th House':
        return 'sponsorship' if column <= 15 else 'committee_vote' if column in (24, 25) else 'statement' if column == 72 else 'letter' if column in (71, 73) else 'roll_call_vote'
    if title == '119th Senate':
        return 'sponsorship' if column <= 11 else 'roll_call_vote'
    if title == '118th House':
        return 'sponsorship' if column <= 14 else 'petition_signature' if column == 15 else 'statement' if column == 56 else 'letter' if column == 57 else 'roll_call_vote'
    return 'roll_call_vote'


def disposition(title, column):
    config = TABS[title]
    if config['start'] <= column <= config['end']:
        return 'tracked_action'
    if title.startswith('119th') and column == 1:
        return 'ignored_source_grade'
    if column in (config['first'], config['last'], config['location']):
        return 'member_identity'
    return 'excluded_metadata_score_funding_endorsement_or_summary'


def date_label(cell):
    if cell['numeric']:
        try:
            value = float(cell['value'])
            if value.is_integer() and 35000 <= value <= 70000:
                return (dt.date(1899, 12, 30) + dt.timedelta(days=int(value))).isoformat()
        except (ValueError, OverflowError):
            pass
        fail('Unrecognized numeric action date')
    return cell['value'].strip()


def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()).strip('-')


def capture(raw, htmls, checked_on, baseline=None, accept_layout=False):
    if dt.date.fromisoformat(checked_on).isoformat() != checked_on:
        fail('checked_on must be a calendar date')
    if dt.date.fromisoformat(checked_on) > dt.datetime.now(dt.timezone.utc).date():
        fail('checked_on cannot be in the future')
    parsed = parse_xlsx(raw)
    actions, records, sheets, color_sources = {}, [], [], []
    seen = set()
    for title, config in TABS.items():
        sheet = parsed[title]
        sheet_url = SOURCE_URL + '?gid=' + str(config['gid']) + '#gid=' + str(config['gid'])
        prefix = f'{config["congress"]}-{config["chamber"].lower()}'
        chips = {}
        if title.startswith('119th'):
            if title not in htmls:
                fail(f'{title}: rendered HTML is required to preserve dropdown colors')
            parser = ChipParser(config['gid'])
            parser.feed(htmls[title].decode('utf-8'))
            chips = parser.cells
            rendered_end = 70 if title == '119th House' else config['end']
            if not chips or f'{col_name(rendered_end)}{config["rows"]}' not in chips:
                fail(f'{title}: incomplete HTML grid; use htmlview/sheet, not the first 100 rows of edit HTML')
            color_sources.append({'sheet_title': title, 'url': html_url(config['gid']),
                                  'sha256': hashlib.sha256(htmls[title]).hexdigest(), 'bytes': len(htmls[title])})
        columns = []
        for column in range(1, config['columns'] + 1):
            letter = col_name(column)
            headers = []
            for row in range(1, config['header_rows'] + 1):
                ref = letter + str(row)
                cell = sheet['cells'].get(ref, {'value': '', 'numeric': False})
                header = {'cell': ref, 'value': cell['value']}
                if ref in sheet['links']:
                    header['url'] = sheet['links'][ref]
                if ref in sheet['comments']:
                    header['note'] = sheet['comments'][ref]
                headers.append(header)
            columns.append({'column': letter, 'disposition': disposition(title, column), 'headers': headers})
            if disposition(title, column) != 'tracked_action':
                continue
            action_title = sheet['cells'].get(letter + '1', {}).get('value', '').strip()
            if not action_title:
                fail(f'{title} {letter}: tracked action has no title')
            action = {'title': action_title, 'kind': kind_for(title, column), 'congress': config['congress'],
                      'chamber': config['chamber'], 'sheet_title': title, 'sheet_column': letter,
                      'sheet_url': sheet_url + '&range=' + letter + '1'}
            label = date_label(sheet['cells'].get(letter + ('3' if config['header_rows'] == 4 else '2'), {'value': '', 'numeric': False}))
            if label:
                action['date_label'] = label
            urls = [x['url'] for x in headers if x.get('url')]
            if urls:
                action['source_url'] = urls[0]
            notes = [x['note'] for x in headers if x.get('note')]
            if notes:
                action['notes'] = notes
            actions[prefix + '-' + letter] = action
        for row in range(config['header_rows'] + 1, config['rows'] + 1):
            first = normalized(sheet['cells'].get(col_name(config['first']) + str(row), {}).get('value', ''))
            last = normalized(sheet['cells'].get(col_name(config['last']) + str(row), {}).get('value', ''))
            if not first or not last:
                fail(f'{title} row {row}: missing member identity; source may have changed')
            member_name = first + ' ' + last
            record_id = prefix + '-' + slug(member_name)
            if record_id in seen:
                fail(f'Ambiguous member identity: {member_name}')
            seen.add(record_id)
            location = normalized(sheet['cells'].get(col_name(config['location']) + str(row), {}).get('value', ''))
            record = {'record_id': record_id, 'member_name': member_name, 'chamber': config['chamber'],
                      'congress': config['congress'], 'source_url': sheet_url + '&range=A' + str(row),
                      'sheet_title': title, 'sheet_row': row, 'checked_on': checked_on, 'actions': []}
            if config['chamber'] == 'House':
                if not re.fullmatch(r'[A-Z]{2}-(?:[0-9]{2}|AL)', location):
                    fail(f'{title} row {row}: invalid congressional district {location!r}')
                record.update(district=location, state=location[:2])
            elif location:
                record['state'] = location
            for column in range(config['start'], config['end'] + 1):
                ref = col_name(column) + str(row)
                cell = sheet['cells'].get(ref, {'value': '', 'numeric': False})
                value = cell['value']
                fill, basis = effective_color(sheet, ref)
                # The source hides House BS:BU (letters/statements) in HTML;
                # those cells retain XLSX fills, rather than dropdown chips.
                if title.startswith('119th') and not (title == '119th House' and column > 70):
                    html_cell = chips.get(ref)
                    if html_cell is None or normalized(html_cell['text']) != normalized(value):
                        fail(f'{title} {ref}: HTML/XLSX values differ; retry a coherent snapshot')
                    colors = html_cell['colors']
                    if len(colors) > 1:
                        fail(f'{title} {ref}: ambiguous chip colors')
                    if colors:
                        fill, basis = next(iter(colors)), 'sheet_dropdown'
                assessment = PALETTE.get(fill, 'unclassified')
                # Blank cells retain their source fill but never imply a favorable position.
                if not normalized(value):
                    assessment = 'unclassified'
                elif fill is None and '(correct)' in value:
                    assessment, basis = 'positive', 'explicit_label'
                elif fill is None and '(incorrect)' in value:
                    assessment, basis = 'negative', 'explicit_label'
                item = {'action_id': prefix + '-' + col_name(column), 'value': value,
                        'assessment': assessment, 'sheet_color': fill, 'assessment_basis': basis}
                if ref in sheet['comments']:
                    item['note'] = sheet['comments'][ref]
                if ref in sheet['links']:
                    item['source_url'] = sheet['links'][ref]
                record['actions'].append(item)
            records.append(record)
        sheets.append({'title': title, 'gid': config['gid'], 'hidden': sheet['hidden'],
                       'rows': config['rows'], 'columns': columns, 'header_rows': config['header_rows'],
                       'member_count': config['rows'] - config['header_rows'],
                       'action_count': config['end'] - config['start'] + 1})
        # Every nonempty out-of-contract cell is a drift signal, never silently discarded.
        for ref, cell in sheet['cells'].items():
            column, row = coordinates(ref)
            if normalized(cell['value']) and (column > config['columns'] or row > config['rows']):
                fail(f'{title} extends beyond reviewed dimensions at {ref}; update the adapter after review')
    # Compare meaningful header labels/links, excluding mutable summary row percentages.
    layout = [{**{k: x[k] for k in ('title', 'gid', 'header_rows')},
               'columns': [{'column': c['column'], 'disposition': c['disposition'],
                            'headers': c['headers'][:3 if x['header_rows'] == 4 else 2]} for c in x['columns']]} for x in sheets]
    layout_hash = hashlib.sha256(json.dumps(layout, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    if baseline and baseline.get('layout_sha256') != layout_hash and not accept_layout:
        fail('Spreadsheet header/layout drift: review all column dispositions, then explicitly --accept-layout')
    return {'format': 'gaza-legislative-tracker/v1', 'checked_on': checked_on,
            'provider': 'Congressional Democrat Palestine Tracker', 'source_url': SOURCE_URL,
            'scope_note': SCOPE_NOTE, 'source': {'url': EXPORT_URL, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)},
            'color_sources': color_sources, 'layout_sha256': layout_hash, 'sheets': sheets,
            'counts': {'members': len(records), 'actions': len(actions), 'member_action_cells': sum(len(x['actions']) for x in records)},
            'actions': actions, 'records': records}


def html_url(gid):
    return f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/htmlview/sheet?headers=true&gid={gid}'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'BayAreaElectionResearch/1.0'})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read(20_000_001)
        if len(raw) > 20_000_000 or response.geturl().startswith('https://accounts.google.com/'):
            fail('Source is oversized or requires sign-in')
        return raw


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def protect_output(args):
    """A research export must not replace maintained product files or its inputs."""
    output = args.output.resolve()
    protected = {ROOT / name for name in ('2026-11-03_Bay_Area_Elections.json', 'elections.schema.json', 'index.html', 'ballot.html')}
    inputs = []
    for name in ('data', 'snapshot', 'links', 'baseline', 'xlsx'):
        path = getattr(args, name, None)
        if path is not None:
            inputs.append(path.resolve())
    html_dir = getattr(args, 'html_dir', None)
    if html_dir is not None:
        inputs.extend((html_dir / (title.replace(' ', '-') + '.html')).resolve() for title in TABS if title.startswith('119th'))
    if output in {p.resolve() for p in protected} or (ROOT / 'src').resolve() in output.parents or output in inputs:
        fail('Output may not replace maintained data/schema/pages/src or any capture/preview input')
    # Source snapshots currently pinned by the product are immutable publication
    # inputs too, even when a newer custom --baseline is supplied.
    try:
        published = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())
    except (OSError, ValueError):
        published = {}
    for field in ('gaza_voting', 'uscpr_scorecard'):
        path = (published.get(field) or {}).get('snapshot_path')
        if isinstance(path, str) and output == (ROOT / path).resolve():
            fail('Output may not replace a published pinned source snapshot; choose a new dated path')


def preview(data, snapshot, links):
    if snapshot.get('format') != 'gaza-legislative-tracker/v1' or links.get('format') != 'gaza-legislative-candidate-links/v1':
        fail('Unsupported snapshot or identity-link format')
    candidates = {(p['id'], c['name']): c for p in data['positions'] for c in p.get('candidates') or []}
    records = {}
    for record in snapshot['records']:
        key = record['sheet_title'], record['member_name']
        if key in records:
            fail('Ambiguous source member')
        records[key] = record
    updates, seen = [], set()
    for link in links['links']:
        key = link['position_id'], link['candidate_name']
        if key in seen or key not in candidates or not link.get('identity_sources') or not link.get('reviewed_on') or not link.get('matches'):
            fail(f'Unreviewed, duplicate or stale candidate identity link: {key}')
        try:
            dt.date.fromisoformat(link['reviewed_on'])
        except (TypeError, ValueError):
            fail(f'Invalid identity review date: {key}')
        if any(not source.get('url', '').startswith('https://') for source in link['identity_sources']):
            fail(f'Identity link lacks a primary source URL: {key}')
        seen.add(key)
        attached, matched = [], set()
        for match in link['matches']:
            source_key = match['sheet_title'], match['member_name']
            if source_key in matched:
                fail(f'Ambiguous duplicate member match: {key}')
            matched.add(source_key)
            record = records.get(source_key)
            if record is None or record.get('district') != match.get('district'):
                fail(f'Source identity/location mismatch: {key}')
            attached.append(copy.deepcopy(record))
        updates.append({'position_id': key[0], 'candidate_name': key[1],
                        'before': candidates[key].get('gaza_voting_records'), 'after': attached})
    shared = {key: copy.deepcopy(snapshot[key]) for key in ('provider', 'checked_on', 'source_url', 'scope_note', 'actions')}
    return {'format': 'gaza-legislative-candidate-preview/v1', 'checked_on': snapshot['checked_on'],
            'snapshot_source_sha256': snapshot['source']['sha256'], 'gaza_voting': shared, 'candidate_updates': updates,
            'limits': links.get('unmatched_prior_service', [])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    capture_parser = subs.add_parser('capture', help='Capture all four tabs atomically; no election-data writes')
    capture_parser.add_argument('--xlsx', type=Path, help='Offline workbook export; otherwise fetch public source')
    capture_parser.add_argument('--html-dir', type=Path, help='Offline 119th-House.html and 119th-Senate.html color captures')
    capture_parser.add_argument('--checked-on', required=True, help='Actual source retrieval date in the maintainer’s timezone')
    capture_parser.add_argument('--output', type=Path, required=True)
    capture_parser.add_argument('--baseline', type=Path, default=ROOT / 'research/gaza-records/voting-records-2026-10-14.json')
    capture_parser.add_argument('--accept-layout', action='store_true', help='Only after manually reviewing new headers/dispositions')
    preview_parser = subs.add_parser('preview', help='Resolve reviewed links and export a publication preview')
    preview_parser.add_argument('--data', type=Path, default=ROOT / '2026-11-03_Bay_Area_Elections.json')
    preview_parser.add_argument('--snapshot', type=Path, default=ROOT / 'research/gaza-records/voting-records-2026-10-14.json')
    preview_parser.add_argument('--links', type=Path, default=ROOT / 'research/gaza-records/candidate-links.json')
    preview_parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        protect_output(args)
        if args.command == 'capture':
            raw = args.xlsx.read_bytes() if args.xlsx else fetch(EXPORT_URL)
            htmls = {title: (args.html_dir / (title.replace(' ', '-') + '.html')).read_bytes() if args.html_dir else fetch(html_url(config['gid']))
                     for title, config in TABS.items() if title.startswith('119th')}
            baseline = json.loads(args.baseline.read_text()) if args.baseline.exists() else None
            if baseline is None and not args.accept_layout:
                fail('First capture needs reviewed layout acceptance (--accept-layout)')
            result = capture(raw, htmls, args.checked_on, baseline, args.accept_layout)
        else:
            result = preview(*(json.loads(path.read_text()) for path in (args.data, args.snapshot, args.links)))
        atomic_json(args.output, result)
        print(json.dumps(result.get('counts') or {'candidate_updates': len(result['candidate_updates'])}))
    except (ValueError, OSError, zipfile.BadZipFile, UnicodeError) as exc:
        parser.exit(1, f'Capture/preview refused; existing output preserved: {exc}\n')


if __name__ == '__main__':
    main()
