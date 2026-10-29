#!/usr/bin/env python3
"""Build candidate recommendations: Jev picks the best candidate per race; a Qwen
sub-agent writes the race-level recommendation reason; both readers (explore +
find-my-ballot) render the recommendation inside each race. Deterministic precedence (owner rules):
  1. A confirmed Muslim-community candidate wins that race outright.
  2. Otherwise Jev chooses the best graded candidate.
  3. No candidate with a political grade -> no information.
  4. Only grades below C -> no known good candidate.
Jev answers are cached and resumable; summaries are cached too."""
import argparse
import hashlib
import json
import os
import re
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "2026-11-03_Bay_Area_Elections.json"
OBS = ROOT / "research/candidate-community/observations.json"
OUTDIR = ROOT / "research" / "candidate-recommendations"
PLAN = OUTDIR / "recommendations-2026-10-28-latest.json"
JEV_CACHE = OUTDIR / "jev-answers-2026-10-28-latest.jsonl"
SUM_CACHE = OUTDIR / "summaries-2026-10-28-latest.jsonl"
REASON_CACHE = OUTDIR / "race-reasons-2026-10-28-latest.jsonl"

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_KEY = None  # Loaded only for an uncached provider call; offline builds need no key.
LMSTUDIO_URL = "http://192.168.0.66:11434/v1/chat/completions"
LMSTUDIO_MODEL = "qwen/qwen3.8-27b"
LMSTUDIO_REASONING = "medium"

GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

CAT_MUSLIM = "muslim_community"
CAT_JEV = "jev_pick"
CAT_NO_GOOD = "no_good_candidate"
CAT_NO_INFO = "no_information"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode().lower())


def grade_of(c):
    """The candidate's pro-Palestine grade. Trust the dataset's own label: it is
    already N/A when there is no usable evidence, and it is what the site shows."""
    g = c.get("pro_palestine_score_grade")
    if not g or g == "N/A":
        return None
    return g


def all_candidates(p):
    out = []
    for r in ("candidates", "filed_candidates_not_confirmed_on_ballot", "qualified_write_in_candidates"):
        for c in p.get(r) or []:
            out.append(c)
    return out


def digest(s, n):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def cand_brief(c):
    """Compact, factual digest of one candidate for Jev and the summary model."""
    ev = c.get("pro_palestine_evaluation") or {}
    expl = c.get("pro_palestine_explanation") or {}
    b = {
        "name": c.get("name"),
        "party": c.get("party"),
        "grade": c.get("pro_palestine_score_grade"),
        "score": c.get("pro_palestine_score"),
    }
    gp = c.get("gaza_platform")
    if isinstance(gp, dict) and gp.get("summary"):
        b["platform"] = digest(gp.get("summary"), 260)
    pp = c.get("platform_positions")
    if isinstance(pp, dict) and pp.get("positions"):
        pts = []
        for pos in pp["positions"][:4]:
            t = pos.get("topic")
            s = pos.get("summary") or pos.get("position")
            if t and s:
                pts.append(f"{t}: {s}")
        if pts:
            b["positions"] = [digest(x, 160) for x in pts]
    end = c.get("endorsements") or []
    end_names = []
    for e in end:
        if isinstance(e, dict):
            nm = e.get("endorser")
            rel = e.get("relation")
            if nm and rel in (None, "endorsed", "preferred"):
                end_names.append(nm)
    if end_names:
        b["endorsed_by"] = end_names[:8]
    ge = c.get("gaza_evidence") or []
    acts = []
    for g in ge:
        if isinstance(g, dict):
            t = g.get("action") or g.get("title") or g.get("summary")
            if t:
                acts.append(t)
    if acts:
        b["gaza_actions"] = [digest(x, 140) for x in acts[:3]]
    if isinstance(expl, dict) and expl.get("text"):
        b["explanation"] = digest(expl["text"], 220)
    return b


