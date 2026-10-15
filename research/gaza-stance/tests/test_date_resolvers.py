#!/usr/bin/env python3
"""Offline tests for date_resolvers (no network): snowflake decoding, metadata
patterns, and the trust order. Run: python3 tests/test_date_resolvers.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from date_resolvers import resolve_x, _from_html, resolve_meta

fails = []
def eq(got, want, label):
    if got != want: fails.append(f"{label}: got {got!r} want {want!r}")

# --- X snowflake ids carry the creation timestamp -------------------------
# 2010889591281025119 -> 2026-01-13 (verified against the live post)
eq(resolve_x("https://x.com/abc7newsbayarea/status/2010889591281025119"), "2026-01-13", "snowflake wiener")
eq(resolve_x("https://twitter.com/foo/statuses/2010889591281025119"), "2026-01-13", "legacy host+statuses")
# pre-snowflake sequential ids must NOT be decoded into a bogus 1970 date
eq(resolve_x("https://x.com/foo/status/1234567890"), None, "pre-snowflake id -> null")
# implausible future id is rejected rather than trusted
future = ((int(time.time() * 1000) + 10**12 - 1288834974657) << 22)
eq(resolve_x(f"https://x.com/foo/status/{future}"), None, "future id -> null")
for bad in ["https://x.com/someuser", "https://example.com/a/123", "", None]:
    eq(resolve_x(bad), None, f"non-status url {bad!r}")

# --- page metadata patterns ----------------------------------------------
HTML_OG = '<meta property="article:published_time" content="2026-01-12T21:28:05+00:00"/>'
eq(_from_html(HTML_OG), "2026-01-12", "og published_time")
eq(_from_html('<script>{"datePublished":"2024-05-16T09:00:00-07:00"}</script>'), "2024-05-16", "jsonld datePublished")
eq(_from_html('<time datetime="2026-07-22">Jul 22</time>'), "2026-07-22", "<time> element")
# modified_time must not beat an earlier published_time (publication is the fact we want)
eq(_from_html('<meta property="article:published_time" content="2025-03-01T00:00:00Z"/>'
              '<meta property="article:modified_time" content="2026-09-01T00:00:00Z"/>'), "2025-03-01", "published beats modified")
# no date anywhere -> None (never guess from URL path numbers or prose)
eq(_from_html("<html><body>no dates here, see 2019 and route 101</body></html>"), None, "no false positive")
eq(_from_html(""), None, "empty html")

# --- resolve_meta uses the cache when present (offline determinism) -------
import date_resolvers as dr, hashlib, tempfile
tmp = tempfile.mkdtemp(); dr.META_CACHE = tmp
u = "https://example.test/article"
open(os.path.join(tmp, hashlib.sha1(u.encode()).hexdigest()[:16] + ".html"), "w").write(HTML_OG)
eq(dr.resolve_meta(u), "2026-01-12", "cached html used without network")

# --- resolve_date trust order: X id wins over page metadata --------------
calls = []
dr.resolve_x_real = dr.resolve_x
def fake_meta(url, html=None): calls.append("meta"); return "2030-01-01"
orig_meta = dr.resolve_meta; dr.resolve_meta = fake_meta
eq(dr.resolve_date("https://x.com/a/status/2010889591281025119"), ("2026-01-13", "x_snowflake"), "snowflake first")
eq(calls, [], "metadata not fetched when snowflake resolves")
dr.resolve_meta = orig_meta

print("FAIL" if fails else "PASS", f"{len(fails)} failure(s)")
for f in fails: print("  -", f)
sys.exit(1 if fails else 0)
