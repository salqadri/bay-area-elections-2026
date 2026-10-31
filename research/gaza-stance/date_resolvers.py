#!/usr/bin/env python3
"""date_resolvers.py — deterministic publication-date recovery for evidence URLs.

Used by gaza_research.py (at collection time) and backfill_dates.py (retrofit).
Order of trust: X/Twitter snowflake id > page metadata (og/meta/JSON-LD/time)
> Wayback snapshot metadata. Returns 'YYYY-MM-DD' | 'YYYY-MM' | 'YYYY' | None.
Never guesses from URL path numbers or prose heuristics — a wrong date is worse
than an honest null.
"""
import hashlib, json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
META_CACHE = os.path.join(ROOT, "raw", "meta")
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=_UA)
    return urllib.request.urlopen(req, timeout=timeout).read(400000).decode("utf-8", "ignore")

# ---- X / Twitter: the status id IS a snowflake containing the creation ms ----
_X_STATUS = re.compile(r"(?:x|twitter)\.com/[^/]+/status(?:es)?/(\d{15,25})", re.I)
def resolve_x(url):
    m = _X_STATUS.search(url or "")
    if not m: return None
    twid = int(m.group(1))
    # ids below the snowflake era (pre-Nov 2010) are sequential, not timestamps
    if twid < 2**35: return None
    ms = (twid >> 22) + 1288834974657
    if ms > time.time() * 1000 + 86400_000: return None   # implausible future id
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))

# ---- page metadata ----
_DATE_PATTERNS = [
    re.compile(r'''(?:article:published_time|article:modified_time|"datePublished"|"dateModified"|datePublished|itemprop="datePublished"[^>]*content)\D{0,25}(\d{4}-\d{2}-\d{2})(?:[T ]\d{2}:\d{2})?'''),
    re.compile(r'''<time[^>]+datetime=["'](\d{4}-\d{2}-\d{2})'''),
]
def _from_html(html):
    for pat in _DATE_PATTERNS:
        m = pat.search(html or "")
        if m: return m.group(1)
    return None

def resolve_meta(url, html=None):
    """Publication date from page metadata. Fetches (and caches) unless html given."""
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    cache = os.path.join(META_CACHE, h + ".html")
    if html is None:
        if os.path.exists(cache):
            html = open(cache).read()
        else:
            try: html = _get(url)
            except Exception: html = ""
            os.makedirs(META_CACHE, exist_ok=True)
            tmp = cache + ".tmp"; open(tmp, "w").write(html); os.replace(tmp, cache)
    return _from_html(html)

# ---- Wayback fallback for moved/404 pages (metadata only, not prose) ----
def resolve_wayback(url):
    try:
        q = urllib.parse.quote(url, safe="")
        avail = json.loads(_get(f"https://archive.org/wayback/available?url={q}", timeout=20))
        snap = ((avail.get("archived_snapshots") or {}).get("closest") or {}).get("url")
        if not snap: return None
        return _from_html(_get(snap, timeout=35))
    except Exception:
        return None

def resolve_date(url):
    """Best deterministic date for a URL; None when nothing supports one."""
    d = resolve_x(url)
    if d: return d, "x_snowflake"
    d = resolve_meta(url)
    if d: return d, "page_metadata"
    d = resolve_wayback(url)
    if d: return d, "wayback_first_capture"
    return None, None

if __name__ == "__main__":
    import sys
    for u in sys.argv[1:]:
        print(resolve_date(u), "<-", u[:90])