def classify(data, obs):
    trues = [o for o in obs["observations"] if o.get("part_of_muslim_community") is True]
    muslim_by_pos = {}
    for o in trues:
        muslim_by_pos.setdefault(o["position_id"], []).append(o["candidate"])
    # The dataset's office_category casing is inconsistent across scans ("City council" vs
    # "City Council"); canonicalize the known collisions so filters and groupings stay stable.
    OFFICE_CATEGORY_CANON = {
        "city clerk": "City Clerk",
        "city council": "City Council",
        "city treasurer": "City Treasurer",
    }
    def office_category(p):
        raw = p.get("office_category") or ""
        return OFFICE_CATEGORY_CANON.get(raw.lower(), raw)
    races = []
    for p in data["positions"]:
        cands = all_candidates(p)
        if not cands:
            continue
        office = p.get("office")
        base = {
            "position_id": p["id"],
            "jurisdiction": p.get("jurisdiction") or "",
            "office_category": office_category(p),
            "office": office,
            "district_or_seat": p.get("district_or_seat"),
            "counties": p.get("counties") or [],
            "ballot_status": p.get("ballot_status"),
            "roster": [
                {
                    "name": c.get("name"),
                    "party": c.get("party"),
                    "grade": c.get("pro_palestine_score_grade"),
                    "score": c.get("pro_palestine_score"),
                    "muslim": norm(c.get("name")) in {norm(m) for m in muslim_by_pos.get(p["id"], [])},
                }
                for c in cands
            ],
        }
        muslims = [c for c in cands if norm(c.get("name")) in {norm(m) for m in muslim_by_pos.get(p["id"], [])}]
        if muslims:
            base["category"] = CAT_MUSLIM
            base["recommended"] = muslims[0]["name"]
            base["recommend_reason"] = "Confirmed member of the Muslim community."
            base["muslim_candidate"] = muslims[0]["name"]
            base["needs_summary"] = True
        else:
            graded = [c for c in cands if grade_of(c)]
            if not graded:
                base["category"] = CAT_NO_INFO
                base["recommended"] = None
                base["recommend_reason"] = "No recommendation due to a lack of information about this race."
                base["needs_summary"] = False
            else:
                below_c = [c for c in graded if GRADE_ORDER[grade_of(c)] > GRADE_ORDER["C"]]
                if len(below_c) == len(graded):
                    base["category"] = CAT_NO_GOOD
                    base["recommended"] = None
                    base["recommend_reason"] = "No recommendation due to a lack of known good candidates."
                    base["needs_summary"] = False
                else:
                    base["category"] = CAT_JEV
                    base["recommended"] = None  # filled by Jev
                    base["recommend_reason"] = "Jev selected the strongest candidate in this race."
                    base["needs_summary"] = True
        races.append(base)
    return races


def jev_request(race):
    """Recommendations compare published letter grades, per the documented policy.

    Evidence is evaluated in the scorecard, not reinterpreted by this selector.
    The complete request is archived and hashed so changed grades/rosters cannot
    silently reuse a decision cached only against the race ID.
    """
    candidates = [{k: c.get(k) for k in ("name", "party", "grade")}
                  for c in race["roster"] if c.get("grade") in GRADE_ORDER]
    return {"model": "jev-latest", "state": {
        "position_id": race["position_id"], "office": race["office"],
        "district_or_seat": race.get("district_or_seat"), "candidates": candidates},
        "questions": {"best_candidate": {"type": "choice",
            "instructions": "Choose the strongest candidate for Palestinian justice using only the supplied published letter grades. A is strongest, followed by B, C, D, E, F. Do not use outside knowledge. Choose among the strongest tied candidates when grades are equal.",
            "criteria": {c["name"]: "Published pro-Palestine grade: " + c["grade"] for c in candidates}}}}


