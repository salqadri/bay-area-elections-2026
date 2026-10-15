#!/usr/bin/env python3
"""xhunt2.py — web-search re-sweep: X accounts for missed candidates + campaign sites for all.

Why this exists: grok x_search only sees X's indexed posts; small/zero-post
campaign accounts are invisible there. This stage uses Serper (Google) which
indexes public profile pages and campaign sites, then verifies any x.com hit
against live profile metadata via fxtwitter (no auth), adjudicated by the LM
Studio jev model with qwen3.8-flash-next (low reasoning) as escalation.

Phases:
  A  candidates still missing x_url -> combined query finds X profiles AND
     campaign domains in one shot; follow-up query when needed
  B  all remaining candidates -> campaign website discovery only

Resumable via state2.json. Output: results_web_all.json (merge-compatible,
adds optional campaign_url + campaign evidence fields).

Usage: python3 xhunt2.py --limit 6   # smoke test
       python3 xhunt2.py --workers 4 # full run
"""
import argparse, concurrent.futures, glob, json, os, re, threading, time
import urllib.request, urllib.error
from html.parser import HTMLParser

WORK = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(WORK, "state2.json")
OUT_PATH = os.path.join(WORK, "results_web_all.json")
SERPER_KEY_FILE = os.environ.get("SERPER_KEY_FILE", os.path.expanduser("~/.config/gaza-research/serper_key"))
LMS = os.environ.get("GAZA_LMS_URL", "http://127.0.0.1:11434/v1/chat/completions")
JEV_MODEL = "jev-style-qwen3.5-2b-decision"
FLASH_MODEL = "qwen3.8-flash-next"

DOMAIN_DENY = re.compile(
    r"(^|\.)(x\.com|twitter\.com|ballotpedia\.org|wikipedia\.org|wikimedia\.org|"
    r"facebook\.com|instagram\.com|youtube\.com|linkedin\.com|tiktok\.com|truthsocial\.com|threads\.net|bsky\.app|"
    r"actblue\.com|winred\.com|secure2\.vote\.gov|vote\.gov|sos\.ca\.gov|"
    r"sfgate\.com|mercurynews\.com|eastbaytimes\.com|sfchronicle\.com|nytimes\.com|washingtonpost\.com|"
    r"cnn\.com|foxnews\.com|abc7(?:news)?\.(com|us)|kqed\.org|calmatters\.org|berkeleyside\.org|sfstandard\.com|"
    r"baycitynews\.com|patch\.com|maplight\.org|opensecrets\.org|fec\.gov|sourcewatch\.org|"
    r"amazon\.com|census\.gov|usa\.gov|ca\.gov|congress\.gov)($|/)", re.I)

_log_lock = threading.Lock()
def log(msg):
    with _log_lock: print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def http(url, headers=None, timeout=30, attempts=2, data=None):
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, data=data, headers=headers or {})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode(errors="replace")
        except Exception as e:
            last = repr(e); time.sleep(2 * (i + 1))
    raise RuntimeError(last)

def serper(q, num=8):
    key = open(SERPER_KEY_FILE).read().strip()
    body = json.dumps({"q": q, "num": num}).encode()
    d = json.loads(http("https://google.serper.dev/search",
        {"X-API-KEY": key, "Content-Type": "application/json"}, data=body))
    return d.get("organic", []) or []

def fx_profile(handle):
    try:
        d = json.loads(http(f"https://api.fxtwitter.com/{handle}", timeout=20))
        u = d.get("user") or {}
        if not u.get("screen_name"): return None
        return {"name": u.get("name", ""), "description": u.get("description", ""),
                "location": u.get("location", ""), "followers": u.get("followers")}
    except Exception:
        return None

def call_lms(model, prompt, timeout=180, effort=None):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    if effort: payload["reasoning_effort"] = effort
    r = json.loads(http(LMS, {"Content-Type": "application/json"}, timeout=timeout,
                        data=json.dumps(payload).encode()))
    return r["choices"][0]["message"].get("content") or ""

def extract_json(text):
    text = re.sub(r"```(json)?", "", text or "")
    for pat in (r"\[[\s\S]*\]", r"\{[\s\S]*\}"):
        m = re.search(pat, text)
        if m:
            try: return json.loads(m.group(0))
            except Exception: pass
    return None

