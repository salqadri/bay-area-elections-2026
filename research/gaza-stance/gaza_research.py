#!/usr/bin/env python3
"""gaza_research.py v2 — deterministic-first Gaza stance evidence collection.

Per person:
  PASS A (no LLM): fixed query set via serper + X syndication timeline + FEC Schedule A
    regex scan + campaign site text + Wikipedia text; every fetched page keyword-gated,
    assembled into one bounded dossier.
  PASS B (1 LLM call): qwen/qwen3.8-27b (medium thinking) extracts dated evidence items
    AND proposes <=3 follow-up queries ("next steps").
  PASS C (0-1 LLM calls): deterministic fetch of follow-ups, second extraction pass.

GPU discipline: global semaphore caps concurrent LM Studio calls at 4; jev is gone;
reasoning_effort only for the 27b model (flash GGUF ignores it). Fallback chain on error.

Resumable per person via ledger/state.json; evidence append-only, deduped by URL.
Usage: python3 gaza_research.py --county "San Francisco" [--limit N] [--only substr] [--redo]
"""
import argparse, concurrent.futures, json, os, re, sys, threading, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xhunt2 import serper, http, extract_json, norm_name, TextExtract
from date_resolvers import resolve_date
from validate_evidence import check as ev_check, person_contexts, normalize_url

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "2026-11-03_Bay_Area_Elections.json")
STATE_P = os.path.join(ROOT, "ledger", "state.json")
FEC_KEY_FILE = os.environ.get("FEC_KEY_FILE", os.path.expanduser("~/.config/gaza-research/fec_key"))
LMS_URL = os.environ.get("GAZA_LMS_URL", "http://127.0.0.1:11434/v1/chat/completions")
BIG_MODEL = "qwen/qwen3.8-27b"      # Parallel 4 in LM Studio, xhigh thinking
FAST_MODEL = "qwen3.8-flash-next"   # parallel 4 in LM Studio
GPU_SLOTS = threading.Semaphore(4)  # hard cap on concurrent LM Studio calls
_lock = threading.Lock()
TODAY = time.strftime("%Y-%m-%d")

def fec_key():
    try: return open(FEC_KEY_FILE).read().strip() or "DEMO_KEY"
    except Exception: return "DEMO_KEY"
def log(*a): print(time.strftime("[%H:%M:%S]"), *a, flush=True)

# ---------------- LLM (semaphore-capped, fallback chain) ----------------
def lms(prompt, model=BIG_MODEL, effort="medium", timeout=600):
    payload = {"model": model, "temperature": 0,
               "messages": [{"role": "user", "content": prompt}]}
    if effort: payload["reasoning_effort"] = effort
    with GPU_SLOTS:
        r = json.loads(http(LMS_URL, {"Content-Type": "application/json"},
                            timeout=timeout, data=json.dumps(payload).encode()))
    return r["choices"][0]["message"].get("content") or ""

def lms_json(prompt, timeout=420):
    """BIG -> BIG(no-effort) -> FAST chain; returns parsed JSON or None."""
    for model, effort in ((BIG_MODEL, "medium"), (BIG_MODEL, None), (FAST_MODEL, None)):
        try:
            j = extract_json(lms(prompt, model=model, effort=effort, timeout=timeout))
            if isinstance(j, list): j = {"items": j}
            if isinstance(j, dict): return j
        except Exception as e:
            log(f"    lms {model}/{effort} err {repr(e)[:80]}")
    return None

# ---------------- stores ----------------
def load_state(): return json.load(open(STATE_P)) if os.path.exists(STATE_P) else {}
def save_state(s):
    tmp = STATE_P + ".tmp"; json.dump(s, open(tmp, "w"), indent=1); os.replace(tmp, STATE_P)

def safe_key(k): return re.sub(r"[^a-z0-9|_-]", "_", k)[:80]
def ev_path(k): return os.path.join(ROOT, "evidence", safe_key(k) + ".json")
def load_ev(k): return json.load(open(ev_path(k))) if os.path.exists(ev_path(k)) else []

_eid_lock = threading.Lock(); _eid_counter = [None]
def next_eid():
    with _eid_lock:
        if _eid_counter[0] is None:
            mx = 0
            for f in os.listdir(os.path.join(ROOT, "evidence")):
                for e in json.load(open(os.path.join(ROOT, "evidence", f))):
                    m = re.match(r"GE-(\d+)", e.get("id", ""))
                    if m: mx = max(mx, int(m.group(1)))
            _eid_counter[0] = mx
        _eid_counter[0] += 1
        return f"GE-{_eid_counter[0]:04d}"

