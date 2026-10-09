"""Conservative, source-local extraction for the endorsement research collector.

No model calls. Search snippets, logo guesses, name-only identity matches, and
footer years never establish an endorsement. Ambiguities go to a source packet.
"""
import hashlib
from html.parser import HTMLParser
import re
import unicodedata
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

VERSION = 'endorsements-2'


def invalid_endorser_name(name):
    """Reject UI text/category labels without guessing an actual endorser."""
    return bool(re.search(
        r'\bcookies?\b|privacy policy|terms of (?:use|service)|all rights reserved|'
        r'^(?:\d+\s+)?leaders of (?:the )?community$|'
        r'^(?:our |local )?(?:elected officials|community leaders|organizations|supporters|endorsements)$',
        name.strip(' *'), re.I))


def norm(text):
    text = unicodedata.normalize('NFKD', text)
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in text if not unicodedata.combining(c)).lower()).split())


def uid(prefix, *parts):
    return prefix + hashlib.sha256('\x1f'.join(map(str, parts)).encode()).hexdigest()[:20]


def clean_url(url):
    p = urlsplit(url.strip())
    if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password:
        raise ValueError('Expected a public HTTP(S) URL without credentials')
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in {'fbclid', 'gclid'}]
    # Preserve path case, query values, and non-tracking arguments.
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', urlencode(query), ''))


class PageParser(HTMLParser):
    """Keep headings, list nesting, tables, and link labels without executing JS."""
    SKIP = {'script', 'style', 'nav', 'footer', 'form', 'noscript', 'svg'}
    BLOCK = {'p', 'div', 'section', 'article', 'main', 'li', 'tr', 'blockquote'}

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.lines = []
        self.links = []
        self.images = []
        self.buf = []
        self.prefix = ''
        self.depth = 0
        self.skip = []
        self.anchor = None
        self.title = ''
        self.in_title = False

    def flush(self):
        text = re.sub(r'\s+', ' ', ''.join(self.buf)).strip()
        if text:
            self.lines.append(self.prefix + text)
        self.buf = []
        self.prefix = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        # Navigation text is excluded from evidence, but its real links are
        # useful for finding a campaign's endorsements page.
        if tag == 'a' and attrs.get('href'):
            self.anchor = [urljoin(self.base, attrs['href']), []]
        if self.skip:
            if tag in self.SKIP:
                self.skip.append(tag)
            return
        if tag in self.SKIP:
            self.flush(); self.skip.append(tag); return
        if tag == 'title':
            self.in_title = True; return
        if tag == 'img':
            alt = attrs.get('alt', '').strip()
            if alt:
                self.images.append(alt)
            return
        if tag in {'ul', 'ol'}:
            self.flush(); self.depth += 1
        elif re.fullmatch(r'h[1-6]', tag):
            self.flush(); self.prefix = '#' * int(tag[1]) + ' '
        elif tag in self.BLOCK:
            self.flush()
            if tag == 'li':
                self.prefix = '  ' * max(0, self.depth - 1) + '- '
        elif tag == 'br':
            self.flush()
        elif tag in {'td', 'th'} and self.buf:
            self.buf.append(' | ')

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor:
            url, pieces = self.anchor
            try:
                self.links.append({'url': clean_url(url), 'text': ''.join(pieces).strip()})
            except ValueError:
                pass
            self.anchor = None
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
            return
        if tag == 'title':
            self.in_title = False; return
        if tag in {'ul', 'ol'}:
            self.flush(); self.depth = max(0, self.depth - 1)
        elif tag in self.BLOCK or re.fullmatch(r'h[1-6]', tag):
            self.flush()

    def handle_data(self, text):
        if self.anchor:
            self.anchor[1].append(text)
        if self.skip:
            return
        if self.in_title:
            self.title += text; return
        self.buf.append(text)


def page_from_html(html, url):
    parser = PageParser(url)
    parser.feed(html); parser.flush()
    return {'text': '\n'.join(parser.lines), 'title': parser.title.strip(),
            'links': parser.links, 'image_labels': parser.images}