def norm_name(s): return re.sub(r"[^a-z ]", "", (s or "").lower().replace(".", " ").replace("-", " "))
def key_of(n, p): return norm_name(n) + "|" + str(p)

class TextExtract(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,t,a):
        if t in ("script","style"): self.skip+=1
    def handle_endtag(self,t):
        if t in ("script","style") and self.skip: self.skip-=1
    def handle_data(self,d):
        if not self.skip and len("".join(self.parts))<4000: self.parts.append(d)

def page_text(url):
    try:
        html = http(url, {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}, timeout=25)
        p = TextExtract(); p.feed(html)
        return re.sub(r"\s+", " ", " ".join(p.parts))[:3500]
    except Exception:
        return ""

def office_hint(c):
    m = re.search(r"(United States Representative|State Senate|State Assembly|Governor|"
                  r"Board of Supervisors|Superior Court|Sheriff|Assessor|District Attorney|"
                  r"Treasurer|Recorder|School Board|Trustee|Mayor|City Council|Water District|"
                  r"Fire|Sanitary|Irrigation|Library)", c["offices"], re.I)
    return m.group(1) if m else (c["jurisdictions"].split(";")[0][:40])

def jev_x(cand, prof):
    prompt = ("Decide whether this X account belongs to the named 2026 ballot candidate.\n"
        f"CANDIDATE: {cand['name']} ({cand.get('party')}), running for: {cand['offices']}, "
        f"jurisdiction: {cand['jurisdictions']}\n"
        f"ACCOUNT NAME: {prof['name']}\nBIO: {(prof['description'] or 'none')[:300]}\n"
        f"LOCATION: {prof.get('location') or 'none'}\n"
        "If name+bio explicitly match this person and office -> accept. If it contradicts "
        "(different office/place/famous same-name person) -> reject. Otherwise uncertain.\n"
        'Answer ONLY JSON: {"verdict":"accept|reject|uncertain"}')
    for _ in range(2):
        out = call_lms(JEV_MODEL, prompt, timeout=120)
        v = str((extract_json(out) or {}).get("verdict", "")).lower()
        if v in ("accept","reject","uncertain"): return v
    return "uncertain"

def flash_x(cand, handle, prof, first):
    prompt = (f"You adjudicate one identity match for election reference data. Use ONLY the evidence given.\n"
        f"CANDIDATE: {cand['name']} ({cand.get('party') or 'NPP'}), running for: {cand['offices']}, "
        f"jurisdiction: {cand['jurisdictions']}, counties: {cand['counties']}\n"
        f"CLAIMED X ACCOUNT: https://x.com/{handle} — name: {prof['name']!r}; bio: {(prof['description'] or '')[:300]!r}; location: {prof.get('location')!r}\n"
        f"FIRST-PASS VERDICT: {first}\n"
        "Accept only if evidence ties this account to THIS person AND office. Reject same-name "
        "collisions, parody/fan accounts, or a different officeholder with the same name. Indirect "
        "but consistent campaign-style evidence -> probable.\n"
        'Return STRICT JSON only: {"verdict":"accept|probable|reject","confidence":"verified|probable|null","reason":"<=200 chars"}')
    j = extract_json(call_lms(FLASH_MODEL, prompt, timeout=240, effort="low")) or {}
    v = str(j.get("verdict","")).lower()
    if v not in ("accept","probable","reject"): return None
    conf = "verified" if v=="accept" else "probable"
    return {"confidence": conf, "reason": str(j.get("reason",""))[:250]}

def flash_site(cand, url, title, snippet, body):
    prompt = (f"Does this website belong to the specific 2026 ballot candidate below as their official "
        f"campaign/office site? Use ONLY evidence given.\n"
        f"CANDIDATE: {cand['name']} ({cand.get('party') or 'NPP'}), running for: {cand['offices']}, "
        f"jurisdiction: {cand['jurisdictions']}\nSITE URL: {url}\nSEARCH TITLE: {title[:150]!r}\n"
        f"SNIPPET: {snippet[:200]!r}\nHOMEPAGE TEXT (truncated): {body[:900]!r}\n"
        "Accept only if the page is clearly this person's own campaign/office site (name + office/city "
        "present). Reject party pages, news articles, opponent sites, generic domains parked for sale.\n"
        'Return STRICT JSON only: {"verdict":"accept|reject","reason":"<=160 chars"}')
    j = extract_json(call_lms(FLASH_MODEL, prompt, timeout=240, effort="low")) or {}
    return str(j.get("verdict","")).lower() == "accept", str(j.get("reason",""))[:200]

