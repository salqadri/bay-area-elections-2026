#!/usr/bin/env python3
"""validate_evidence.py — deterministic acceptance rules for Gaza evidence items.

Shared by gaza_research.py (gate at add time) and revalidation passes over the
existing ledger. Motivated by the October 8, 2026 external review: wrong-person
attribution dominated the failure modes, so identity/direct-attribution checks
come first. HARD rules quarantine automatically; SOFT rules only flag for human
review (e.g. a candidate genuinely travelling to Israel is fine).

Every quarantine entry records a reason — nothing is silently dropped.
"""
import re

# --- context needed from the dataset: person -> set of (level, office, jurisdiction) ---
LOCAL_LEVELS = {"City or town", "Education", "Special district", "County", "Judicial"}

# an item must actually concern the Israel/Gaza/Palestine conflict to be evidence
RELEVANCE = re.compile(
    r"gaza|palestin|israel|ceasefire|genocide|\bidf\b|hamas|aipac|jpac|"
    r"arms sale|west bank|rafah|two-state|zionist|anti-?semit|october 7|oct\.? ?7|"
    r"hezbollah|knesset|intifada|divest|netanyahu|block the bombs", re.I)


def normalize_url(u):
    """Canonical form for duplicate detection: lowercase, drop fragments and
    known tracking parameters, strip trailing slash."""
    u = (u or "").lower().split("#")[0]
    u = re.sub(r"[?&](utm_[^=]+|srsltid|fbclid|ref_src|ref_url|lang|m|feature|"
               r"trk[^=]*|gsrc|s)[^&]*", "", u)
    u = re.sub(r"\?&*$|\?$", "", u)
    return u.rstrip("/")


# markers that a source is about foreign or far-away politics; for LOCAL candidates
# these demand an explicit identity link before acceptance (soft flag)
FOREIGN = re.compile(
    r"\bMP\b|SNP|Westminster|\bUK Parliament\b|Knesset|\bDáil\b|Oireachtas|"
    r"New Rochelle|Madrid|Geneva|Spanish|Deputy Minister|State Secretary", re.I)

# absence-of-evidence phrasing: "no/zero contributions" is not a position
ABSENCE = re.compile(
    r"\b(zero|\$0|no)\b[^.]{0,40}\b(contribution|receipt|funding from|itemized)\b|"
    r"absence of (any )?(record|statement|position)|received no\b", re.I)

# failed extraction artifacts
BROKEN = re.compile(r"\$None|\bnan\b|could not be (retrieved|found)|extraction failed", re.I)

# bare X profile URL: cannot pin a claim to a stable dated post
BARE_X = re.compile(r"^https://x\.com/[A-Za-z0-9_]+/?$")

# non-specific citation targets: site root or month-archive pages
ROOT_URL = re.compile(r"^https://[^/]+/?$|/\d{4}/\d{2}/?\?m=0$|^https://[^/]+$")

# third-party speech ABOUT the candidate rather BY them (soft flag)
ABOUT_ONLY = re.compile(
    r"was (criticized|targeted|vandalized|called)|opponent alleges|"
    r"ads targeting|named among|framed as|listed as a member", re.I)

# co-signature claims inferred from roster membership (soft flag; hard if the
# cited page's roster era conflicts with the claimed date — handled by review)
COSIGN = re.compile(r"co-signed|joint statement.{0,60}member|as a member of the .{0,40}caucus", re.I)


def check(item, person_ctx=None, context_text=None):
    """Return (ok, hard_reasons, soft_flags). person_ctx: iterable of
    (level, office, jurisdiction, county) tuples for this candidate.
    context_text: cached source-page text; a paraphrased summary that misses
    the relevance keywords is kept with a review flag when the page itself
    is about the conflict."""
    hard, soft = [], []
    url = item.get("url") or ""
    blob = f"{item.get('summary') or ''} {item.get('quote') or ''}"

    if not url.startswith("https://"):
        hard.append("URL is not https")
    if BARE_X.match(url):
        hard.append("bare X profile URL: claim cannot be pinned to a stable dated post")
    elif "x.com" in url and "/status/" not in url and "?" in url.split("x.com/")[-1]:
        soft.append("X URL with query parameters; verify it resolves to the cited post")
    if ROOT_URL.search(url):
        hard.append("citation target is a site root or month archive, not a specific document")
    date = str(item.get("date") or "")
    if not re.match(r"^\d{4}(-\d{2})?(-\d{2})?$", date):
        hard.append("missing or malformed date")
    elif date > "2026-10-31" or date < "1990":
        hard.append(f"implausible date {date}")
    if BROKEN.search(blob):
        hard.append("failed-extraction artifact ($None/nan/could-not-retrieve)")
    if not RELEVANCE.search(blob):
        if context_text and RELEVANCE.search(context_text):
            soft.append("relevance unclear from summary; source page is conflict-related — verify the claim's context")
        else:
            hard.append("relevance: item states no position or record on the Israel/Gaza/Palestine conflict")
    if ABSENCE.search(item.get("summary") or ""):
        hard.append("absence-of-evidence phrasing is not a position")

    levels = {c[0] for c in (person_ctx or set())}
    if levels and levels <= LOCAL_LEVELS:
        m = FOREIGN.search(blob)
        if m:
            soft.append(f"local candidate but source mentions foreign politics ({m.group(0)}): "
                        "verify the person is explicitly linked to this office/location")
    if ABOUT_ONLY.search(item.get("summary") or ""):
        soft.append("third-party speech about (not by) the candidate; keep only if it conveys "
                    "the candidate's own position or verified funding/action record")
    if COSIGN.search(blob):
        soft.append("co-signature inferred from caucus membership: confirm the cited page names "
                    "this individual AND that its roster era matches the claimed date")
    return (not hard), hard, soft


def person_contexts(dataset):
    """name -> set of (level, office, jurisdiction, county) across all positions."""
    ctx = {}
    for p in dataset["positions"]:
        jur = str(p.get("jurisdiction") or "")
        for c in (p.get("candidates") or []):
            for co in (p.get("counties") or []):
                ctx.setdefault(c["name"], set()).add(
                    (p["government_level"], p.get("office") or "", jur, co))
    return ctx
