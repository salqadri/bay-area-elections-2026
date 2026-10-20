#!/usr/bin/env python3
"""Adjudicate official-source blocks for ballot-status flips.

For contests whose capture contains an office block (verdicts.json FULL/PARTIAL):
 1. Mechanical: extract the office-block text; require a November 2026 general
    election marker on the page; every compiled name contained in the block.
 2. Jev System One per candidate: does the excerpt show this person as a
    CANDIDATE ROW for this office/election (not nav chrome, not another race)?
    Entries ride in instructions; accept choice+probability >= 0.75.
 3. Mechanical extras scan: party-token adjacency names not in our roster are
    reported for human review (an official list with extra candidates means the
    compiled roster is incomplete -> do NOT flip to complete).

Writes adjudication.json. Never mutates the dataset; a separate apply step reads it.
"""
import json, os, re, sys, time, urllib.request, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from match_official import page_text, norm_tokens  # noqa: E402
from office_blocks import block_windows  # noqa: E402

API = 'https://api.typesafe.ai/v1/systemone'
KEY = os.environ.get('TYPESAFE_API_KEY', '') or open('/root/.cfg/typesafe_key').read().strip()
THRESHOLD = 0.75

PARTY_WORDS = re.compile(r'\b(REPUBLICAN|DEMOCRAT(?:IC)?|LIBERTARIAN|GREEN PARTY|CONSTITUTION|'
                         r'INDEPENDENT|UNAFFILIATED|NONPARTISAN|WRITE[- ]?IN|WORKING FAMILIES|'
                         r'CONSERVATIVE|LEGAL MARIJUANA|AMERICA FIRST|REFORM|SOCIALIST)\b', re.I)