def add_evidence(k, items, person_ctx=None):
    with _lock:
        cur = load_ev(k); seen = {normalize_url(e["url"]) for e in cur}; added = 0
        for it in items:
            u = (it.get("url") or "").strip()
            if not u.startswith(("http://", "https://")): continue
            # deterministic upgrade: https variants almost always exist; only
            # quarantine when the https URL itself fails to load
            if u.startswith("http://"):
                su = "https://" + u[7:]
                try: http(su, {"User-Agent": "Mozilla/5.0 (research bot)"}, timeout=20); u = su
                except Exception: pass
            nu = normalize_url(u)
            if nu in seen: continue   # normalized dedupe (tracking params, trailing slash)
            seen.add(nu)
            date = it.get("date")
            dmethod = "source_stated" if date else None
            if not date:
                # deterministic safety net: X snowflake id > page metadata > Wayback
                try: date, _how = resolve_date(u); dmethod = _how or "page_metadata"
                except Exception: date = None
            if not date:
                # dates are mandatory (stance evolution needs them); quarantine for review
                qpath = os.path.join(ROOT, "ledger", "undated_quarantine.json")
                quar = json.load(open(qpath)) if os.path.exists(qpath) else []
                quar.append({"person": it["person"], "url": u, "summary": (it.get("summary") or "")[:240],
                             "skipped_on": TODAY})
                json.dump(quar, open(qpath, "w"), indent=1)
                continue
            cand = {**it, "date": date, "url": u}
            # cached page text gives the relevance rule context when a summary
            # paraphrases without conflict keywords (page_text caches by URL hash)
            try: ctx_text = page_text(u)
            except Exception: ctx_text = None
            ok, hard, soft = ev_check(cand, person_ctx, context_text=ctx_text)
            if not ok:
                # acceptance rules (validate_evidence.py): quarantine with reason
                qpath = os.path.join(ROOT, "ledger", "undated_quarantine.json")
                quar = json.load(open(qpath)) if os.path.exists(qpath) else []
                quar.append({"person": it["person"], "url": u, "summary": (it.get("summary") or "")[:240],
                             "skipped_on": TODAY, "reason": "acceptance rules: " + "; ".join(hard)})
                json.dump(quar, open(qpath, "w"), indent=1)
                continue
            if soft:  # human-review queue; item still enters the ledger
                rpath = os.path.join(ROOT, "ledger", "review_flags.json")
                rev = json.load(open(rpath)) if os.path.exists(rpath) else []
                for s in soft:
                    rev.append({"person": it["person"], "url": u, "date": date,
                                "flag": s, "summary": (it.get("summary") or "")[:200], "on": TODAY})
                json.dump(rev, open(rpath, "w"), indent=1)
            cur.append({"id": next_eid(), "person": it["person"], "date": date or None,
                        **({"date_method": dmethod} if dmethod else {}),
                        "url": u, "domain": urllib.parse.urlparse(u).netloc.replace("www.", ""),
                        "summary": (it.get("summary") or "")[:240],
                        "quote": (it.get("quote") or "")[:300] or None,
                        "dimension": it.get("dimension", "other"),
                        "source_kind": it.get("source_kind", "news"), "checked_on": TODAY})
            added += 1
        if added:
            tmp = ev_path(k) + ".tmp"; json.dump(cur, open(tmp, "w"), indent=1); os.replace(tmp, ev_path(k))
        return added

KW = re.compile(r"gaza|palestin|israel|ceasefire|genocide|\bidf\b|hamas|aipac|arms sale|west bank|rafah|two-state|zionist", re.I)

def page_text(url, cap=6000):
    import hashlib
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    cache = os.path.join(ROOT, "raw", "pages", h + ".txt")
    if os.path.exists(cache): return open(cache).read() or None
    try:
        html = http(url, {"User-Agent": "Mozilla/5.0 (research bot)"}, timeout=25)
        p = TextExtract(); p.feed(html); t = re.sub(r"\s+", " ", "".join(p.parts)).strip()
        t = t[:cap] if len(t) > 40 else ""
    except Exception:
        t = ""
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    open(cache, "w").write(t)
    return t or None

