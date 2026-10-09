"""Parse CAIR's captured recommendation cards; apply explicitly reviewed matches.

No network, model calls, fuzzy identity matching, or automatic roster additions.
Raw HTML stays outside Git. Every captured card needs a review disposition.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = 'https://cairactionguide.org/explore'
REVIEW = ROOT / 'research/endorsements/cair-action-2026-10-09.json'
DATA = ROOT / '2026-11-03_Bay_Area_Elections.json'
LEVELS = {'Endorsed': 'endorsed', 'Preferred': 'preferred', 'Oppose': 'opposed',
          'Opposed': 'opposed', 'Joint Endorsement': 'endorsed'}


class CaptureParser(HTMLParser):
    VOID = {'img', 'br', 'hr', 'meta', 'link', 'input', 'source', 'area', 'wbr', 'embed', 'param', 'track', 'col', 'base'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {'tag': 'root', 'attrs': {}, 'children': []}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = {'tag': tag, 'attrs': dict(attrs), 'children': []}
        self.stack[-1]['children'].append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index]['tag'] == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        self.stack[-1]['children'].append(data)


def text(node):
    return ' '.join(' '.join(x if isinstance(x, str) else text(x) for x in node['children']).split())


def nodes(node):
    yield node
    for child in node['children']:
        if isinstance(child, dict):
            yield from nodes(child)


def parse_capture(raw, checked_on):
    date.fromisoformat(checked_on)
    parser = CaptureParser()
    parser.feed(raw.decode('utf-8'))
    section, cards, ids = '', [], set()
    for node in nodes(parser.root):
        if node['tag'] == 'span' and 'uppercase' in node['attrs'].get('class', '').split():
            section = text(node)
        ident = node['attrs'].get('data-testid', '')
        if not ident.startswith('card-endorsement-'):
            continue
        ident = ident.removeprefix('card-endorsement-')
        children = list(nodes(node))
        names = [text(n) for n in children if n['attrs'].get('data-testid', '') == 'text-candidate-name-' + ident]
        levels = [text(n) for n in children if n['attrs'].get('data-testid', '').startswith('endorsement-level-')]
        paragraphs = [text(n) for n in children if n['tag'] == 'p']
        if ident in ids or not ident.isdigit() or len(names) != 1 or not names[0] or len(levels) != 1 or not paragraphs or not paragraphs[0]:
            raise ValueError('Duplicate, incomplete or ambiguous CAIR card: ' + ident)
        if levels[0] not in LEVELS:
            raise ValueError('Unrecognized recommendation level: ' + levels[0])
        ids.add(ident)
        cards.append({'id': ident, 'section': section, 'name': names[0], 'office': paragraphs[0],
                      'level': levels[0], 'annotations': paragraphs[1:]})
    if not cards:
        raise ValueError('No complete CAIR recommendation cards found')
    return {'source_url': URL, 'reviewed_on': checked_on, 'retrieval': 'user_supplied_html_capture',
            'capture_sha256': hashlib.sha256(raw).hexdigest(), 'capture_bytes': len(raw),
            'card_count': len(cards), 'level_counts': dict(Counter(c['level'] for c in cards)), 'cards': cards}


def recommendation(card, review):
    record = {'endorser': 'CAIR Action', 'kind': 'organization', 'relation': LEVELS[card['level']],
              'phase': review['phase'], 'url': review['source_url'], 'checked_on': review['reviewed_on'],
              'verification': 'endorser_statement', 'note_id': review['publication_note_id']}
    if card['level'] == 'Joint Endorsement':
        record['shared'] = True
    return record


def reviewed_records(data, review):
    """Require an explicit, internally consistent disposition for every card."""
    people = {(p['id'], c['name']): c for p in data['positions'] for c in p.get('candidates') or []}
    cards = {c['id']: c for c in review['cards']}
    if len(cards) != review['card_count'] or set(cards) != set(review['dispositions']):
        raise ValueError('Every captured card must have exactly one disposition')
    if review['source_url'] != URL or review['phase'] not in {'general', 'primary', 'unspecified'}:
        raise ValueError('Wrong source or invalid phase')
    if review['level_counts'] != dict(Counter(c['level'] for c in cards.values())):
        raise ValueError('Capture level counts disagree with cards')
    if 'disposition_counts' in review and review['disposition_counts'] != dict(Counter(d['action'] for d in review['dispositions'].values())):
        raise ValueError('Disposition counts disagree with review decisions')
    if 'published_level_counts' in review and review['published_level_counts'] != dict(Counter(cards[i]['level'] for i, d in review['dispositions'].items() if d['action'] == 'publish')):
        raise ValueError('Published level counts disagree with review decisions')
    result = {}
    for ident, disposition in review['dispositions'].items():
        action = disposition['action']
        if not disposition.get('reason'):
            raise ValueError('A disposition needs a reason: ' + ident)
        if action == 'publish':
            key = (disposition['position_id'], disposition['candidate'])
            if key not in people or key in result:
                raise ValueError('Missing candidacy or duplicate publication: ' + repr(key))
            result[key] = recommendation(cards[ident], review)
        elif action == 'duplicate':
            target = disposition['duplicate_of']
            other = review['dispositions'].get(target, {})
            if other.get('action') != 'publish' or cards[ident]['level'] != cards[target]['level']:
                raise ValueError('Invalid or conflicting duplicate: ' + ident)
            if (disposition['position_id'], disposition['candidate']) != (other['position_id'], other['candidate']):
                raise ValueError('Duplicate points to a different candidacy')
        elif action not in {'not_in_current_roster', 'held_office_mismatch'}:
            raise ValueError('Unknown disposition: ' + action)
    return result


def apply_capture(data, review):
    records = reviewed_records(data, review)
    note_id = review['publication_note_id']
    if note_id in data['notes'] and data['notes'][note_id] != review['publication_note']:
        raise ValueError('Note ID collision: ' + note_id)
    data['notes'][note_id] = review['publication_note']
    for p in data['positions']:
        for c in p.get('candidates') or []:
            current = [r for r in c.get('endorsements', []) if r['endorser'] == 'CAIR Action']
            if any(r['checked_on'] > review['reviewed_on'] for r in current):
                raise ValueError('Refusing to replace newer CAIR research')
            record = records.get((p['id'], c['name']))
            if current == ([record] if record else []):
                continue
            retained = [r for r in c.get('endorsements', []) if r['endorser'] != 'CAIR Action']
            if record:
                retained.append(record)
            if retained:
                c['endorsements'] = retained
            else:
                c.pop('endorsements', None)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    parse = sub.add_parser('parse')
    parse.add_argument('input', type=Path)
    parse.add_argument('--checked-on', required=True)
    parse.add_argument('--output', type=Path, required=True)
    sub.add_parser('apply')
    args = parser.parse_args()
    if args.command == 'parse':
        parsed = parse_capture(args.input.read_bytes(), args.checked_on)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k: v for k, v in parsed.items() if k != 'cards'}, indent=2))
    else:
        # Use the combined migration so coverage, prior quarantines and the CAIR
        # replacement remain consistent. It also performs publication checks.
        from apply_endorsement_review import apply_review, encode, EXPORT, REVIEW as PRIOR_REVIEW
        data, export = apply_review(json.loads(DATA.read_text()), json.loads(PRIOR_REVIEW.read_text()), json.loads(EXPORT.read_text()))
        DATA.write_text(encode(data))
        EXPORT.write_text(encode(export, indent=1))
        print('Applied reviewed CAIR recommendations and updated publication coverage.')