def candidates_from_data(data):
    rows = {}
    for p in data['positions']:
        for c in p.get('candidates') or []:
            ident = uid('C-', p['id'], norm(c['name']))
            if ident in rows:
                raise ValueError('Duplicate candidacy in dataset: ' + ident)
            rows[ident] = {'id': ident, 'position_id': p['id'], 'name': c['name'],
                           'office': p['office'], 'jurisdiction': p['jurisdiction'],
                           'seat': p['district_or_seat'], 'counties': p['counties'],
                           'term': p.get('term', ''), 'election_type': p.get('election_type', ''),
                           'campaign_url': c.get('campaign_url'), 'aliases': []}
    return rows


def contains_name(text, candidate):
    haystack = ' ' + norm(text) + ' '
    return any(' ' + norm(name) + ' ' in haystack for name in [candidate['name'], *candidate.get('aliases', [])])


def office_matches(candidate, context):
    s = norm(context)
    seat = candidate['seat']
    legislative = re.fullmatch(r'(CD|AD|SD)-(\d+)', seat)
    if legislative:
        prefix, n = legislative.groups()
        body = {'CD': r'congress|united states house|u s house',
                'AD': r'assembly', 'SD': r'state senate|senate district'}[prefix]
        return bool(re.search(body, s) and
                    (re.search(r'\b(?:district|dist|cd|ad|sd)\s*0*'+n+r'\b', s)
                     or re.search(r'\b0*'+n+r'(?:th|st|nd|rd)?\s+(?:congressional|assembly|senate)', s)))
    office = norm(candidate['office'])
    if candidate['jurisdiction'] == 'California':
        if office == 'governor':
            return bool(re.search(r'\bgovernor\b', s) and not re.search(r'lieutenant|lt governor', s))
        aliases = {'lieutenant governor': ('lieutenant governor', 'lt governor'),
                   'controller': ('controller',), 'treasurer': ('treasurer',),
                   'superintendent of public instruction': ('superintendent of public instruction', 'state superintendent')}
        return any(x in s for x in aliases.get(office, (office,)))
    jurisdiction = norm(candidate['jurisdiction'])
    jurisdiction = re.sub(r'^(city and county of|city of|town of|county of) ', '', jurisdiction)
    def expand_school(value):
        for short, full in (('uhsd', 'high school district'), ('usd', 'school district'),
                            ('sd', 'school district'), ('ccd', 'community college district'), ('boe', 'board of education')):
            value = re.sub(r'\b'+short+r'\b', full, value)
        return re.sub(r'\b(?:union|unified)\s+(?=(?:high )?school district)', '', value)
    if expand_school(jurisdiction) not in expand_school(s):
        return False
    for marker in ('mayor', 'council', 'supervisor', 'assessor', 'auditor', 'sheriff', 'treasurer',
                   'coroner', 'recorder', 'clerk', 'district attorney', 'public defender', 'superintendent', 'judge', 'justice'):
        if marker in office and marker not in s:
            return False
    if 'council' in office and 'mayor' in s:
        return False
    if re.search(r'board|trustee', office) and not re.search(r'board|trustee|school district|college district', expand_school(s)):
        return False
    number = re.search(r'(?:District|Area|Ward|Seat|Office)\s*(\d+|[A-Z])\b', seat, re.I)
    if number and not re.search(r'\b(?:district|area|ward|seat|office)\s*0*'+number[1].lower()+r'\b', s):
        return False
    partial = r'partial|short term|unexpired'
    if bool(re.search(partial, norm(seat+' '+(candidate.get('term') or '')))) != bool(re.search(partial, s)):
        return False
    return True