# ---------------- PASS A collectors (deterministic) ----------------
def x_timeline(handle):
    cache = os.path.join(ROOT, "raw", "x", handle.lower() + ".json")
    if os.path.exists(cache): return json.load(open(cache))
    try:
        html = http(f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}",
                    {"User-Agent": "Mozilla/5.0"}, timeout=25)
    except Exception:
        return []
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    tweets = []
    if m:
        try:
            def walk(o):
                if isinstance(o, dict):
                    tw = o.get("tweet") or o
                    if all(x in tw for x in ("full_text", "id_str")) and isinstance(tw.get("full_text"), str):
                        u = tw.get("user") or {}
                        tweets.append({"id": tw["id_str"], "text": tw["full_text"],
                                       "date": (tw.get("created_at") or "")[:100],
                                       "handle": (u.get("screen_name") or handle)})
                    for v in o.values(): walk(v)
                elif isinstance(o, list):
                    for v in o: walk(v)
            walk(json.loads(m.group(1)))
        except Exception: pass
    if not tweets:
        for fm in re.finditer(r'"full_text":"((?:[^"\\]|\\.){20,})"', html):
            txt = fm.group(1).encode().decode("unicode_escape", "ignore")
            tweets.append({"id": "", "text": txt, "date": "", "handle": handle})
    seen = set(); uniq = []
    for t in tweets:
        if t["id"] and t["id"] in seen: continue
        seen.add(t["id"]); uniq.append(t)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(uniq, open(cache, "w"), indent=1)
    return uniq

PRO_ISRAEL = re.compile(r"aipac|israel|democratic majority for israel|united democracy project|"
                        r"standwithus|christians united|zionist|hadassah|chabad|b'nai b'rith|"
                        r"american jewish committee|j street|netanyahu", re.I)
def fec_receipts(cid):
    cache = os.path.join(ROOT, "raw", "fec", cid + ".json")
    if os.path.exists(cache): return json.load(open(cache))
    recs, last_idx = [], None
    for _page in range(12):
        u = f"https://api.open.fec.gov/v1/schedules/schedule_a/?committee_id={cid}&per_page=100&api_key={fec_key()}"
        if last_idx: u += f"&last_index_number={last_idx}"
        try: d = json.loads(http(u, timeout=25))
        except Exception: break
        rs = d.get("results") or []
        recs.extend(rs)
        nxt = (d.get("pagination") or {}).get("last_index_number")
        if not rs or not nxt or nxt == last_idx: break
        last_idx = nxt
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(recs, open(cache, "w"))
    return recs

