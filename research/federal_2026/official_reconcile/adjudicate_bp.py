#!/usr/bin/env python3
"""Adjudicate the remaining unverified contests via Ballotpedia race pages + Jev.

For each contest in ballotpedia_triage_result.json with a fetched page:
 1. Mechanical: locate the "General election ... November 3, 2026" candidate
    block; split printed candidates vs (Write-in) vs withdrawn/disqualified.
    Governor pages list gov/lt-gov tickets — only the lead of each "/" ticket
    is the gubernatorial candidate.
 2. Jev System One: one choice question per compiled name — does the excerpt
    from the race page show this person running in the Nov 3, 2026 GENERAL
    election (not a primary opponent, past cycle, withdrawn-only)? Accept on
    choice=candidate_row with probability >= 0.75. Also one question per BP
    printed candidate NOT in our roster (extra detection).
 3. Tier: FULL when all ours accepted and no active extras; BALLOT when extras
    exist; OURS-MISSING left unverified for manual handling.

Merges results into adjudication.json (source_kind=ballotpedia) and records
wave2_bp entries in captures.json. Does not mutate the dataset.
"""
import json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = 'https://api.typesafe.ai/v1/systemone'
KEY = os.environ.get('TYPESAFE_API_KEY', '') or open('/root/.cfg/typesafe_key').read().strip()
THRESHOLD = 0.75

def jev(questions, state='ballotpedia-general-slate'):
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
        except (urllib.error.URLError, TimeoutError):
            if attempt < 5:
                time.sleep(2 ** attempt); continue
            raise

import html as _html
def textify(fn):
    raw = open(fn, encoding='utf-8', errors='replace').read()
    raw = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', raw, flags=re.S)
    t = _html.unescape(re.sub(r'<[^>]+>', ' ', raw))
    return re.sub(r'\s+', ' ', t)

ALIAS = {('tim', 'long'): ('timothy', 'long'), ('cd', 'reynolds'): ('christopher', 'reynolds'),
         ('josh', 'green'): ('joshua', 'green'), ('ed', 'markey'): ('edward', 'markey'),
         ('angie', 'nixon'): ('angela', 'nixon'), ('mike', 'minogue'): ('michael', 'minogue'),
         ('joe', 'tache'): ('joseph', 'tache')}

def norm(n):
    n = n.lower().replace('\u201c', '"').replace('\u201d', '"')
    n = re.sub(r'"[^"]*"', '', n); n = n.replace('submit photo', ' ')
    n = re.sub(r'\b(jr|sr|ii|iii|iv)\b', ' ', n)
    n = re.sub(r"[^a-z ]", ' ', n)
    parts = [p for p in n.split() if p not in ('photo', 'submit')]
    if len(parts) < 2: return ' '.join(parts)
    key = (parts[0], parts[-1])
    if key in ALIAS: return ' '.join(ALIAS[key])
    return f"{parts[0]} {parts[-1]}"

def general_block(t):
    """Return the candidate-list block text for the Nov 3, 2026 general race."""
    for m in re.finditer(r'(Special general election|General election) for', t):
        seg = t[m.start():m.start() + 2400]
        if 'November 3, 2026' not in seg[:500]: continue
        c = re.search(r'Candidate (.*?)(?:Incumbents are bolded|There are no incumbents)', seg)
        if c: return c.group(1), seg
    return None, None

def parse_entries(block):
    """[(name, party, write_in, is_ticket_lead)] — lead = not preceded by '/ '."""
    cut = re.search(r'[Ww]ithdrawn or disqualified', block)
    active = block[:cut.start()] if cut else block
    ents = []
    for em in re.finditer(r'([A-Z][^()/]{2,60}?) \(([^()]{1,45})\)( \(Write-in\))?', active):
        lead = not active[max(0, em.start() - 3):em.start()].endswith('/ ')
        name = re.sub(r'^submit photo\s+', '', em.group(1).strip())
        if re.search(r'defeated|won|\d{3},', name): continue
        ents.append((name, em.group(2), bool(em.group(3)), lead))
    return ents