def contexts(text):
    """Yield source lines with section/list ancestry and local election markers."""
    headings, parents = [], []
    cycle, phase, cycle_quote, endorsement_section = None, 'unspecified', '', False
    endorsement_level = None
    paragraph_blocked = False
    lines = text.splitlines()
    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line or re.search(r'^(?:copyright|©|paid for by)', line, re.I):
            continue
        item = re.match(r'^(\s*)[-*]\s+(.+)', raw)
        h = re.match(r'^(#{1,6})\s+(.+)', item[2] if item else line)
        if h:
            level = len(h[1])
            if endorsement_level is not None and level <= endorsement_level:
                endorsement_section = False
                endorsement_level = None
            headings = [(n, s) for n, s in headings if n < level]
            parents = []
            label = h[2]
            paragraph_blocked = False
        else:
            label = item[2] if item else line
        # Only election/campaign markers, never a copyright, navigation URL or
        # arbitrary recent article date, establish the cycle.
        marker = re.search(r'\b(20\d{2})\b', label)
        scope_marker = bool(h) or bool(re.match(r'^(?:☑\s*)?(?:(?:general|primary|special) election|(?:june|november|nov\b)\s|election endorsements|20\d\d\s+endorsements)', label, re.I))
        if marker and scope_marker and len(label) < 220 and re.search(r'endorse|election|primary|general|campaign|for (?:congress|governor|council)', label, re.I):
            cycle = int(marker[1]); cycle_quote = label
            primary = bool(re.search(r'primary|june\b', label, re.I))
            general = bool(re.search(r'general|nov(?:ember)?\b', label, re.I))
            phase = 'unspecified' if primary == general else 'primary' if primary else 'general'
        negative_section = r'questionnaire|forum|process|seeking|interview|ballot measures|resources|volunteer|donate'
        if not h and not item and len(label) < 250 and re.search(r'questionnaires|candidate forum|endorsement process', label, re.I):
            paragraph_blocked = True
        if re.search(r'endorsements?\b|endorsed candidates', label, re.I) and len(label) < 160 and not re.search(negative_section, label, re.I):
            endorsement_section = True
            endorsement_level = len(h[1]) if h else (headings[-1][0] if headings else 0)
        if item:
            depth = len(item[1])
            parents = [(n, s) for n, s in parents if n < depth]
        else:
            parents = []
        context = [s for _, s in headings] + [s for _, s in parents] + [label]
        # Candidate cards sometimes put the office just below the name.
        if h:
            for following in lines[index+1:index+4]:
                if following.lstrip().startswith('#'):
                    break
                if following.strip():
                    context.append(following.strip())
        yield {'line': index+1, 'text': label, 'context': '\n'.join(context),
               'cycle': cycle, 'phase': phase, 'cycle_quote': cycle_quote,
               'endorsement_section': endorsement_section and not paragraph_blocked and not any(re.search(negative_section, x, re.I) for x in [s for _, s in headings] + ([label] if h else [])),
               'heading': len(h[1]) if h else None,
               'list_item': bool(item)}
        if h:
            headings.append((len(h[1]), label))
        if item:
            parents.append((len(item[1]), label))


def qualifier(line, name):
    pieces = re.split(r'[|;]', line)
    segment = next((p for p in pieces if norm(name) in norm(p)), line)
    rank = re.search(r'#\s*([1-9])\b', segment)
    result = {}
    if rank:
        result['rank'] = int(rank[1])
    if re.search(r'\bdual\b|co.endorse|\bslate\b', line, re.I):
        result['shared'] = True
    return result