def wiki_text(name):
    slug = name.replace(" ", "_")
    cache = os.path.join(ROOT, "raw", "wiki", re.sub(r"[^A-Za-z0-9_-]", "", slug) + ".txt")
    if os.path.exists(cache): return open(cache).read() or None
    t = ""
    try:
        d = json.loads(http(f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(slug)}", timeout=20))
        if d.get("type") != "disambiguation": t = (d.get("extract") or "") + "\n"
    except Exception: pass
    try:
        html = http(f"https://en.wikipedia.org/wiki/{urllib.parse.quote(slug)}", {"User-Agent": "Mozilla/5.0"}, timeout=25)
        p = TextExtract(); p.feed(html); t += re.sub(r"\s+", " ", "".join(p.parts))[:12000]
    except Exception: pass
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    open(cache, "w").write(t[:14000])
    return (t[:14000] or None) if KW.search(t) else None

FIXED_QUERY_TEMPLATES = [
    '"{name}" gaza',
    '"{name}" israel palestine',
    '"{name}" ceasefire vote',
    '"{name}" AIPAC pro-israel funding',
]
ENRICH_QUERY_TEMPLATES = [
    '"{name}" "genocide" palestine gaza',
    '"{name}" arms sales Israel vote congress',
    '"{name}" JLM endorsement OR "Jewish Democratic Council" OR AIPAC endorsement 2026',
    '"{name}" IDF war crimes statement',
]
def fixed_search_pages(name, handle, enrich=False):
    """Run the fixed query set; return keyword-gated page snippets+texts (no LLM)."""
    templates = FIXED_QUERY_TEMPLATES + (ENRICH_QUERY_TEMPLATES if enrich else [])
    queries = [q.format(name=name) for q in templates]
    if handle:
        queries.append(f'site:x.com {handle} gaza OR palestine OR israel')
    pages, seen_urls = [], set()
    for q in queries:
        try: results = serper(q, num=8)
        except Exception as ex: log(f"    serper err {q!r}: {repr(ex)[:60]}"); continue
        hits = [r for r in results if KW.search((r.get("title") or "") + " " + (r.get("snippet") or ""))]
        fetched_here = 0
        for r in hits:
            u = r.get("link", "")
            if not u or u in seen_urls or re.search(r"(youtube|facebook|instagram)\.com", u): continue
            if u.startswith(("https://x.com/", "https://twitter.com/")) and fetched_here >= 1: continue
            t = page_text(u)
            seen_urls.add(u); fetched_here += 1
            if t and KW.search(t):
                pages.append({"url": u, "title": (r.get("title") or "")[:120], "text": t})
            if fetched_here >= 3: break
    return queries, pages

# ---------------- PASS B/C extraction prompt ----------------
PROMPT = """You extract research evidence for a stance audit on the Gaza war. Person: {name} ({party}).

Below is a dossier assembled deterministically from fixed searches (news snippets+pages), this person's recent X posts, FEC itemized receipts, campaign site text and Wikipedia text.

TASK 1 — items: list every claim/action/statement BY or ABOUT this specific person regarding Israel, Gaza, Palestine, arms sales/military aid to Israel, AIPAC or pro-Israel funding/endorsements, ceasefire votes or actions, genocide recognition, or how they frame the conflict. Rules:
- ONLY this exact person (reject same-name different people; reject generic party-platform statements unless attributed to them).
- IDENTITY FIRST: before including ANY item, confirm the source text connects the person to THIS candidate's office, jurisdiction or biography (e.g. "Oakland school board", "Berkeley", "CA-17", "candidate for"). If the source describes a different career, city, country or era than this candidate's office ({office}, {jurisdiction}), REJECT it even if the name matches exactly.
- The evidence must convey THIS person's own position, vote, statement, or funding record. Statements by others merely criticizing/mentioning them, vandalism against them, ads about them, attendance where others spoke, or "received $0 / no record" absence claims are NOT evidence — omit them.
- Do not infer a past co-signature from current caucus membership; include only if the cited page names this individual as a signatory at that date.
- url MUST be copied verbatim from the dossier — never invent or modify URLs.
- date: REQUIRED whenever the dossier or source states one — check bylines, article
  timestamps, post times shown as "(YYYY-MM-DD)" in X POSTS lines (copy that exact day),
  FEC receipt dates and visible "Posted on ..." text. Format YYYY-MM-DD / YYYY-MM / YYYY
  as stated; use null ONLY when no publication/statement date appears anywhere.
- summary: one factual line <=200 chars saying what this evidence conveys about THEIR position.
- quote: exact supporting phrase from the dossier text <=250 chars, else null.
- dimension: genocide_language | war_crimes | military_aid | aipac_funding | framing_balance | actions_votes | other.

TASK 2 — followup_queries: up to {nq} NEW Google search strings that would likely surface MISSING dimensions (e.g. did they ever say 'genocide'? which AIPAC-endorsed? arms sale votes?). Use the person's name plus district/office words to disambiguate. Empty list if dossier is sufficient or nothing more is findable.

DOSSIER:
{dossier}

Return STRICT JSON only: {{"items":[...],"followup_queries":[...]}}"""

def build_dossier(person, pages, xposts, fec_hits, site_t, wiki_t):
    parts = []
    def add(label, body, cap):
        if body: parts.append(f"### {label}\n{body[:cap]}")
    add("WEB PAGES (fixed searches)", "\n\n".join(
        f"[{i}] URL: {p['url']}\nTITLE: {p['title']}\nTEXT: {p['text'][:2500]}" for i, p in enumerate(pages)), 16000)
    add("X POSTS (recent timeline)", "\n".join(
        f"- ({t['date'][:16]}) https://x.com/{t['handle']}/status/{t['id']}: {t['text'][:280]}" for t in xposts), 4000)
    add("FEC RECEIPTS (pro-Israel regex hits)", "\n".join(
        f"- {h.get('contribution_receipt_date')} ${h.get('receipt_amount')} from {h.get('contributor_name')}" for h in fec_hits[:15]), 2000)
    add("CAMPAIGN SITE", site_t, 3000)
    add("WIKIPEDIA", wiki_t, 6000)
    d = "\n\n".join(parts)
    return d[:28000]

def norm_items(name, j):
    out = []
    for it in (j.get("items") or [])[:15]:
        if not isinstance(it, dict): continue
        dim = it.get("dimension")
        out.append({"person": name, "date": str(it.get("date") or "") or None, "url": str(it.get("url") or ""),
                    "summary": str(it.get("summary") or ""), "quote": it.get("quote"),
                    "dimension": dim if dim in ("genocide_language","war_crimes","military_aid",
                        "aipac_funding","framing_balance","actions_votes") else "other",
                    "source_kind": it.get("source_kind") or "news"})
    return out

# ---------------- person pipeline ----------------
def work(person):
    key, name, party = person["key"], person["name"], person.get("party")
    # PASS A — deterministic collection
    xposts = []
    if person.get("handle"):
        for t in x_timeline(person["handle"])[:40]:
            if KW.search(t["text"]):
                d = ""
                try: d = time.strftime("%Y-%m-%d", time.strptime(t["date"], "%a %b %d %H:%M:%S %z %Y"))
                except Exception: pass
                xposts.append({**t, "iso": d})
    fec_hits = []
    for cid in (person.get("committee_ids") or [])[:2]:
        fec_hits += [r for r in fec_receipts(cid)
                     if PRO_ISRAEL.search((r.get("contributor_name") or "") + " " + str(r.get("contributor_employer")))]
    site_t = None
    if person.get("campaign_url"):
        t = page_text(person["campaign_url"])
        if t and KW.search(t): site_t = t
    wiki_t = wiki_text(name)
    queries, pages = fixed_search_pages(name, person.get("handle"), enrich=person.get("enrich"))
    # auto-attribute X posts + FEC hits as evidence (deterministic, no LLM needed for URL/date)
    det_items = []
    for t in xposts[:12]:
        iso = t["iso"] or ""
        if not iso and t["id"]:
            try:  # regex-fallback tweets have no created_at; the snowflake id still does
                iso = time.strftime("%Y-%m-%d", time.gmtime(((int(t["id"]) >> 22) + 1288834974657) / 1000))
            except Exception: pass
        det_items.append({"person": name, "date": iso or None,
                          "url": f"https://x.com/{t['handle']}/status/{t['id']}" if t["id"] else f"https://x.com/{t['handle']}",
                          "summary": "X post: " + re.sub(r"\s+", " ", t["text"])[:200],
                          "quote": re.sub(r"\s+", " ", t["text"])[:300],
                          "dimension": "other", "source_kind": "x_post"})
    for r in fec_hits[:12]:
        first_cid = (person.get("committee_ids") or [""])[0]
        det_items.append({"person": name, "date": (r.get("contribution_receipt_date") or "")[:10] or None,
                          "url": f"https://www.fec.gov/data/receipts/?committee_id={first_cid}",
                          "summary": f"FEC receipt ${r.get('receipt_amount')} from {r.get('contributor_name')}"
                                     + (f" ({r.get('contributor_employer')})" if r.get("contributor_employer") else "")
                                     + " — pro-Israel-linked contributor",
                          "quote": None, "dimension": "aipac_funding", "source_kind": "fec_receipt"})
    pctx = person.get("ctx")
    added = add_evidence(key, det_items, pctx)

    has_content = bool(xposts or fec_hits or site_t or wiki_t or pages)
    if not has_content:
        return name, added, 0
    # PASS B — one big extraction + next-step proposals
    dossier = build_dossier(person, pages, xposts, fec_hits, site_t, wiki_t)
    office = person.get("office") or ""
    jurisdiction = next((c[2] for c in (person.get("ctx") or set()) if c[2]), "")
    j = lms_json(PROMPT.format(name=name, party=party or "NPP", nq=3, dossier=dossier,
                               office=office, jurisdiction=jurisdiction), timeout=480)
    if not j:
        # LMS down/exhausted fallback chain: leave the person pending so a resume retries
        # instead of silently marking them done with extraction-less results.
        raise RuntimeError("LMS extraction unavailable (all models failed)")
    items = norm_items(name, j)
    # keep only URLs that actually appeared in the dossier (anti-hallucination)
    valid_urls = {p["url"] for p in pages} | {f"https://x.com/{t['handle']}/status/{t['id']}" for t in xposts if t["id"]} \
                 | ({person["campaign_url"]} if person.get("campaign_url") else set()) \
                 | {f"https://en.wikipedia.org/wiki/{name.replace(' ','_')}"}
    items = [it for it in items if it["url"] in valid_urls]
    added += add_evidence(key, items, pctx)
    # PASS C — deterministic follow-ups (max 3 queries), one second extraction pass
    fups = [str(q).strip()[:120] for q in (j.get("followup_queries") or [])[:3] if str(q).strip()]
    more_pages = []
    for q in fups:
        try: results = serper(q, num=6)
        except Exception: continue
        got = 0
        for r in results:
            u = r.get("link", "")
            if not u or u in valid_urls or re.search(r"(youtube|facebook|instagram)\.com", u): continue
            if not KW.search((r.get("title") or "") + " " + (r.get("snippet") or "")): continue
            t = page_text(u)
            if t and KW.search(t): more_pages.append({"url": u, "title": (r.get("title") or "")[:120], "text": t})
            got += 1
            if got >= 2: break
    if more_pages:
        j2 = lms_json(PROMPT.format(name=name, party=party or "NPP", nq=0, office=office,
                                    jurisdiction=jurisdiction,
                                    dossier=build_dossier(person, more_pages, [], [], None, None)), timeout=480)
        if j2:
            items2 = [it for it in norm_items(name, j2) if it["url"] in {p["url"] for p in more_pages}]
            added += add_evidence(key, items2, pctx)
    return name, added, len(fups)

def _mark_done(key, person, stages):
    with _lock:
        s = load_state(); ent = s.setdefault(key, {"name": person["name"], "party": person.get("party")})
        ent.setdefault("stages", {}).update(stages)   # merge: keep earlier flags (e.g. enriched)
        ent["done_on"] = TODAY; save_state(s)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--county", default="San Francisco")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default=None)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--enrich", action="store_true",
                    help="add deep-dive query templates and re-run even if already done")
    ap.add_argument("--names", default=None,
                    help="comma-separated name substrings to restrict the pass")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    d = json.load(open(DATA))
    people = {}
    for p in d["positions"]:
        if args.county not in (p.get("counties") or []): continue
        for c in (p.get("candidates") or []):
            k = norm_name(c["name"]) + "|" + str(c.get("party"))
            ent = people.setdefault(k, {"key": k, "name": c["name"], "party": c.get("party"),
                                        "level": p["government_level"], "office": p["office"],
                                        "ctx": set(),
                                        "handle": None, "committee_ids": [], "campaign_url": None})
            ent["ctx"].add((p["government_level"], p.get("office") or "",
                            str(p.get("jurisdiction") or ""), ""))
            if c.get("x_url"): ent["handle"] = ent["handle"] or c["x_url"].rstrip("/").split("/")[-1]
            for cid in ((c.get("fec") or {}).get("committee_ids") or []):
                if cid not in ent["committee_ids"]: ent["committee_ids"].append(cid)
            ent["campaign_url"] = ent["campaign_url"] or c.get("campaign_url")
    state = load_state()
    subs = [s.strip().lower() for s in (args.names.split(",") if args.names else [])] + \
           ([args.only.lower()] if args.only else [])
    todo = [v for k, v in people.items() if not subs or any(s in v["name"].lower() for s in subs)]
    for v in todo:
        v["enrich"] = bool(args.enrich)
    pending = [v for v in todo if args.redo or (args.enrich and not state.get(v["key"], {}).get("stages", {}).get("enriched"))
               or not state.get(v["key"], {}).get("stages", {}).get("done")]
    if args.limit: pending = pending[:args.limit]
    log(f"{args.county}: {len(people)} unique people; {len(pending)} pending")

    def run_one(person):
        try:
            r = work(person)
        except Exception as e:
            log(f"  {person['name']}: FAILED {repr(e)[:120]}"); return person["name"], -1, 0
        _mark_done(person["key"], person, {"done": True, **({"enriched": True} if person.get("enrich") else {})})
        return r

    # workers<=2: 27b runs Parallel 2 in LM Studio; GPU_SLOTS caps total LMS calls at 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        for name, added, nfu in ex.map(run_one, pending):
            log(f"  {name}: +{added} items ({nfu} follow-ups)")
    total = sum(len(load_ev(k)) for k in people if os.path.exists(ev_path(k)))
    done_n = sum(1 for k in people if load_state().get(k, {}).get("stages", {}).get("done"))
    log(f"{args.county} PASS DONE — {total} evidence items across "
        f"{len([k for k in people if os.path.exists(ev_path(k))])} people; {done_n}/{len(people)} done")

if __name__ == "__main__":
    main()