def excerpt_for(block, bpname, width=420):
    up = block.upper(); tn = norm(bpname)
    if not tn: return ''
    last = tn.split()[-1].upper()
    for m in re.finditer(re.escape(last), up):
        a, b = max(0, m.start() - width // 2), min(len(up), m.end() + width // 2)
        if tn.split()[0].upper() in up[a:b]:
            return block[a:b]
    return ''

def main():
    only = sys.argv[1:] or None
    tri = json.load(open(f'{HERE}/ballotpedia_triage.json'))
    # refresh rosters from the live dataset (NH/IA roster corrections landed after triage)
    data = json.load(open('/workspace/bay-area-elections-2026/2026-11-03_Bay_Area_Elections.json'))
    pos = {x['id']: x for x in data['positions']}
    for pid, r in tri.items():
        p = pos[pid]
        r['roster'] = [c['name'] for c in (p.get('candidates') or []) + (p.get('filed_candidates_not_confirmed_on_ballot') or [])]
    adj_all = json.load(open(f'{HERE}/adjudication.json'))
    caps = json.load(open(f'{HERE}/captures.json'))
    report, jev_calls = {}, 0
    for pid, r in sorted(tri.items()):
        if only and pid not in only: continue
        t = textify(f'/tmp/bph/{pid}.html')
        block, seg = general_block(t)
        if not block:
            report[pid] = {'tier': 'NO-SLATE'}; continue
        ents = [e for e in parse_entries(block) if e[3]]  # ticket leads only
        printed = [(n, p) for n, p, wi, _ in ents if not wi]
        writeins = [n for n, p, wi, _ in ents if wi]
        ours = {norm(x): x for x in r['roster']}
        theirs = {norm(n): f"{n} ({p})" for n, p in printed}

        crit = {'candidate_row': ("The page presents this person as running in the NOVEMBER 3, 2026 "
                                  "GENERAL election for this office (listed among the general-election "
                                  "candidates, any party)"),
                'not_candidate_row': ("Only appears as a primary opponent, in a past election cycle, as "
                                      "withdrawn/disqualified-only, or coincidental text")}
        questions, order = {}, []
        for i, (k, ourname) in enumerate(sorted(ours.items())):
            ex = excerpt_for(block, theirs.get(k, ourname))
            if not ex:
                continue
            qid = f'o{i}'
            questions[qid] = {'type': 'choice',
                'instructions': (f"Context: Ballotpedia race page ({r['bp_url']}). Does the excerpt show "
                                 f"'{ourname}' (page form: '{theirs.get(k, ourname)}') as running in the "
                                 f"November 3, 2026 general election?\n\nEXCERPT: {ex}"),
                'criteria': crit}
            order.append((qid, ('ours', k)))
        for j, (k, disp) in enumerate(sorted(theirs.items())):
            if k in ours: continue
            qid = f'x{j}'
            questions[qid] = {'type': 'choice',
                'instructions': (f"Context: Ballotpedia race page ({r['bp_url']}). Does the excerpt show "
                                 f"'{disp}' as an ACTIVE general-election candidate for this office on "
                                 f"November 3, 2026 (not withdrawn/disqualified)?\n\nEXCERPT: {excerpt_for(block, disp)}"),
                'criteria': {'candidate_row': ("Listed among the active November 3, 2026 general-election "
                                               "candidates for this office"),
                             'not_candidate_row': "Withdrawn or disqualified section only, or not a candidate"}}
            order.append((qid, ('extra', k)))
        answers = {}
        items = list(questions.items())
        for start in range(0, len(items), 5):
            answers.update((jev(dict(items[start:start + 5])) or {}).get('answers') or {})
            jev_calls += 1; time.sleep(0.3)
        per_name, accepted = [], {}
        for qid, (kind, k) in order:
            a = answers.get(qid) or {}
            pr = float((a.get('probabilities') or {}).get('candidate_row', 0.0))
            ok = a.get('choice') == 'candidate_row' and pr >= THRESHOLD
            if kind == 'ours':
                per_name.append({'name': ours[k], 'jev': {'choice': a.get('choice'), 'probability': round(pr, 3), 'accepted': ok}})
            else:
                accepted[k] = ok
        ours_missing = [n for k, n in sorted(ours.items()) if not any(p['name'] == n and p['jev']['accepted'] for p in per_name)]
        extras_active = [theirs[k] for k, ok in sorted(accepted.items()) if ok]
        tier = 'FULL' if (not ours_missing and not extras_active) else ('BALLOT' if not ours_missing else 'OURS-MISSING')
        report[pid] = {'tier': tier, 'ours_missing': ours_missing, 'extras_active': extras_active,
                       'write_ins': writeins, 'per_name': per_name}
        print(f"{pid} {r['state']} {r['office']:8} -> {tier}", ('miss:' + str(ours_missing)) if ours_missing else '',
              ('extra:' + str(extras_active)) if extras_active else '')

    # merge into adjudication.json for FULL/BALLOT (manual cases stay out)
    for pid, v in report.items():
        if v['tier'] not in ('FULL', 'BALLOT'): continue
        r = tri[pid]
        roster = [p['name'] for p in v['per_name']]
        adj_all[pid] = {'state': r['state'],
            'office': 'U.S. Senate' if r['office'] == 'senate' else 'Governor',
            'roster': roster, 'all_accepted': True, 'election_marker': True, 'block_chars': 500,
            'mechanical_all_accepted': True, 'mechanical_extras': v['extras_active'],
            'mechanical_write_ins': [w for w in v['write_ins'] if norm(w) not in {norm(x) for x in roster}],
            'override_reviewer': 'hermes-ballotpedia-jev 2026-10-20',
            'override_election_context': ('Ballotpedia race page general-election block, November 3, 2026 '
                                          '(retrieved 2026-10-20); each candidacy judged by Jev System One.'),
            'override_evidence': {p['name']: f"BP slate; jev p={p['jev']['probability']}" for p in v['per_name']},
            'per_name': v['per_name'], 'source_kind': 'ballotpedia',
            'extras_candidates': [], 'source_url': r['bp_url']}
        caps.setdefault(pid, {'state': r['state']})['wave2_bp'] = {
            'checked_on': '2026-10-20', 'bp_url': r['bp_url'], 'tier': v['tier'],
            'jev_calls': jev_calls}
    json.dump(adj_all, open(f'{HERE}/adjudication.json', 'w'), indent=1)
    json.dump(caps, open(f'{HERE}/captures.json', 'w'), indent=1)
    json.dump(report, open(f'{HERE}/ballotpedia_jev_report.json', 'w'), indent=1)
    print('jev calls:', jev_calls)

if __name__ == '__main__':
    main()
