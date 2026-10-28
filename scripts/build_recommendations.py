#!/usr/bin/env python3
"""Build candidate recommendations: Jev picks the best candidate per race; a Qwen
sub-agent writes a short voter summary; a standalone recommendations.html is
published. Deterministic precedence (owner rules):
  1. A confirmed Muslim-community candidate wins that race outright.
  2. Otherwise Jev chooses the best graded candidate.
  3. No candidate with a political grade -> no information.
  4. Only grades below C -> no known good candidate.
Jev answers are cached and resumable; summaries are cached too."""
import argparse
import hashlib
import json
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
PLAN = OUTDIR / "recommendations-2026-10-28.json"
JEV_CACHE = OUTDIR / "jev-answers-2026-10-28.jsonl"
SUM_CACHE = OUTDIR / "summaries-2026-10-28.jsonl"
OUT_HTML = ROOT / "recommendations.html"
TEMPLATE = ROOT / "src" / "recommendations.template.html"
DISPLAY_JS = ROOT / "src" / "recommendations-display.js"

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_KEY = Path("/root/.cfg/typesafe_key").read_text().strip()
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


def jev_pick(race, evmap):
    """Call Jev to choose the best candidate among the race's graded candidates."""
    cands = []
    for c in evmap:
        if c.get("grade") and c["grade"] != "N/A":
            cands.append(c)
    if len(cands) == 1:
        return {"choice": cands[0]["name"], "confidence": 1.0, "probabilities": {cands[0]["name"]: 1.0}, "single_candidate": True}
    criteria = {}
    for c in cands:
        bits = [f"Grade {c['grade']} ({c['score']})"]
        if c.get("platform"):
            bits.append(c["platform"])
        if c.get("positions"):
            bits.append("Positions: " + " | ".join(c["positions"][:3]))
        if c.get("endorsed_by"):
            bits.append("Endorsed by: " + ", ".join(c["endorsed_by"][:5]))
        criteria[c["name"]] = digest("; ".join(bits), 420)
    state = {
        "race": f"{race['office']}{' - ' + race['district_or_seat'] if race.get('district_or_seat') else ''}",
        "candidates": [
            {"name": c["name"], "party": c.get("party"), "grade": c.get("grade"), "score": c.get("score"),
             "platform": c.get("platform"), "endorsed_by": c.get("endorsed_by", [])}
            for c in cands
        ],
    }
    questions = {
        "best_candidate": {
            "type": "choice",
            "instructions": {
                "task": "Select the single best candidate to support in this race. Rely ONLY on the candidate records provided: their pro-Palestine grade and evidence, platform positions, and endorsements. Do not use outside knowledge or personal opinion.",
                "candidates": "See the candidates field of the state.",
            },
            "criteria": criteria,
        }
    }
    req = json.dumps({"model": "jev-latest", "state": state, "questions": questions}).encode()
    return _jev_call(req)