# ------------------------------------------------------------------ state
_lock = threading.Lock()
def load_state():
    if os.path.exists(STATE_PATH): return json.load(open(STATE_PATH))
    return {"done": {}}   # key -> row dict (may have x_url and/or campaign_url null)

def save_state(s):
    tmp = STATE_PATH + ".tmp"
    with open(tmp,"w") as f: json.dump(s,f)
    os.replace(tmp, STATE_PATH)

def flush(s):
    rows=[v for v in s["done"].values() if isinstance(v,dict)]
    tmp=OUT_PATH+".tmp"
    with open(tmp,"w") as f: json.dump(rows,f,indent=1)
    os.replace(tmp,OUT_PATH)
    return len(rows)

# ------------------------------------------------------------------ per-candidate work
def build_row(cand):
    return {"name": cand["name"], "party": cand.get("party"), "contest_ids": cand["contest_ids"],
            "x_url": None, "confidence": None, "evidence_url": None, "evidence_quote": "",
            "method": "web", "checked_on": time.strftime("%Y-%m-%d"),
            "campaign_url": None, "campaign_evidence_url": None, "campaign_evidence_quote": ""}

def find_x(cand, taken_handles):
    hint = office_hint(cand).lower()
    short = ("congress" if "united states representative" in hint else
             "senate" if "senate" in hint else
             "assembly" if "assembly" in hint else
             cand["counties"].split(",")[0].strip())
    queries = [f'x.com "{cand["name"]}"',
               f'site:x.com "{cand["name"]}" {short}',
               f'"{cand["name"]}" twitter OR x.com {short} candidate']
    handles, seen_h = [], set()
    for q in queries:
        try: results = serper(q)
        except Exception: continue
        for r in results:
            m = re.match(r"https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/?$", r.get("link",""))
            if not m: continue
            h = m.group(1)
            if h.lower() in ("home","search","hashtag","intent","share","status") or h.lower() in seen_h: continue
            if h.lower() in taken_handles: continue
            seen_h.add(h.lower()); handles.append((h, r))
        if any(h.lower() not in taken_handles for h, _ in handles): break
    for h, r in handles[:3]:
        prof = fx_profile(h)
        if not prof:
            prof = {"name": re.sub(r"\s*/\s*X$","",r.get("title","")), "description": r.get("snippet",""), "location": ""}
        v = jev_x(cand, prof)
        if v == "accept":
            return h, "verified", f"https://x.com/{h}", f"Name: {prof['name']} | Bio: {prof['description'][:150]}"
        adj = flash_x(cand, h, prof, v)
        if adj:
            return h, adj["confidence"], f"https://x.com/{h}", (f"Name: {prof['name']} | Bio: {prof['description'][:120]} | {adj['reason']}")
    return None

def find_site(cand, x_results=None):
    cands = []
    for r in (x_results or []) + serper(f'"{cand["name"]}" {office_hint(cand)} 2026 official campaign website', num=8):
        link = r.get("link","")
        m = re.match(r"https?://([^/]+)(/.*)?$", link)
        if not m: continue
        dom = m.group(1).lower()
        if dom.startswith(("www.","m.")): dom = dom[4:] if dom.startswith("www.") else dom[2:]
        if DOMAIN_DENY.search(dom): continue
        blob = (r.get("title","") + " " + r.get("snippet","")).lower()
        surname = norm_name(cand["name"]).split()[-1]
        score = 2 if surname in blob else 0
        score += sum(1 for w in ("for congress","for assembly","for senate","vote ","elect ","campaign","committee to elect") if w in blob)
        if score >= 2: cands.append((score, link, r))
    seen=set(); out=[]
    for s,l,r in sorted(cands,key=lambda t:-t[0]):
        d=re.sub(r"^https?://(www\.)?","",l).split("/")[0].lower()
        if d in seen: continue
        seen.add(d); out.append((s,l,r))
    surname = norm_name(cand["name"]).split()[-1]
    for score, link, r in out[:2]:
        body = page_text(link)
        dom = re.sub(r"^https?://(www\.)?","",link).split("/")[0].lower()
        # self-evident only when the DOMAIN itself is candidate-branded + campaign wording present
        strong = surname.lower() in dom.split(".")[0] and bool(body) and re.search(
            r"(for congress|for assembly|for senate|campaign|vote for|elect |committee to elect|"
            r"board of supervisors|school (board|district)|city council)", body, re.I)
        if strong:
            return link, f"{r.get('title','')[:80]} | {body[:150]}"
        ok, why = flash_site(cand, link, r.get("title",""), r.get("snippet",""), body)
        if ok:
            return link, f"flash-adjudicated: {why}"
    return None

