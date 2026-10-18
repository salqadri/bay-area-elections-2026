#!/usr/bin/env python3
"""Parse ONLY the 'Race summary' wikitable blocks from cached Wikipedia 2026
Senate + gubernatorial wikitext into a working inventory. RESEARCH LEAD only —
every roster must be corroborated against official state sources before publication.
"""
import json, re

def clean(s):
    s = re.sub(r'<ref[^>]*/>', '', s)
    s = re.sub(r'<ref.*?</ref>', '', s, flags=re.S)
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]+)\]\]', r'\1', s)
    s = re.sub(r"{{sortname\|([^|}]+)\|([^}]+)}}", r"\1 \2", s)
    s = re.sub(r'{{small\|([^}]*)}}', r'\1', s)
    s = re.sub(r'<br\s*/?>', ' ', s)
    return s.strip()

PARTY_RE = re.compile(r'\{\{Party stripe\|([^}]+)\}\}')

def norm_party(p_raw, paren):
    s = (p_raw + ' ' + paren).lower()
    if 'democrat' in s: return 'D'
    if 'republican' in s: return 'R'
    if 'independent' in s or s.strip().startswith(('i',) ) and 'ind' in s: return 'I'
    if 'libertarian' in s: return 'L'
    if 'green' in s: return 'G'
    if 'constitution' in s: return 'C'
    if 'reform' in s: return 'RF'
    if 'socialist' in s or 'psl' in s or 'peace and freedom' in s: return 'SF'
    if 'no party' in s or 'npp' in s: return 'NPP'
    if 'legal marijuana' in s or 'marijuana' in s: return 'LM'
    if 'natural law' in s: return 'NL'
    if 'american independent' in s: return 'AI'
    if 'renewal' in s: return 'TR'
    if 'unaffiliated' in s: return 'I'
    # minor party not in the registry: keep a short uppercase label from the parenthetical
    label = re.sub(r'[^A-Za-z ]', '', (paren or p_raw)).strip()
    if label and len(label) <= 24:
        words = [w for w in label.split() if w.lower() not in ('party','of','the','america','united','states','us')]
        if words: return ''.join(w[0] for w in words).upper()[:6] or None
    return None

def parse_candidates(cell):
    out = []
    for line in cell.splitlines():
        line = line.strip()
        if not line.startswith('*'):
            continue
        m = PARTY_RE.search(line)
        party_raw = m.group(1).strip() if m else ''
        text = clean(PARTY_RE.sub('', line[1:]))
        par = re.search(r'\(([^)]+)\)', text)
        name = re.sub(r'\([^)]*\)', '', text, count=1).strip().rstrip(',').strip()
        out.append({'name': name, 'party_raw': party_raw,
                    'paren': par.group(1).strip() if par else '',
                    'party': norm_party(party_raw, (par.group(1) if par else ''))})
    return out

def find_tables(text):
    """yield full wikitext table blocks {| ... |}"""
    for m in re.finditer(r'^\{\|.*?^\|\}', text, flags=re.S | re.M):
        yield m.group(0)

SEN_LINK = re.compile(r'^!\s*\[\[2026 United States Senate (special )?election in ([^|\]]+)(?:\|([^\]]+))?\]\]', re.M)
GOV_LINK = re.compile(r'^!\s*\[\[2026 ([A-Za-z. ]+) gubernatorial election(?:\|([^\]]+))?\]\]', re.M)

def parse_table(block, kind):
    races = []
    for row in re.split(r'^\|\-.*$', block, flags=re.M):
        if kind == 'senate':
            m = SEN_LINK.search(row)
            if not m: continue
            state = clean(m.group(2))
            special = bool(m.group(1))
            office = 'United States Senator'
        else:
            m = GOV_LINK.search(row)
            if not m: continue
            state = clean(m.group(1))
            special = False
            office = 'Governor'
        inc_m = re.search(r'(?:\{\{Shading PVI\|[^}]*\}\}\s*)?\n\|\s*(?:\{\{sortname\|([^|}|]+)\|([^}|]+)|\[\[([^\]|]+)(?:\|[^\]]+)?\]\])', row)
        incumbent = None
        if inc_m:
            incumbent = (f"{inc_m.group(1)} {inc_m.group(2)}" if inc_m.group(1) else inc_m.group(3)).strip()
        cm = re.search(r'(?:nowrap[^|]*)?\|\s*\{\{[Pp]lainlist\s*\|?(.*)', row, flags=re.S)
        cands = parse_candidates(cm.group(1)) if cm else []
        status_m = re.search(r'(?:Interim appointee nominated|Interim appointee(?: [^|<]*)?|Incumbent (?:retiring[^|<]*|not seeking[^|<]*|running[^|<]*|lost renomination[^|<]*))', clean(row))
        refs = sorted(set(re.findall(r'https?://[^\s"\'|}\]]+', ' '.join(re.findall(r'<ref.*?</ref>|<ref[^>]*/>', row, flags=re.S)))))
        races.append({'state': state, 'office': office, 'special': special,
                      'incumbent': incumbent,
                      'status': status_m.group(0).strip() if status_m else '',
                      'refs': refs,
                      'candidates': cands})
    return races

def main():
    senate_text = open('senate_raw.wikitext').read()
    gov_text = open('gov_raw.wikitext').read()
    # Senate: only tables inside the Race summary section
    rs = senate_text[senate_text.index('== Race summary =='):]
    senate = []
    for t in find_tables(rs): senate += parse_table(t, 'senate')
    gov = []
    for t in find_tables(gov_text): gov += parse_table(t, 'gov')

    def dedupe(races):
        seen = {}
        for r in races:
            key = (r['state'], r['office'], r['special'])
            if key not in seen or len(r['candidates']) > len(seen[key]['candidates']):
                seen[key] = r
        return sorted(seen.values(), key=lambda r: (r['office'], r['state']))
    senate, gov = dedupe(senate), dedupe(gov)
    json.dump({'senate': senate, 'governor': gov}, open('wiki_inventory.json', 'w'), indent=1)
    print(f"senate races: {len(senate)}  governor races: {len(gov)}")
    problems = []
    for r in senate + gov:
        names = [(c['name'], c['party'] or '?') for c in r['candidates']]
        if len(names) < 2: problems.append(('few-cands', r['state'], r['office'], r['special']))
        for n, p in names:
            if p == '?': problems.append(('noparty', r['state'], r['office'], n))
    print("PROBLEMS:")
    for p in problems: print(' ', p)

if __name__ == '__main__':
    main()