def extract(page, meta, candidates, year):
    records, issues = [], []
    role = meta.get('role', 'unverified')
    # Neutral guides are discovery sources; mentioning every candidate is not
    # an endorsement. Aggregators still create review issues, never own-publisher
    # endorsements. A vetted voter guide with no endorsement heading requires
    # manual review instead of trusting its title alone.
    if role == 'discovery':
        return [], []
    text = page['text']
    source_candidates = list(candidates.values())
    if role == 'campaign':
        source_candidates = [candidates[x] for x in meta.get('candidate_ids', []) if x in candidates]
    name_index = [(c, [' '+norm(n)+' ' for n in [c['name'], *c.get('aliases', [])]]) for c in source_candidates]
    matched_ids = set()
    for row in contexts(text):
        line, context = row['text'], row['context']
        if role == 'campaign':
            if not row['endorsement_section'] or not (row['list_item'] or row['heading'] in {3, 4, 5}):
                continue
            if len(line) > 140 or len(line.split()) < 2 or re.search(r'endorsement|\b(?:join|sign up|learn more|donate|volunteer|contact|click|thank|subscribe)\b|^elected officials|^community|^organizations|^labor$|^speaker |^former |^u\.?s\.? senator|^congress|^supervisor$|^mayor$|20\d\d.*(?:election|campaign)|(?:election|campaign).*20\d\d', line, re.I):
                continue
            if invalid_endorser_name(line):
                continue
            matches = [c for c in source_candidates if not contains_name(line, c)]
            endorser_name = line.strip(' *')
        else:
            normalized_line = ' '+norm(line)+' '
            matches = [c for c, names in name_index if any(n in normalized_line for n in names)]
            endorser_name = meta.get('publisher', '')
        if not matches:
            if role == 'endorser' and row['endorsement_section'] and row['cycle'] == year and len(line) < 180:
                words = set(norm(line).split())
                possible = [c for c in source_candidates if len(norm(c['name']).split()) >= 2
                            and {norm(c['name']).split()[0], norm(c['name']).split()[-1]} <= words
                            and office_matches(c, context)]
                if possible:
                    issues.append({'reasons': ['name_variant_requires_confirmed_alias'],
                                   'candidate_ids': [c['id'] for c in possible], 'quote': line, 'context': context})
            continue
        matched_ids.update(c['id'] for c in matches)
        if not row['endorsement_section']:
            continue
        for c in matches:
            reasons = []
            if role not in {'endorser', 'campaign'} or not endorser_name:
                reasons.append('publisher_or_source_role_unverified')
            if row['cycle'] != year:
                reasons.append('cycle_unproven' if row['cycle'] is None else 'different_election_cycle')
            race_context = context.rsplit('\n', 1)[0] if role == 'campaign' else context
            if not office_matches(c, race_context):
                reasons.append('office_or_district_not_established')
            if role == 'campaign' and not contains_name(context, c):
                reasons.append('campaign_candidate_not_identified_in_section')
            if role != 'campaign' and len(matches) > 1 and len({(m['name'], m['position_id']) for m in matches}) > len({m['name'] for m in matches}):
                reasons.append('same_name_multiple_races')
            nearby = line + '\n' + '\n'.join(re.sub(r'^\s*[-*]\s+', '', x) for x in text.splitlines()[row['line']:row['line']+2])
            if '*' in line or re.search(r'\bagainst\b|no endorsement|not endorse|no recommendation|withdraw|rescind|un.endors|recommendations.*positions', nearby, re.I):
                reasons.append('negative_withdrawal_or_qualified_claim')
            if meta.get('assertion') == 'mixed':
                reasons.append('mixed_endorsements_and_recommendations')
            relation = 'recommended' if meta.get('assertion') == 'recommendations' else 'endorsed'
            evidence = {'quote': line, 'context': context, 'cycle_quote': row['cycle_quote'], 'line': row['line']}
            item = {'candidate_id': c['id'], 'endorser': endorser_name, 'relation': relation,
                    'phase': row['phase'], 'cycle': row['cycle'], 'evidence': evidence,
                    'verification': 'campaign_claim' if role == 'campaign' else 'endorser_statement',
                    **qualifier(context, c['name'])}
            if role == 'campaign':
                item['endorser_kind'] = 'unspecified'
                if re.search(r'titles? (?:are )?for identification|individual capacity|personal capacity', text, re.I):
                    item['titles_for_identification_only'] = True
            else:
                item['endorser_kind'] = meta.get('kind', 'organization')
            if reasons:
                issues.append({'candidate_id': c['id'], 'reasons': reasons, 'proposal': item})
            else:
                records.append(item)
    has_endorsement_body = any(r['endorsement_section'] for r in contexts(text))
    if page.get('image_labels') and role == 'campaign' and has_endorsement_body:
        issues.append({'reasons': ['image_labels_need_confirmation'], 'image_labels': page['image_labels'][:100],
                       'candidate_ids': [c['id'] for c in source_candidates]})
    # No match is an explicit coverage gap, never evidence of no endorsements.
    if not records and not issues:
        if role == 'campaign' and not has_endorsement_body and any(re.search(r'endors', x.get('url', '')+' '+x.get('text', ''), re.I) for x in page.get('links', [])):
            return [], []
        issues.append({'reasons': ['no_unambiguous_extractable_endorsements'],
                       'candidate_ids': sorted(matched_ids or set(meta.get('candidate_ids', [])))})
    return records, issues