def request_hash(request):
    return hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _jev_call(req):
    key = JEV_KEY or os.environ.get("JEV_API_KEY", "").strip()
    if not key:
        raise ValueError("An uncached Jev call requires JEV_API_KEY or --jev-key-file")
    last = None
    for attempt in range(4):
        r = urllib.request.Request(JEV_URL, data=req, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                ans = json.load(resp)
            ch = ans["answers"]["best_candidate"]
            from grade_gaza import validate_response
            validate_response(json.loads(req)["questions"], ans)
            return {"choice": ch.get("choice"), "confidence": ch.get("confidence"), "probabilities": ch.get("probabilities"), "response": ans}
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Jev call failed: {last}")


def jev_phase(races):
    cache = _load_jsonl(JEV_CACHE)
    requests = {r["position_id"]: jev_request(r) for r in races if r["category"] == CAT_JEV}
    todo = [r for r in races if r["category"] == CAT_JEV and
            not cached_pick_matches(cache.get(r["position_id"]), requests[r["position_id"]])]
    print(f"Jev: {len(races)} total, {len(cache)} cached, {len(todo)} to run")
    def work(r):
        request = requests[r["position_id"]]
        candidates = request["state"]["candidates"]
        if len(candidates) == 1:
            name = candidates[0]["name"]
            res = {"choice": name, "confidence": 1.0, "probabilities": {name: 1.0}, "single_candidate": True}
        else:
            res = _jev_call(json.dumps(request).encode())
        rec = {"position_id": r["position_id"], "choice": res["choice"], "confidence": res.get("confidence"),
               "probabilities": res.get("probabilities"), "model": res.get("response", {}).get("model", "jev-latest"),
               "request": request, "request_sha256": request_hash(request),
               "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if res.get("single_candidate"): rec["single_candidate"] = True
        if res.get("response"): rec["response"] = res["response"]
        if not cached_pick_matches(rec, request):
            raise ValueError("Invalid Jev recommendation: " + r["position_id"])
        return r["position_id"], rec
    JEV_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        for pid, rec in ex.map(work, todo):
            with JEV_CACHE.open("a") as f:
                f.write(json.dumps(rec) + "\n")
            cache[pid] = rec
            r = next(x for x in races if x["position_id"] == pid)
            r["jev"] = rec
    # apply cached + fresh to all jev races
    for r in races:
        if r["category"] == CAT_JEV and r["position_id"] in cache:
            r["jev"] = cache[r["position_id"]]
            r["recommended"] = cache[r["position_id"]]["choice"]
    return races


def cached_pick_matches(cached, request):
    if not cached or cached.get("request") != request or cached.get("request_sha256") != request_hash(request):
        return False
    grades = {c["name"]: c["grade"] for c in request["state"]["candidates"]}
    choice = cached.get("choice")
    return choice in grades and GRADE_ORDER[grades[choice]] == min(map(GRADE_ORDER.get, grades.values()))


def _lmstudio(prompt, max_tokens=4000):
    body = json.dumps({"model": LMSTUDIO_MODEL, "reasoning_effort": LMSTUDIO_REASONING, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    last = None
    for attempt in range(4):
        r = urllib.request.Request(LMSTUDIO_URL, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=300) as resp:
                d = json.load(resp)
            m = d["choices"][0]["message"]
            text = (m.get("content") or "").strip()
            if not text:
                raise RuntimeError("empty content")
            text = re.sub(r"\s+", " ", text).strip()
            return text
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"LM Studio call failed: {last}")


def _load_jsonl(path):
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                o = json.loads(line)
                out[o["position_id"]] = o
    return out


# ---- race-level recommendation reasons (owner framework, 2026-10-28) ----
# Litmus test first; silence is a ding, not neutrality; no numeric scores;
# endorsement policy: Muslim-community-aligned vs AIPAC/Zionist/Hindutva only.
COMMUNITY_ENDORSERS = ["bamc", "cair", "aroc", "arab resource", "vote for peace",
                       "khanna", "muslim", "jewish voice for peace", "jvp",
                       "peace action", "organize for peace", "track aipac"]
ISRAEL_ALIGNED_ENDORSERS = ["aipac", "united democracy project", "dmfi",
                            "democratic majority for israel", "cufo", "cufi",
                            "christians united", "israeli-american civic", "ican",
                            "bajc", "jstreet", "j street", "hindu", "americans4hindus",
                            "jewish democratic council"]
REASON_ENDORSER_RELATIONS = (None, "endorsed", "preferred", "opposed", "recommended")


def relevant_endorsements(c):
    community, contrast = [], []
    for e in c.get("endorsements") or []:
        if not isinstance(e, dict):
            continue
        nm, rel = e.get("endorser"), e.get("relation")
        if not nm or rel not in REASON_ENDORSER_RELATIONS:
            continue
        low = nm.lower()
        if any(p in low for p in COMMUNITY_ENDORSERS):
            community.append((nm, rel or "endorsed"))
        elif any(p in low for p in ISRAEL_ALIGNED_ENDORSERS):
            contrast.append((nm, rel or "endorsed"))
    return community, contrast


def reason_evidence(c):
    """Textual evidence for the reason prompt. Numeric scores deliberately excluded."""
    lines = []
    expl = c.get("pro_palestine_explanation") or {}
    if isinstance(expl, dict) and expl.get("summary"):
        lines.append("Our assessment: " + digest(expl["summary"], 460))
    pp = c.get("platform_positions")
    if isinstance(pp, dict) and pp.get("positions"):
        for pos in pp["positions"][:4]:
            t, s = pos.get("topic"), pos.get("summary") or pos.get("position")
            if t and s:
                lines.append(f"Platform — {t}: " + digest(s, 220))
    for g in (c.get("gaza_evidence") or [])[:8]:
        if isinstance(g, dict):
            t = g.get("action") or g.get("title") or g.get("summary")
            d = g.get("date") or g.get("as_of")
            if t:
                lines.append("Record" + (f" ({d})" if d else "") + ": " + digest(t, 220))
    community, contrast = relevant_endorsements(c)
    if community:
        lines.append("Muslim-community / pro-Palestine-aligned records: "
                     + "; ".join(f"{n} ({r})" for n, r in community[:6]))
    if contrast:
        lines.append("Israel-aligned / AIPAC / Hindu-nationalist-aligned records: "
                     + "; ".join(f"{n} ({r})" for n, r in contrast[:6]))
    return lines


def reason_prompt(race, pos_by_id):
    cands = all_candidates(pos_by_id[race["position_id"]])
    rec = next(c for c in cands if c.get("name") == race["recommended"])
    graded = [c for c in cands if grade_of(c) and c.get("name") != race["recommended"]]
    graded.sort(key=lambda c: GRADE_ORDER[grade_of(c)])
    graded = graded[:3]
    federal = race.get("office_category") in ("U.S. House", "U.S. Senate")
    lines = [f"Race: {race['office']}"
             + (f" — {race['district_or_seat']}" if race.get("district_or_seat") else "")
             + f" ({race['jurisdiction'] or ' '.join(race.get('counties') or [])}), November 3, 2026 general election."]
    if race["category"] == CAT_MUSLIM:
        lines.append(f"We support {race['recommended']}, a confirmed member of the Muslim community,"
                     " our community's candidate in this race.")
    else:
        lines.append(f"Our research selects {race['recommended']} as the strongest candidate in this race.")
    lines += ["", f"RECOMMENDED CANDIDATE: {rec.get('name')}"
              + (f" ({rec.get('party')})" if rec.get("party") else ""),
              "- " + "\n- ".join(reason_evidence(rec))]
    if graded:
        lines += ["", "OTHER CANDIDATES IN THIS RACE WE HAVE INFORMATION ABOUT:"]
        for c in graded:
            lines.append(f"{c.get('name')}" + (f" ({c.get('party')})" if c.get("party") else ""))
            lines += ["- " + l for l in reason_evidence(c)[:6]]
    else:
        lines += ["", "No other candidate in this race has a researched record."]
    framing = ("" if not federal else
               "This is a FEDERAL race: for a federal office-seeker, taking no recorded position on these "
               "questions effectively supports the status quo, and the paragraph should say that plainly "
               "when the recommended candidate's shown record lacks litmus-test action.")
    lines += ["",
              "Write ONE voter-facing paragraph of up to 200 words explaining why a voter should support "
              f"{race['recommended']} in this race and why {race['recommended']} is stronger than the other "
              "candidates above, grounded in the textual records shown. "
              "OUR FRAMEWORK: voters judge candidates first on two litmus tests — opposing the genocide in "
              "Gaza and ending U.S. military/economic aid to Israel. When the recommended candidate's shown "
              "record contains concrete acts on these tests (cosponsoring the Block the Bombs Act, voting "
              "against arms funding, calling it a genocide, divestment action), name the specific acts with "
              "their dates or bill names as shown. When the shown record does NOT contain them, be "
              "transparent: one plain sentence stating what the candidate has not done on the record (for "
              "example: has not called it a genocide; has not backed blocking weapons transfers; voted for "
              "aid bills), then explain why the candidate is still the best option listed. Never hide a "
              "shortfall and never invent one. Do not write meta-language like 'the record does not show' or "
              "'has not published a stated position' — write about what the candidate has or has not done. "
              "A candidate who refused to properly support Palestinians when put in the position (a contrary "
              "vote, an opposed resolution, rejecting community asks) gets that held against them; an "
              "abstention under heavy pressure can read as qualified support if the shown assessment says so — "
              "follow the shown assessments. " + framing + " "
              "Rules: never mention any numeric score or rating; a letter grade may appear at most in "
              "passing — prefer explaining actual acts, votes, statements and positions. Use ONLY the facts "
              "shown; never add outside knowledge or invent events, dates, quotes or endorsements; if a "
              "competitor has no shown record, say nothing about them. Endorsements: mention only the "
              "'Muslim-community / pro-Palestine-aligned records' and 'Israel-aligned / AIPAC / "
              "Hindu-nationalist-aligned records' lines (Muslim-aligned backing supports a candidate; "
              "AIPAC/UDP/DMFI/ICAN or Hindu-nationalist-aligned backing or opposition is a relevant "
              "contrast); never name any other endorser. Plain prose, no lists, no quotation marks, no "
              f"headings, no AI disclaimer. Name the office once. Output ONLY the paragraph."]
    return "\n".join(lines)


def _policy_match(low, tokens):
    """Word-boundary token match so short tokens like 'ican' cannot hide inside
    'american' (plain substring matching caused a real policy miss)."""
    return any(re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", low) for a in tokens)


def _close_to(a, b):
    """True when a equals b or differs by at most two single-character edits."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 2:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            if cur[-1] > 2:  # prune hopeless rows
                cur[-1] = 3
        prev = cur
    return prev[-1] <= 2


def out_of_policy_endorsers(race, pos_by_id, text):
    """Endorser names present in this race's records but outside the two policy
    buckets; a paragraph that NAMES one violates the endorsement policy.
    Multi-word names are matched exactly (case-sensitive full name) so city or
    county prefixes inside org names cannot false-positive on ordinary prose;
    single distinctive names match on word boundaries. Candidate names in this
    race are never endorsements-of-record for policy purposes."""
    allowed = set(COMMUNITY_ENDORSERS) | set(ISRAEL_ALIGNED_ENDORSERS)
    cand_names = {norm(c.get("name")) for c in all_candidates(pos_by_id[race["position_id"]])}
    cores = set()
    for c in all_candidates(pos_by_id[race["position_id"]]):
        for e in c.get("endorsements") or []:
            if not isinstance(e, dict):
                continue
            nm = e.get("endorser") or ""
            low = nm.lower()
            if not nm or _policy_match(low, allowed):
                continue
            head = re.split(r"[,(]", nm)[0].strip()
            head = re.sub(r"^(hon|dr|mr|mrs|ms|sen|rep|fmr|former|supervisor|assemblymember|mayor|president)\.?\s+", "", head, flags=re.I)
            people = [head] + [m.strip() for m in re.findall(r"\bby\s+([A-Z][\w'\u00c0-\u024f.-]+(?:\s+[A-Z][\w'\u00c0-\u024f.-]+){1,3})", nm)]
            for person in people:
                if not person:
                    continue
                nperson = norm(person)
                if any(nperson == cn or _close_to(nperson, cn) for cn in cand_names):
                    continue
                if len(person.split()) >= 2:
                    cores.add(("phrase", re.sub(r"\s+", " ", person)))
                else:
                    cores.add(("word", norm(person)))
    hits = []
    flat = re.sub(r"\s+", " ", text)
    lower = text.lower()
    for kind, value in sorted(cores, key=lambda x: -len(x[1])):
        if kind == "phrase":
            if value in flat:
                hits.append(value)
        elif len(value) >= 4 and re.search(r"(?<![a-z0-9])" + re.escape(value) + r"(?![a-z0-9])", lower):
            hits.append(value)
    # collapse hits that are substrings of other hits
    hits = [h for h in hits if not any(h != o and h.lower() in o.lower() for o in hits)]
    return hits


def reasons_phase(races, only=None):
    data = json.loads(DATA.read_text())
    by_pos = {p["id"]: p for p in data["positions"]}
    cache = _load_jsonl(REASON_CACHE)
    prompts = {r["position_id"]: reason_prompt(r, by_pos)
               for r in races if r.get("recommended")}
    cached_ok = {}
    for pid, rec in cache.items():
        if rec.get("prompt_sha256") == request_hash(prompts.get(pid, "")) if prompts.get(pid) else False:
            if rec.get("text") and not out_of_policy_endorsers(next((r for r in races if r["position_id"] == pid), {"position_id": pid}), by_pos, rec["text"]):
                cached_ok[pid] = rec
    todo = [r for r in races if r["position_id"] in prompts and r["position_id"] not in cached_ok
            and (not only or r["position_id"] in only)]
    print(f"Reasons: {len(prompts)} picks, {len(cached_ok)} cached, {len(todo)} to run")
    def work(r):
        prompt = prompts[r["position_id"]]
        text = _lmstudio(prompt, max_tokens=8000)
        for _ in range(2):  # endorsement-policy retry: never name out-of-policy backers
            bad = out_of_policy_endorsers(r, by_pos, text)
            if not bad:
                break
            print(f"  [endorser-retry] {r['position_id']}: naming {bad}", flush=True)
            text = _lmstudio(prompt + "\nIMPORTANT: do not name, allude to, or characterize the following people or organizations in this race: "
                             + "; ".join(bad) + ". Output ONLY the paragraph.", max_tokens=8000)
        bad = out_of_policy_endorsers(r, by_pos, text)
        if bad:  # last resort: explicit ban list, describe such backers generically
            text = _lmstudio(prompt + "\nHARD CONSTRAINT: you may name ONLY organizations from the two lines "
                             "'Muslim-community / pro-Palestine-aligned records' and 'Israel-aligned / AIPAC / "
                             "Hindu-nationalist-aligned records'. Do NOT name or describe: "
                             + "; ".join(bad) + ". If an opponent's strength comes from such groups, say "
                             '"labor and civic endorsements" without naming them. Output ONLY the paragraph.',
                             max_tokens=8000)
            bad = out_of_policy_endorsers(r, by_pos, text)
        if bad:
            raise ValueError("out-of-policy endorsers after retries: " + "; ".join(bad))
        rec = {"position_id": r["position_id"], "text": text, "words": len(text.split()),
               "model": LMSTUDIO_MODEL, "prompt_sha256": request_hash(prompt)}
        return r["position_id"], rec
    def _run(batch):
        with ThreadPoolExecutor(max_workers=2) as ex:  # LM Studio concurrency = 2
            futs = {ex.submit(work, r): r for r in batch}
            for fut in as_completed(futs):
                r = futs[fut]
                try:
                    pid, rec = fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"  [FAILED] {r['position_id']} {r['recommended']}: {e}", flush=True)
                    continue
                if not 30 <= rec["words"] <= 215:
                    print(f"  [FAILED] {r['position_id']} {r['recommended']}: {rec['words']} words outside 30-215", flush=True)
                    continue
                with REASON_CACHE.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                cache[pid] = rec
                print(f"  [{len(cache)}] {pid} {r['recommended']} -> {rec['words']} words", flush=True)
    for i in range(0, len(todo), 4):
        _run(todo[i:i + 4])
    for r in races:
        if r["position_id"] in cached_ok:
            r["summary"] = cached_ok[r["position_id"]]
    missing = [r["position_id"] for r in races if r["position_id"] in prompts and "summary" not in r]
    if missing:
        print(f"Reasons incomplete: {len(missing)} missing (re-run 'reasons'): {missing[:8]}", flush=True)
        if not only:
            raise SystemExit(1)
    return races


def build_pages():
    """Rebuild index.html and ballot.html (both carry the embedded recommendation map)."""
    import build_site
    for page in ("index", "ballot"):
        result = build_site.render(page)
        (ROOT / f"{page}.html").write_text(result, encoding="utf-8")
        print(f"Built {page}.html ({(ROOT / f'{page}.html').stat().st_size:,} bytes)")


def validate_plan(races, data):
    """Refuse a stale page after a new score publication or roster change."""
    expected = {r["position_id"]: r for r in classify(data, json.loads(OBS.read_text()))}
    if len(races) != len(expected) or {r["position_id"] for r in races} != set(expected):
        raise ValueError("Recommendation race coverage differs from the current dataset")
    for race in races:
        base = expected[race["position_id"]]
        for key in ("roster", "category", "ballot_status", "office", "district_or_seat", "counties", "jurisdiction"):
            if race.get(key) != base.get(key):
                raise ValueError("Stale recommendation " + key + ": " + race["position_id"])
        if race["category"] == CAT_JEV:
            if not cached_pick_matches(race.get("jev"), jev_request(race)) or race.get("recommended") != race["jev"]["choice"]:
                raise ValueError("Recommendation decision differs from current grades: " + race["position_id"])
        elif race.get("recommended") != base.get("recommended"):
            raise ValueError("Recommendation differs from deterministic rule: " + race["position_id"])


def save_plan(races):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_on": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_dataset": DATA.name,
        "source_dataset_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
        "source_score_publication_id": json.loads(DATA.read_text()).get("pro_palestine_grading", {}).get("publication_id"),
        "pending_summaries": [r["position_id"] for r in races if r.get("recommended") and not r.get("summary")],
        "rules": "Muslim-community candidate first; else Jev best-of-graded; none graded = no information; all grades below C (D/F) = no known good candidate.",
        "counts": {
            CAT_MUSLIM: sum(1 for r in races if r["category"] == CAT_MUSLIM),
            CAT_JEV: sum(1 for r in races if r["category"] == CAT_JEV),
            CAT_NO_GOOD: sum(1 for r in races if r["category"] == CAT_NO_GOOD),
            CAT_NO_INFO: sum(1 for r in races if r["category"] == CAT_NO_INFO),
        },
        "races": races,
    }
    PLAN.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {PLAN.relative_to(ROOT)}: {json.dumps(payload['counts'])}")


def main():
    global PLAN, JEV_CACHE, SUM_CACHE, REASON_CACHE, JEV_KEY
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["classify", "jev", "reasons", "build", "all", "refresh"])
    ap.add_argument("--plan", type=Path, default=PLAN)
    ap.add_argument("--jev-cache", type=Path, default=JEV_CACHE)
    ap.add_argument("--summary-cache", type=Path, default=SUM_CACHE)
    ap.add_argument("--reason-cache", type=Path, default=REASON_CACHE)
    ap.add_argument("--only", default=None, help="reasons: comma-separated position ids")
    ap.add_argument("--jev-key-file", type=Path)
    args = ap.parse_args()
    PLAN, JEV_CACHE, SUM_CACHE, REASON_CACHE = args.plan.resolve(), args.jev_cache.resolve(), args.summary_cache.resolve(), args.reason_cache.resolve()
    if args.jev_key_file: JEV_KEY = args.jev_key_file.read_text().strip()
    data = json.loads(DATA.read_text())
    obs = json.loads(OBS.read_text())
    if args.command in ("classify", "all", "refresh"):
        races = classify(data, obs)
        save_plan(races)
    if args.command == "refresh":
        # Publish the current choices/grades without narratives from an older run.
        races = jev_phase(races)
        save_plan(races)
        build_pages()
    elif args.command == "all":
        races = json.loads(PLAN.read_text())["races"]
        races = jev_phase(races)
        save_plan(races)
        races = reasons_phase(races)
        save_plan(races)
        build_pages()
    elif args.command == "jev":
        races = json.loads(PLAN.read_text())["races"]
        races = jev_phase(races)
        save_plan(races)
    elif args.command == "reasons":
        races = json.loads(PLAN.read_text())["races"]
        only = set(args.only.split(",")) if args.only else None
        races = reasons_phase(races, only=only)
        save_plan(races)
    elif args.command == "build":
        races = json.loads(PLAN.read_text())["races"]
        validate_plan(races, data)
        build_pages()


if __name__ == "__main__":
    main()