def jev(questions, state='ballot-candidate-list-verification'):
    body = json.dumps({'model': 'jev-latest', 'state': state, 'questions': questions}).encode()
    for attempt in range(6):
        try:
            req = urllib.request.Request(API, data=body, headers={
                'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(2 ** attempt); continue
            raise RuntimeError(f'jev HTTP {e.code}: {e.read()[:200]!r}') from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 5:
                time.sleep(2 ** attempt); continue
            raise RuntimeError(f'jev network: {e}') from e

def excerpt_for(block, name, width=340):
    """Window centered on the name-PAIR occurrence. Operate entirely in the
    normalized text so match offsets and slice positions agree (mixing raw and
    normalized produced drifted windows)."""
    t = norm_tokens(name)
    if not t: return ''
    up = re.sub(r'\s+', ' ', block.upper())
    for m in re.finditer(re.escape(t[-1]), up):
        a, b = max(0, m.start()-width//2), min(len(up), m.end()+width//2)
        if t[0] in up[a:b]:
            return up[a:b].strip()
    return ''

def adjudicate(pid):
    caps = json.load(open(f'{HERE}/captures.json'))
    ver = json.load(open(f'{HERE}/verdicts.json'))
    v = ver[pid]; cap = caps[pid]
    text = page_text(f"{HERE}/raw/{cap['path']}")
    office = v['office']
    wins = block_windows(text, office)
    # best window = most roster names contained
    roster = v['roster']
    def score(w):
        up = re.sub(r'\s+', ' ', w.upper())
        n = 0
        for name in roster:
            t = norm_tokens(name)
            if not t: continue
            m = re.search(re.escape(t[-1]), up)
            if m and t[0] in up[max(0, m.start()-60):m.end()+60]:
                n += 1
        return n
    best = max(wins, key=score) if wins else ''
    election_ok = bool(re.search(r'NOVEMBER\s*3?,?\s*(?:2026)?|11/3/2026|GENERAL ELECTION', text.upper()))
    per_name = []
    norm_page = re.sub(r'\s+', ' ', text.upper())
    for name in roster:
        ex = excerpt_for(best, name) if best else ''
        # Office-block windows can miss rows that precede the heading occurrence
        # (wide tables). Fall back to a page-centered window; Jev judges context.
        if not ex:
            ex = excerpt_for(norm_page, name)
        per_name.append({'name': name, 'excerpt': re.sub(r'\s+', ' ', ex)[:400]})
    # Jev batch: one choice question per candidate row check (calibrated shape:
    # questions dict, criteria in each question's instructions/criteria fields)
    crit = {
        'candidate_row': ("The official list presents this person as running for " + office +
                          " in the November 3, 2026 general election — name adjacent to party/"
                          "office/filing/status info for THIS race"),
        'not_candidate_row': ("Navigation menus, footer links, unrelated offices, counties or races, "
                              "withdrawn-only entries without general status, or coincidental word use"),
    }
    questions = {}
    order = []
    for i, pn in enumerate(per_name):
        if not pn['excerpt']:
            pn['jev'] = {'choice': 'no_excerpt', 'probability': 1.0}
            continue
        questions[f'q{i}'] = {
            'type': 'choice',
            'instructions': (f"Context: excerpt from the official {v['state']} candidate list for the "
                             f"November 3, 2026 general election ({cap.get('source_url','')}). Question: does the "
                             f"excerpt show '{pn['name']}' as a candidate row for {office}?\n\n"
                             f"EXCERPT: {pn['excerpt']}"),
            'criteria': crit,
        }
        order.append((f'q{i}', pn))
    answers = {}
    items = list(questions.items())
    for start in range(0, len(items), 5):
        batch = dict(items[start:start+5])
        resp = jev(batch)
        answers.update(resp.get('answers') or {})
        time.sleep(0.35)
    for qid, pn in order:
        a = answers.get(qid) or {}
        ch = a.get('choice'); pr = float((a.get('probabilities') or {}).get('candidate_row', 0.0))
        pn['jev'] = {'choice': ch, 'probability': round(pr, 3),
                     'accepted': ch == 'candidate_row' and pr >= THRESHOLD}
    # extras scan: party-token adjacency with a capitalized name not in roster
    roster_joined = {re.sub(r'[^A-Z]', '', unicodedata.normalize('NFKD', n).upper()) for n in roster}
    up = re.sub(r'\s+', ' ', best.upper())
    extras = set()
    for m in PARTY_WORDS.finditer(up):
        seg = up[max(0, m.start()-70):min(len(up), m.end()+70)]
        names = re.findall(r'\b([A-Z][A-Z]{2,}(?:\s+(?:[A-Z]\.|[A-Z][a-z]+|[A-Z]{2,})){1,3})\b', seg)
        for nm in names:
            jn = re.sub(r'[^A-Z]', '', nm.replace('.', ''))
            if not any(jn in r or r in jn for r in roster_joined):
                extras.add(nm.strip())
    return {'pid': pid, 'state': v['state'], 'office': office, 'source_url': cap.get('source_url'),
            'checked_on': cap.get('checked_on'), 'election_marker': election_ok,
            'block_chars': len(best), 'roster': roster, 'per_name': per_name,
            'all_accepted': bool(per_name) and all(p['jev'].get('accepted') for p in per_name),
            'extras_candidates': sorted(extras)[:25],
            'block_text': re.sub(r'\s+', ' ', best)[:6000]}

def main():
    pids = sys.argv[1:] or [k for k, r in json.load(open(f'{HERE}/verdicts.json')).items()
                            if r.get('verdict') in ('FULL', 'PARTIAL')]
    out_file = f'{HERE}/adjudication.json'
    try: out = json.load(open(out_file))
    except FileNotFoundError: out = {}
    for pid in pids:
        if pid in out and out[pid].get('all_accepted') is not None:
            continue
        try:
            out[pid] = adjudicate(pid)
        except Exception as e:
            print(pid, 'ERROR', str(e)[:150], flush=True); continue
        r = out[pid]
        print(f"{pid} {r['state']} {r['office']}: all_accepted={r['all_accepted']} "
              f"extras={len(r['extras_candidates'])} block={r['block_chars']}ch", flush=True)
        json.dump(out, open(out_file, 'w'), indent=1)

if __name__ == '__main__':
    main()