def work(cand, need_x, taken_handles):
    row = build_row(cand)
    try:
        xres = serper(f'x.com "{cand["name"]}" {office_hint(cand)}') if need_x else []
        if need_x:
            hit = find_x(cand, taken_handles)
            if hit:
                h, conf, ev_url, quote = hit
                row.update(x_url=f"https://x.com/{h}", confidence=conf, evidence_url=ev_url,
                           evidence_quote=quote[:400], method="serper+fxtwitter")
        site = find_site(cand, xres if need_x else None)
        if site:
            url, quote = site
            row.update(campaign_url=url, campaign_evidence_url=url, campaign_evidence_quote=quote[:300])
    except Exception as e:
        log(f"  ERROR {cand['name']}: {e}")
        return None   # leave unresolved for retry
    return row

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="comma-separated name substrings (smoke test)")
    args = ap.parse_args()

    state = load_state()
    # candidates + who already has an x_url anywhere
    all_cands, have_x_handles, have_x_people = {}, set(), set()
    for path in sorted(glob.glob(os.path.join(WORK,"batch_*.json"))):
        for c in json.load(open(path)):
            all_cands.setdefault(key_of(c["name"],c.get("party")), c)
    for path in glob.glob(os.path.join(WORK,"results_batch_*.json")) + [os.path.join(WORK,"results_script_all.json")]:
        if not os.path.exists(path): continue
        try:
            for r in json.load(open(path)):
                if r.get("x_url"):
                    have_x_handles.add(r["x_url"].rstrip("/").split("/")[-1].lower())
                    have_x_people.add(key_of(r["name"], r.get("party")))
        except Exception: pass

    todo=[]
    for k,c in all_cands.items():
        if args.only and not any(s.lower() in c["name"].lower() for s in args.only.split(",")): continue
        prev = state["done"].get(k)
        need_x = k not in have_x_people and not (isinstance(prev,dict) and prev.get("x_url"))
        need_site = not (isinstance(prev,dict) and "campaign_url" in prev)
        if not need_x and not need_site: continue
        todo.append((k,c,need_x))
    if args.limit: todo = todo[:args.limit]
    log(f"{len(todo)} candidates queued ({sum(1 for _,_,n in todo if n)} also need X search)")

    taken_handles = set(have_x_handles)
    t0=time.time(); done=found_x=found_site=err=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs={ex.submit(work,c,n,taken_handles):(k,c) for k,c,n in todo}
        for fut in concurrent.futures.as_completed(futs):
            k,c = futs[fut]; row=fut.result()
            with _lock:
                if row is None: err+=1
                else:
                    state["done"][k]=row; save_state(state); done+=1
                    if row["x_url"]: found_x+=1; taken_handles.add(row["x_url"].split("/")[-1].lower())
                    if row["campaign_url"]: found_site+=1
            flush(state)
            if done % 25 == 0:
                log(f"progress {done}/{len(todo)} | +{found_x} X, +{found_site} sites, {err} errors | {(time.time()-t0)/60:.1f} min")
    n=flush(state)
    log(f"DONE: {done} processed (+{found_x} new X handles, +{found_site} campaign sites), {err} errors; rows={n}; {(time.time()-t0)/60:.1f} min")

if __name__ == "__main__":
    main()