def _jev_call(req):
    last = None
    for attempt in range(4):
        r = urllib.request.Request(JEV_URL, data=req, headers={"Authorization": "Bearer " + JEV_KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                ans = json.load(resp)
            ch = ans["answers"]["best_candidate"]
            return {"choice": ch.get("choice"), "confidence": ch.get("confidence"), "probabilities": ch.get("probabilities")}
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Jev call failed: {last}")


def jev_phase(races):
    data = json.loads(DATA.read_text())
    by_pos = {p["id"]: p for p in data["positions"]}
    cache = _load_jsonl(JEV_CACHE)
    todo = [r for r in races if r["category"] == CAT_JEV and r["position_id"] not in cache]
    print(f"Jev: {len(races)} total, {len(cache)} cached, {len(todo)} to run")
    def work(r):
        evmap = [cand_brief(c) for c in all_candidates(by_pos[r["position_id"]])]
        res = jev_pick(r, evmap)
        rec = {"position_id": r["position_id"], "choice": res["choice"], "confidence": res.get("confidence"),
               "probabilities": res.get("probabilities"), "model": "jev-latest"}
        return r["position_id"], rec
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


def summary_prompt(race, evmap):
    rec = race["recommended"]
    winner = next((c for c in evmap if c["name"] == rec), None)
    others = [c for c in evmap if c["name"] != rec and c.get("grade") and c["grade"] != "N/A"]
    others.sort(key=lambda c: GRADE_ORDER.get(c["grade"], 9))
    others = others[:2]
    lines = [f"Race: {race['office']}{' - ' + race['district_or_seat'] if race.get('district_or_seat') else ''} (2026 general election)."]
    if race["category"] == CAT_MUSLIM:
        lines.append(f"We support {rec} because they are a confirmed member of the Muslim community and the strongest candidate in this race.")
    else:
        lines.append(f"We support {rec} because Jev selected them as the strongest candidate in this race on the pro-Palestine evidence.")
    lines.append("")
    lines.append(f"RECOMMENDED CANDIDATE: {rec}")
    lines.append(_fmt_evid(winner))
    if others:
        lines.append("")
        lines.append("OTHER GRADGED CANDIDATES (for contrast only):")
        for c in others:
            lines.append(f"- {c['name']}: " + _fmt_evid(c, compact=True))
    lines.append("")
    lines.append("Write a single 45-80 word voter paragraph explaining why a voter should support "
                 f"{rec} in this race and why {rec} is the stronger choice over the other candidate(s). "
                 "Use ONLY the facts above. Plain prose, no lists, no bullet points, no quotation marks, "
                 "no headings, no disclaimer about being an AI, no invented facts. Name the race office once. "
                 "Output ONLY the paragraph.")
    return "\n".join(lines)


def _fmt_evid(c, compact=False):
    if not c:
        return ""
    n = 3 if compact else 5
    bits = [f"Grade {c['grade']} ({c['score']})"]
    if c.get("platform"):
        bits.append("Platform: " + c["platform"])
    if c.get("positions"):
        bits.append("Positions: " + " | ".join(c["positions"][:n]))
    if c.get("endorsed_by"):
        bits.append("Endorsed by: " + ", ".join(c["endorsed_by"][:6]))
    if c.get("gaza_actions"):
        bits.append("Gaza record: " + " | ".join(c["gaza_actions"][:n]))
    if c.get("explanation"):
        bits.append("Assessment: " + c["explanation"])
    return " | ".join(bits)


def summarize(races):
    data = json.loads(DATA.read_text())
    by_pos = {p["id"]: p for p in data["positions"]}
    cache = _load_jsonl(SUM_CACHE)
    todo = [r for r in races if r["needs_summary"] and r["recommended"] and r["position_id"] not in cache]
    print(f"Summaries: {sum(1 for r in races if r['needs_summary'])} needed, {len(cache)} cached, {len(todo)} to run")
    def work(r):
        evmap = [cand_brief(c) for c in all_candidates(by_pos[r["position_id"]])]
        prompt = summary_prompt(r, evmap)
        text = _lmstudio(prompt)
        rec = {"position_id": r["position_id"], "text": text, "words": len(text.split()), "model": LMSTUDIO_MODEL}
        return r["position_id"], rec
    def _run(batch):
        with ThreadPoolExecutor(max_workers=2) as ex:  # LM Studio concurrency = 2
            futs = {ex.submit(work, r): r for r in batch}
            for fut in as_completed(futs):
                r = futs[fut]
                try:
                    pid, rec = fut.result()
                except Exception as e:  # noqa: BLE001 - one flaky item must not kill the batch
                    print(f"  [FAILED] {r['position_id']} {r['recommended']}: {e}", flush=True)
                    continue
                with SUM_CACHE.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                cache[pid] = rec
                r["summary"] = rec
                print(f"  [{len(cache)}] {pid} {r['recommended']} -> {rec['words']} words", flush=True)
    for i in range(0, len(todo), 10):
        _run(todo[i:i + 10])
    for r in races:
        if r["needs_summary"] and r["position_id"] in cache:
            r["summary"] = cache[r["position_id"]]
    missing = [r["position_id"] for r in races if r["needs_summary"] and r["recommended"] and "summary" not in r]
    if missing:
        print(f"Summaries incomplete: {len(missing)} missing (re-run 'summarize' to retry): {missing[:8]}", flush=True)
        raise SystemExit(1)
    return races


def _lmstudio(prompt):
    body = json.dumps({"model": LMSTUDIO_MODEL, "reasoning_effort": LMSTUDIO_REASONING, "max_tokens": 4000,
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


def build_page(races):
    order = {CAT_MUSLIM: 0, CAT_JEV: 1, CAT_NO_GOOD: 2, CAT_NO_INFO: 3}
    data = json.loads(DATA.read_text())
    by_pos = {p["id"]: p for p in data["positions"]}
    for r in races:
        r["order"] = order[r["category"]]
        pos = by_pos.get(r["position_id"], {})
        m = re.search(r"state:([a-z]{2})", pos.get("ocd_division_id") or "")
        r["_state"] = m.group(1).upper() if m else ("CA" if pos.get("counties") else "")
        r["_jur"] = pos.get("jurisdiction") or ""
    def natural_key(s):
        return [(0, int(t)) if t.isdigit() else (1, t) for t in re.split(r"(\d+)", s)]
    races.sort(key=lambda r: (r["order"], r["_jur"], r["_state"], natural_key(r["district_or_seat"] or ""),
                              r["office"] or "", r["position_id"]))
    for r in races:
        r.pop("_state", None); r.pop("_jur", None)
    payload = {
        "generated_on": time.strftime("%Y-%m-%d"),
        "source_dataset": DATA.name,
        "source_dataset_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
        "plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "counts": {
            CAT_MUSLIM: sum(1 for r in races if r["category"] == CAT_MUSLIM),
            CAT_JEV: sum(1 for r in races if r["category"] == CAT_JEV),
            CAT_NO_GOOD: sum(1 for r in races if r["category"] == CAT_NO_GOOD),
            CAT_NO_INFO: sum(1 for r in races if r["category"] == CAT_NO_INFO),
        },
        "races": races,
    }
    html = TEMPLATE.read_text()
    for ph, content in {
        "__RECOMMENDATIONS_DATA_JSON__": json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c"),
        "__RECOMMENDATIONS_DISPLAY_JS__": DISPLAY_JS.read_text(),
        "__CONTEST_LABEL_JS__": (ROOT / "src" / "contest-label.js").read_text(),
    }.items():
        if html.count(ph) != 1:
            raise ValueError(f"Expected one {ph}")
        html = html.replace(ph, content)
    if re.search(r"__[A-Z_]+__", html):
        raise ValueError("Unresolved placeholder")
    OUT_HTML.write_text(html)
    print(f"Built {OUT_HTML.name} ({OUT_HTML.stat().st_size:,} bytes)")


def save_plan(races):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_on": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_dataset": DATA.name,
        "source_dataset_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["classify", "jev", "summarize", "build", "all"])
    args = ap.parse_args()
    data = json.loads(DATA.read_text())
    obs = json.loads(OBS.read_text())
    if args.command in ("classify", "all"):
        races = classify(data, obs)
        save_plan(races)
    if args.command == "all":
        races = json.loads(PLAN.read_text())["races"]
        races = jev_phase(races)
        save_plan(races)
        races = summarize(races)
        save_plan(races)
        build_page(races)
    elif args.command == "jev":
        races = json.loads(PLAN.read_text())["races"]
        races = jev_phase(races)
        save_plan(races)
    elif args.command == "summarize":
        races = json.loads(PLAN.read_text())["races"]
        races = summarize(races)
        save_plan(races)
    elif args.command == "build":
        races = json.loads(PLAN.read_text())["races"]
        build_page(races)


if __name__ == "__main__":
    main()
