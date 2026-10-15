#!/usr/bin/env python3
"""Offline parser, color, completeness and candidate-identity regressions."""
import copy
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

import gaza_voting_records as voting


def workbook_fixture():
    """All required rows/tabs, including hidden history; no live source dependency."""
    files = {}
    sheets, rels = [], []
    htmls = {}
    for index, (title, config) in enumerate(voting.TABS.items(), 1):
        sheets.append(f'<sheet name="{title}" sheetId="{index}" r:id="rId{index}" state="{"hidden" if config["congress"] == 118 else "visible"}"/>')
        rels.append(f'<Relationship Id="rId{index}" Target="worksheets/sheet{index}.xml"/>')
        rows, html_rows = [], []
        for row in range(1, config['rows'] + 1):
            cells, html_cells = [], []
            for column in range(1, config['columns'] + 1):
                value, fill = '', None
                if row == 1:
                    value = 'Action ' + voting.col_name(column)
                elif row > config['header_rows']:
                    if column == config['first']:
                        value = 'Test' + str(row)
                    elif column == config['last']:
                        value = 'Member'
                    elif column == config['location']:
                        value = 'CA-01' if config['chamber'] == 'House' else 'California'
                    elif config['start'] <= column <= config['end']:
                        offset = column - config['start']
                        value, fill = [('No', '#d4edbc'), ('Yes', '#ffcfc9'), ('', '#d4edbc'),
                                       ('0', '#ffcfc9'), ('N/A', None)][offset % 5]
                ref = voting.col_name(column) + str(row)
                cell = ET.Element('c', {'r': ref, 't': 'inlineStr'})
                inline = ET.SubElement(cell, 'is')
                ET.SubElement(inline, 't').text = value
                cells.append(ET.tostring(cell).decode())
                if column <= (70 if title == '119th House' else config['end']):
                    if fill:
                        html_cells.append(f'<td><span style="background-color:{fill}">{value}</span></td>')
                    else:
                        html_cells.append(f'<td>{value}</td>')
            rows.append(f'<row r="{row}">{"".join(cells)}</row>')
            html_rows.append(f'<tr><th id="{config["gid"]}R{row-1}">{row}</th>{"".join(html_cells)}</tr>')
        files[f'xl/worksheets/sheet{index}.xml'] = f'<worksheet xmlns="{voting.NS["s"]}"><sheetData>{"".join(rows)}</sheetData></worksheet>'
        if title.startswith('119th'):
            htmls[title] = ('<table>' + ''.join(html_rows) + '</table>').encode()
    files['xl/workbook.xml'] = f'<workbook xmlns="{voting.NS["s"]}" xmlns:r="{voting.NS["r"]}"><sheets>{"".join(sheets)}</sheets></workbook>'
    files['xl/_rels/workbook.xml.rels'] = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(rels) + '</Relationships>'
    files['xl/styles.xml'] = f'<styleSheet xmlns="{voting.NS["s"]}"><fills><fill><patternFill patternType="none"/></fill></fills><cellXfs><xf fillId="0"/></cellXfs><dxfs/></styleSheet>'
    files['xl/sharedStrings.xml'] = f'<sst xmlns="{voting.NS["s"]}"/>'
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    return output.getvalue(), htmls


class VotingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.htmls = workbook_fixture()
        cls.snapshot = voting.capture(cls.raw, cls.htmls, '2026-10-14', accept_layout=True)

    def test_entire_four_tab_capture_and_column_dispositions(self):
        self.assertEqual(self.snapshot['counts'], {'members': 523, 'actions': 150, 'member_action_cells': 25830})
        self.assertEqual({s['title'] for s in self.snapshot['sheets']}, set(voting.TABS))
        self.assertEqual(sum(len(s['columns']) for s in self.snapshot['sheets']), 253)
        self.assertTrue(all(c.get('disposition') for s in self.snapshot['sheets'] for c in s['columns']))
        self.assertEqual(self.snapshot['sheets'][0]['columns'][0]['disposition'], 'ignored_source_grade')
        self.assertTrue(self.snapshot['sheets'][2]['hidden'])
        self.assertFalse(any('grade' in record for record in self.snapshot['records']))

    def test_actual_dropdown_color_not_yes_no_assumption(self):
        a, b = self.snapshot['records'][0]['actions'][:2]
        self.assertEqual((a['value'], a['assessment'], a['sheet_color']), ('No', 'positive', '#d4edbc'))
        self.assertEqual((b['value'], b['assessment'], b['sheet_color']), ('Yes', 'negative', '#ffcfc9'))
        self.assertEqual(a['assessment_basis'], 'sheet_dropdown')

    def test_missing_zero_and_na_are_distinct(self):
        blank, zero, na = self.snapshot['records'][0]['actions'][2:5]
        self.assertEqual([x['value'] for x in (blank, zero, na)], ['', '0', 'N/A'])
        self.assertEqual(blank['assessment'], 'unclassified')
        self.assertEqual(na['assessment'], 'unclassified')

    def test_inverted_conditional_rules_and_priorities(self):
        rules = [{'ranges': 'G3:T53', 'type': 'cellIs', 'operator': 'equal', 'formulas': ['"Yes (correct)"'], 'color': '#00ff00'},
                 {'ranges': 'G3:T53', 'type': 'cellIs', 'operator': 'equal', 'formulas': ['"Yes"'], 'color': '#ff0000'},
                 {'ranges': 'G3:T53', 'type': 'cellIs', 'operator': 'equal', 'formulas': ['"No"'], 'color': '#00ff00'}]
        sheet = {'cells': {'G3': {'value': 'Yes (correct)', 'color': None, 'numeric': False},
                           'H3': {'value': 'Yes', 'color': None, 'numeric': False},
                           'I3': {'value': 'No', 'color': None, 'numeric': False}}, 'rules': rules}
        self.assertEqual([voting.effective_color(sheet, r)[0] for r in ('G3', 'H3', 'I3')], ['#00ff00', '#ff0000', '#00ff00'])

    def test_partial_or_stale_html_refused(self):
        partial = dict(self.htmls, **{'119th House': b'<html>Sign in</html>'})
        with self.assertRaisesRegex(ValueError, 'incomplete HTML'):
            voting.capture(self.raw, partial, '2026-10-14')
        stale = dict(self.htmls)
        stale['119th House'] = stale['119th House'].replace(b'>No</span>', b'>Stale</span>', 1)
        with self.assertRaisesRegex(ValueError, 'values differ'):
            voting.capture(self.raw, stale, '2026-10-14')

    def test_layout_drift_requires_explicit_review(self):
        with self.assertRaisesRegex(ValueError, 'layout drift'):
            voting.capture(self.raw, self.htmls, '2026-10-14', {'layout_sha256': 'different'})

    def test_malformed_workbook_cannot_overwrite_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'bad.xlsx').write_text('<html>Sign in</html>')
            for title, raw in self.htmls.items():
                (directory / (title.replace(' ', '-') + '.html')).write_bytes(raw)
            output = directory / 'output.json'
            output.write_text('preserve me')
            proc = subprocess.run([sys.executable, str(Path(voting.__file__)), 'capture', '--xlsx', str(directory / 'bad.xlsx'),
                                   '--html-dir', str(directory), '--checked-on', '2026-10-14', '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(output.read_text(), 'preserve me')

    def test_preview_output_cannot_replace_input_even_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data.json'
            data.write_text('preserve this input before attempting to parse it')
            proc = subprocess.run([sys.executable, str(Path(voting.__file__)), 'preview', '--data', str(data), '--output', str(data)],
                                  capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('Output may not replace', proc.stderr)
            self.assertEqual(data.read_text(), 'preserve this input before attempting to parse it')

    def binding(self):
        record = self.snapshot['records'][0]
        data = {'positions': [{'id': 'P1', 'candidates': [{'name': record['member_name']}]}]}
        links = {'format': 'gaza-legislative-candidate-links/v1', 'links': [
            {'position_id': 'P1', 'candidate_name': record['member_name'], 'reviewed_on': '2026-10-14',
             'identity_sources': [{'url': 'https://example.org/official-biography'}],
             'matches': [{'sheet_title': record['sheet_title'], 'member_name': record['member_name'], 'district': 'CA-01'}]}]}
        return data, links

    def test_candidate_binding_is_explicit_and_does_not_mutate(self):
        data, links = self.binding()
        original = copy.deepcopy(data)
        result = voting.preview(data, self.snapshot, links)
        self.assertEqual(data, original)
        self.assertEqual(len(result['candidate_updates']), 1)
        self.assertEqual(len(result['candidate_updates'][0]['after'][0]['actions']), 64)
        self.assertEqual(result, voting.preview(data, self.snapshot, links))

    def test_ambiguous_stale_or_unreviewed_identity_refused(self):
        data, links = self.binding()
        links['links'].append(copy.deepcopy(links['links'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            voting.preview(data, self.snapshot, links)
        links['links'].pop()
        links['links'][0]['matches'][0]['district'] = 'CA-99'
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            voting.preview(data, self.snapshot, links)
        links['links'][0]['matches'][0]['district'] = 'CA-01'
        links['links'][0]['identity_sources'] = []
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            voting.preview(data, self.snapshot, links)

    def test_published_snapshot_internal_completeness(self):
        snapshot = json.loads((voting.ROOT / 'research/gaza-records/voting-records-2026-10-14.json').read_text())
        self.assertEqual(snapshot['counts']['member_action_cells'], sum(len(r['actions']) for r in snapshot['records']))
        self.assertEqual(snapshot['counts']['members'], len(snapshot['records']))
        self.assertEqual(snapshot['counts']['actions'], len(snapshot['actions']))
        for record in snapshot['records']:
            self.assertEqual(len(record['actions']), voting.TABS[record['sheet_title']]['end'] - voting.TABS[record['sheet_title']]['start'] + 1)
            self.assertTrue(all(a['action_id'] in snapshot['actions'] for a in record['actions']))
        wahab = next(r for r in snapshot['records'] if r['member_name'] == 'Aisha Wahab')
        self.assertEqual(next(a for a in wahab['actions'] if a['action_id'] == '119-house-P')['value'], 'No')
        self.assertEqual(next(a for a in wahab['actions'] if a['action_id'] == '119-house-Q')['value'], 'Not elected')


if __name__ == '__main__':
    unittest.main()
