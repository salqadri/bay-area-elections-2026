#!/usr/bin/env python3
"""California Secretary of State (CAL-ACCESS) campaign-finance layer.

Subcommands:
  download  Fetch https://campaignfinance.cdn.sos.ca.gov/dbwebexport.zip into
            .research/ca-finance/ and unzip the CalAccess/DATA tables there.
            Skips when a fresh copy already exists (--force overrides). The zip,
            extracted TSVs and run state all live under ignored paths.
  build     Parse the CAL-ACCESS tables into a dated derived snapshot (JSON) for
            every California statewide / State Senate / Assembly / Board of
            Equalization candidacy in the dataset: controlled-committee total
            cash receipts since January 1, 2025 and independent-expenditure
            aggregates by spender. Records run timestamps in
            .research/ca-finance/run-state.json.
  attach    Write the derived snapshot into the dataset under candidate
            ca_finance / ca_independent_expenditures with shared
            ca_finance_settings, ca_ie_finance and ca_ie_spenders registries
            (FEC-shaped), update coverage metrics and optionally bump
            election.publication_version.

Receipts follow Form 460 summary line 13 Column A summed across each controlled
committee's statements in the window (amendments supersede); independent
expenditures follow Schedule E rows coded IND with a support/oppose code —
contributions and late 24-/48-hour notices stay out, mirroring how the federal
FEC layer excludes notices and memo entries. Amounts are reported dollars to
cent precision; null means no published total, never zero.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
import urllib.request
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "2026-11-03_Bay_Area_Elections.json"
WORK = ROOT / ".research" / "ca-finance"
ZIP_PATH = WORK / "dbwebexport.zip"
DATA_DIR = WORK / "CalAccess" / "DATA"
STATE_PATH = WORK / "run-state.json"
DERIVED_DEFAULT = WORK / "derived-ca-finance.json"
SOURCE_URL = "https://campaignfinance.cdn.sos.ca.gov/dbwebexport.zip"
SOURCE_PAGE = ("https://www.sos.ca.gov/campaign-lobbying/helpful-resources/"
               "raw-data-campaign-finance-and-lobbying-activity")
COMMITTEE_URL = "https://cal-access.sos.ca.gov/Campaign/Committee/Details.aspx?ID={}"

csv.field_size_limit(10 ** 8)

STATEWIDE_OFFICES = {
    "GOV": "Governor", "LTG": "Lieutenant Governor", "SOS": "Secretary of State",
    "CON": "Controller", "TRE": "Treasurer", "ATT": "Attorney General",
    "INS": "Insurance Commissioner", "SUP": "Superintendent of Public Instruction",
}
LEGISLATIVE_OFFICES = {"ASM": "State Assembly", "SEN": "State Senate", "BOE": "Board of Equalization"}
ALL_OFFICES = set(STATEWIDE_OFFICES) | set(LEGISLATIVE_OFFICES)
CYCLE_START = dt.date(2025, 1, 1)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(state):
    WORK.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=1) + "\n")


# ---------------------------------------------------------------- download

def cmd_download(args):
    state = load_state()
    # The CDN does not answer HEAD reliably; a 1-byte ranged GET returns both headers.
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-0"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (fixed https URL)
        last_modified = resp.headers.get("Last-Modified", "")
        content_range = resp.headers.get("Content-Range") or ""
        size = int(content_range.rsplit("/", 1)[-1]) if "/" in content_range else \
            int(resp.headers.get("Content-Length") or 0)
    fresh = (ZIP_PATH.exists() and state.get("source_last_modified") == last_modified
             and ZIP_PATH.stat().st_size == size and not args.force)
    if fresh:
        print(f"Up to date ({last_modified}); use --force to re-download.")
        return
    WORK.mkdir(parents=True, exist_ok=True)
    part = ZIP_PATH.with_suffix(".zip.part")
    print(f"Downloading {SOURCE_URL} ...")
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=120) as resp, part.open("wb") as out:  # noqa: S310
        for chunk in iter(lambda: resp.read(1 << 22), b""):
            out.write(chunk)
            digest.update(chunk)
    part.replace(ZIP_PATH)
    print("Unzipping CAL-ACCESS tables ...")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
        bad = [n for n in names if n.startswith(("/", "..")) or "/../" in f"/{n}"]
        if bad:
            raise SystemExit(f"Refusing unsafe archive entries: {bad[:3]}")
        zf.extractall(WORK, members=[n for n in names if n.startswith("CalAccess/DATA/")])
    state.update({"source_url": SOURCE_URL, "source_page": SOURCE_PAGE,
                  "downloaded_at": now_utc(), "source_last_modified": last_modified,
                  "zip_bytes": size, "zip_sha256": digest.hexdigest()})
    save_state(state)
    print(f"Done: {DATA_DIR} (Last-Modified {last_modified}, sha256 {digest.hexdigest()[:16]}...)")


# ---------------------------------------------------------------- helpers

def read_tsv(name):
    with open(DATA_DIR / name, newline="", encoding="latin-1") as fh:
        yield from csv.DictReader(fh, delimiter="\t")


def parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    date_part = value.split(" ")[0]
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    return None


def money(value):
    value = (value or "").strip().replace(",", "")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


STOP_TOKENS = {"FOR", "THE", "OF", "AND", "COMMITTEE", "INC", "LLC", "SR", "JR", "II", "III", "IV"}


def name_tokens(*parts):
    text = " ".join((p or "") for p in parts).upper()
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    return [t for t in text.split() if len(t) > 1 and t not in STOP_TOKENS]


NICKNAME_GROUPS = [
    {"STEVE", "STEVEN", "STEPHEN", "STEVIE"},
    {"BOB", "ROBERT", "ROBBIE"},
    {"BILL", "WILLIAM", "WILLY"},
    {"JIM", "JAMES", "JAMIE"},
    {"MIKE", "MICHAEL", "MICK"},
    {"DAN", "DANIEL"},
    {"DAVE", "DAVID"},
    {"BOBBI", "BARBARA"},
    {"LIZ", "ELIZABETH", "BETSY"},
    {"KATE", "KATHERINE", "KATHLEEN", "CATHERINE"},
    {"TONY", "ANTHONY"},
    {"NICK", "NICOLAS", "NICHOLAS"},
    {"CHRIS", "CHRISTOPHER", "CHRISTINE"},
]
NICKNAME_CANON = {}
for _group in NICKNAME_GROUPS:
    for _token in _group:
        NICKNAME_CANON[_token] = frozenset(_group)


def token_match(a, b):
    if a == b:
        return True
    group_a = NICKNAME_CANON.get(a)
    if group_a and b in group_a:
        return True
    shorter, longer = sorted((a, b), key=len)
    return len(shorter) >= 4 and longer.startswith(shorter)


def candidate_matches(dataset_name, cal_parts):
    """Match a dataset ballot name against CAL-ACCESS CAND_NAML/CAND_NAMF.

    Cover rows store the surname first; detail rows are free text often written
    First Last. Surnames may span tokens (hyphenated names), so try one- and
    two-token surname variants from each end, then require a given-name overlap."""
    ds = name_tokens(dataset_name)
    cal = name_tokens(*cal_parts)
    if not ds or not cal:
        return False

    def surname_variants(tokens):
        out = {tokens[0], tokens[-1]}
        if len(tokens) >= 3:
            out.add(" ".join(tokens[:2]))
            out.add(" ".join(tokens[-2:]))
        return out

    matched = None
    for sd in surname_variants(ds):
        words_d = sd.split()
        for sc in surname_variants(cal):
            words_c = sc.split()
            if len(words_d) == len(words_c) and all(token_match(x, y) for x, y in zip(words_d, words_c)):
                matched = (words_d, words_c)
                break
        if matched:
            break
    if not matched:
        return False
    given_ds = set(ds) - set(matched[0])
    given_cal = set(cal) - set(matched[1])
    if not given_ds or not given_cal:
        return True
    return any(token_match(a, b) for a in given_cal for b in given_ds)


def contest_key(position):
    """Return (office_cd, district_int_or_None) for a California state contest.

    Jurisdictions in the dataset read 'California', 'California State Senate',
    'California State Assembly' and 'California State Board of Equalization';
    judicial contests are excluded by government_level."""
    if position.get("government_level") != "State":
        return None
    jurisdiction = (position.get("jurisdiction") or "").strip()
    if not jurisdiction.startswith("California"):
        return None
    office = position["office"]
    seat = position.get("district_or_seat") or ""
    if position.get("office_category") in ("Statewide executive", "Statewide education"):
        for code, label in STATEWIDE_OFFICES.items():
            if office == label:
                return (code, None)
        return None
    match = re.match(r"^(AD|SD)-(\d+)$", seat)
    if match:
        return ({"AD": "ASM", "SD": "SEN"}[match.group(1)], int(match.group(2)))
    if position.get("office_category") == "Board of Equalization":
        match = re.match(r"^District (\d+)$", seat)
        if match:
            return ("BOE", int(match.group(1)))
    return None


def dataset_candidacies(data):
    """Yield (position, candidate, office_cd, district_int) for CA state candidacies."""
    for position in data["positions"]:
        key = contest_key(position)
        if not key:
            continue
        office_cd, district = key
        for roster in ("candidates", "filed_candidates_not_confirmed_on_ballot"):
            for candidate in (position.get(roster) or []):
                yield position, candidate, office_cd, district


def row_district(row):
    raw = (row.get("DIST_NO") or "").strip()
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


# ---------------------------------------------------------------- build

def cmd_build(args):
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    wanted = {}  # (office_cd, district) -> [(position_id, candidate_name)]
    for position, candidate, office_cd, district in dataset_candidacies(data):
        wanted.setdefault((office_cd, district), []).append((position["id"], candidate["name"]))

    def match_row(row):
        """Return the single (position_id, cand_name) a row's CAND name matches, or None."""
        office_cd = (row.get("OFFICE_CD") or "").strip()
        if office_cd not in ALL_OFFICES:
            return None
        district = None if office_cd in STATEWIDE_OFFICES else row_district(row)
        cal_name = (row.get("CAND_NAML") or "", row.get("CAND_NAMF") or "")
        matched = [m for m in wanted.get((office_cd, district), []) if candidate_matches(m[1], cal_name)]
        return matched[0] if len(matched) == 1 else None

    # Pass 1: candidacy F460 cover statements since the cycle start -> seed committees.
    seed_committees = set()
    committees_by_key = {}   # (office_cd, district, position_id, name) -> set of committee ids
    for row in read_tsv("CVR_CAMPAIGN_DISCLOSURE_CD.TSV"):
        if (row.get("FORM_TYPE") or "").strip() != "F460":
            continue
        rpt_date = parse_date(row.get("RPT_DATE"))
        if not rpt_date or rpt_date < CYCLE_START:
            continue
        matched = match_row(row)
        committee = (row.get("FILER_ID") or "").strip()
        if not matched or not committee:
            continue  # ambiguous, unmatched or unnamed — never guess
        office_cd = (row.get("OFFICE_CD") or "").strip()
        district = None if office_cd in STATEWIDE_OFFICES else row_district(row)
        committees_by_key.setdefault((office_cd, district) + matched, set()).add(committee)
        seed_committees.add(committee)

    # Pass 2: expand through active candidate-controlled-committee links (type 12011).
    link_pairs = []
    for row in read_tsv("FILER_LINKS_CD.TSV"):
        if row.get("LINK_TYPE") != "12011" or (row.get("ACTIVE_FLG") or "").strip().upper() != "Y":
            continue
        link_pairs.append((row["FILER_ID_A"].strip(), row["FILER_ID_B"].strip()))
    controlled = set(seed_committees)
    for _ in range(4):  # links pair candidates with committees; a small closure suffices
        changed = False
        for a, b in link_pairs:
            if (b in controlled and a not in controlled) or (a in controlled and b not in controlled):
                controlled.add(a); controlled.add(b); changed = True
        if not changed:
            break

    # Pass 3: every F460 statement filed by a controlled committee since the cycle start.
    filings = {}  # (filing_id, amend) -> (committee, from_date, thru_date)
    for row in read_tsv("CVR_CAMPAIGN_DISCLOSURE_CD.TSV"):
        committee = (row.get("FILER_ID") or "").strip()
        if committee not in controlled or (row.get("FORM_TYPE") or "").strip() != "F460":
            continue
        rpt_date = parse_date(row.get("RPT_DATE"))
        if not rpt_date or rpt_date < CYCLE_START:
            continue
        filings[(row["FILING_ID"], row["AMEND_ID"])] = (
            committee, parse_date(row.get("FROM_DATE")), parse_date(row.get("THRU_DATE")))

    # Pass 4: F460 summary line 13 Column A (cash receipts this period). The highest
    # AMEND_ID per filing supersedes; statement periods are contiguous so the sum of
    # in-window periods is the cycle total. Periods opening before the window are
    # excluded rather than split (they would overstate the 2025-onward coverage).
    latest = {}   # committee -> filing_id -> (amend, amount_a)
    for row in read_tsv("SMRY_CD.TSV"):
        key = (row["FILING_ID"], row["AMEND_ID"])
        meta = filings.get(key)
        if not meta or row.get("FORM_TYPE") != "F460" or row.get("LINE_ITEM") != "13":
            continue
        committee, from_date, _thru = meta
        if from_date and from_date < CYCLE_START:
            continue  # cannot split a pre-cycle period; excluded from the sum
        bucket = latest.setdefault(committee, {})
        amend = int(row["AMEND_ID"] or 0)
        prev = bucket.get(row["FILING_ID"])
        if prev is None or amend > prev[0]:
            bucket[row["FILING_ID"]] = (amend, money(row.get("AMOUNT_A")))

    receipts_by_committee = {}
    for committee, bucket in sorted(latest.items()):
        total = Decimal(0)
        any_amount = False
        for _amend, amount in bucket.values():
            if amount is not None:
                total += amount
                any_amount = True
        froms = [v[1] for v in filings.values() if v[0] == committee and v[1]]
        thrus = [v[2] for v in filings.values() if v[0] == committee and v[2]]
        receipts_by_committee[committee] = {
            "total": str(total.quantize(Decimal("0.01"))) if any_amount else None,
            "from": max(min(froms), CYCLE_START).isoformat() if froms else None,
            "through": max(thrus).isoformat() if thrus else None}

    # Pass 5: independent expenditures — Schedule E rows coded IND with a support/oppose
    # code targeting a tracked candidacy since the cycle start. Late 24-/48-hour notices
    # (F465/F496) and memo subtotals are excluded; amendments supersede per filing+line.
    ie_rows = {}   # key -> {(filing_id, line): (amend, direction, amount)}
    ie_filings = set()
    for row in read_tsv("EXPN_CD.TSV"):
        so = (row.get("SUP_OPP_CD") or "").strip().upper()
        if so not in ("S", "O") or (row.get("EXPN_CODE") or "").strip().upper() != "IND":
            continue
        form = (row.get("FORM_TYPE") or "").strip()
        if form not in ("D", "E", "F461P5"):  # detail schedules; notices excluded.
            continue
        # Coalition filings repeat Schedule E detail as memo rollups without an
        # expenditure date; the dated EXPN_DATE requirement below keeps each
        # expenditure exactly once (the schedule-D detail row).
        if (row.get("MEMO_CODE") or "").strip().upper():
            continue
        expn_date = parse_date(row.get("EXPN_DATE"))
        if not expn_date or expn_date < CYCLE_START:
            continue
        amount = money(row.get("AMOUNT"))
        if amount is None:
            continue
        matched = match_row(row)
        if not matched:
            continue
        office_cd = (row.get("OFFICE_CD") or "").strip()
        district = None if office_cd in STATEWIDE_OFFICES else row_district(row)
        key = (office_cd, district) + matched
        bucket = ie_rows.setdefault(key, {})
        row_key = (row["FILING_ID"], row["LINE_ITEM"])
        amend = int(row["AMEND_ID"] or 0)
        prev = bucket.get(row_key)
        if prev is None or amend >= prev[0]:
            bucket[row_key] = (amend, "for" if so == "S" else "against", amount)
        ie_filings.add(row["FILING_ID"])

    # The spender on a Schedule E independent expenditure is the filing committee;
    # EXPN.CMTE_ID is empty on these rows, so resolve filers via FILER_FILINGS_CD.
    filing_to_filer = {}
    for row in read_tsv("FILER_FILINGS_CD.TSV"):
        fid = (row.get("FILING_ID") or "").strip()
        if fid in ie_filings:
            filing_to_filer[fid] = (row.get("FILER_ID") or "").strip()

    # Names for spenders and controlled committees via FILERNAME_CD.
    need_names = {f for f in filing_to_filer.values() if f} | controlled
    filer_names = {}
    for row in read_tsv("FILERNAME_CD.TSV"):
        fid = (row.get("FILER_ID") or "").strip()
        if fid in need_names and fid not in filer_names:
            name = " ".join(p.strip() for p in (row.get("NAML"), row.get("NAMF")) if (p or "").strip())
            if name:
                filer_names[fid] = name

    candidates_out = {}
    spenders_used = set()
    for key, bucket in sorted(ie_rows.items()):
        _office_cd, _district, position_id, cand_name = key
        ident = f"{position_id}|{cand_name}"
        totals = {}  # (spender, direction) -> [Decimal sum, row count]
        for (filing_id, _line), (_amend, direction, amount) in bucket.items():
            spender = filing_to_filer.get(filing_id) or ""
            slot = totals.setdefault((spender, direction), [Decimal(0), 0])
            slot[0] += amount
            slot[1] += 1
        items = []
        for (spender, direction), (total, count) in sorted(totals.items(), key=lambda kv: -kv[1][0]):
            if spender:
                spenders_used.add(spender)
            items.append({"spender_id": spender or "unknown", "direction": direction,
                          "amount": float(total.quantize(Decimal("0.01"))), "items": count})
        candidates_out.setdefault(ident, {})["ie"] = items

    for key, committees in sorted(committees_by_key.items()):
        _office_cd, _district, position_id, cand_name = key
        ident = f"{position_id}|{cand_name}"
        record = candidates_out.setdefault(ident, {})
        record["committees"] = sorted(committees)
        total = None
        froms, thrus = [], []
        for committee in committees:
            payload = receipts_by_committee.get(committee)
            if not payload:
                continue
            if payload["total"] is not None:
                total = (total or Decimal(0)) + Decimal(payload["total"])
            if payload["from"]:
                froms.append(payload["from"])
            if payload["through"]:
                thrus.append(payload["through"])
        record["receipts_total"] = str(total.quantize(Decimal("0.01"))) if total is not None else None
        record["coverage_from"] = min(froms) if froms else None
        record["coverage_through"] = max(thrus) if thrus else None

    state = load_state()
    result = {
        "format": "ca-campaign-finance/v1",
        "generated_at": now_utc(),
        "source_url": SOURCE_URL,
        "source_page": SOURCE_PAGE,
        "cycle_start": CYCLE_START.isoformat(),
        "download": {k: state.get(k) for k in ("downloaded_at", "source_last_modified", "zip_sha256")},
        "candidates": candidates_out,
        "spenders": {fid: {"name": filer_names[fid]} for fid in sorted(spenders_used) if fid in filer_names},
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=1), encoding="utf-8")
    state["last_build_at"] = now_utc()
    save_state(state)
    with_ie = sum(1 for v in candidates_out.values() if v.get("ie"))
    with_receipts = sum(1 for v in candidates_out.values() if v.get("receipts_total"))
    print(f"Wrote {args.output}: {len(candidates_out)} candidacies "
          f"({with_receipts} with receipts totals, {with_ie} with independent-expenditure rows).")


# ---------------------------------------------------------------- attach

def cmd_attach(args):
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    expected_schema = json.loads((ROOT / "elections.schema.json").read_text())["properties"]["schema_version"]["const"]
    if data["schema_version"] != expected_schema:
        raise SystemExit(f"Dataset schema must be {expected_schema} before attach; update the schema first.")

    source_id = args.source_id
    if not source_id:
        numbers = [int(k[1:]) for k in data["sources"]]
        source_id = f"S{max(numbers) + 1}"
        data["sources"][source_id] = {"url": snapshot["source_page"],
                                      "title": ("California Secretary of State — Raw Data for Campaign "
                                                "Finance and Lobbying Activity (CAL-ACCESS dbwebexport.zip)")}

    by_ident = snapshot["candidates"]
    attached_receipts = attached_ie = unmatched = 0
    registry = data.setdefault("ca_ie_spenders", {})
    for position in data["positions"]:
        if not contest_key(position):
            continue
        for roster in ("candidates", "filed_candidates_not_confirmed_on_ballot"):
            for candidate in (position.get(roster) or []):
                ident = f"{position['id']}|{candidate['name']}"
                record = by_ident.get(ident)
                if not record:
                    unmatched += 1
                    continue
                committees = record.get("committees") or []
                if committees:
                    ca_finance = {"committee_ids": committees, "source_id": source_id}
                    total = record.get("receipts_total")
                    if total is not None:
                        ca_finance["receipts"] = float(Decimal(total))
                        ca_finance["from"] = record.get("coverage_from") or snapshot["cycle_start"]
                        ca_finance["through"] = record.get("coverage_through") or snapshot["cycle_start"]
                        attached_receipts += 1
                    else:
                        ca_finance["receipts"] = None
                        if args.note_id:
                            ca_finance["note_id"] = args.note_id
                    candidate["ca_finance"] = ca_finance
                items = []
                for item in record.get("ie") or []:
                    spender_id = item["spender_id"]
                    meta = snapshot["spenders"].get(spender_id) or {}
                    name = meta.get("name") or f"CAL-ACCESS filer {spender_id}"
                    existing = registry.get(spender_id)
                    if existing and existing["name"] != name:
                        # FILERNAME_CD keeps several historical name rows per filer and the
                        # export row order is not stable across nightly dumps, so the build's
                        # first-occurrence pick can flip between runs. The registry published
                        # with this spender id stays authoritative; keep its name.
                        print(f"note: spender {spender_id} now files as {name!r}; "
                              f"keeping registered {existing['name']!r}")
                        name = existing["name"]
                    registry[spender_id] = {"name": name, "source_url": COMMITTEE_URL.format(spender_id)}
                    items.append({"spender_id": spender_id, "direction": item["direction"],
                                  "amount": round(item["amount"], 2), "items": item["items"]})
                if items:
                    for_total = sum(i["amount"] for i in items if i["direction"] == "for")
                    against_total = sum(i["amount"] for i in items if i["direction"] == "against")
                    candidate["ca_independent_expenditures"] = {
                        "for_total": round(for_total, 2), "against_total": round(against_total, 2),
                        "items": sorted(items, key=lambda i: -i["amount"])}
                    attached_ie += 1

    checked_on = args.checked_on or dt.date.today().isoformat()
    data["ca_finance_settings"] = {
        "provider": "California Secretary of State CAL-ACCESS",
        "cycle_start": snapshot["cycle_start"], "currency": "USD",
        "metric": "total_cash_receipts", "checked_on": checked_on,
        "source_id": source_id,
        "method": ("Total cash receipts (Form 460 summary line 13) reported by each candidacy's controlled "
                   "recipient committees for statements covering periods from January 1, 2025 onward, from "
                   "the Secretary of State's nightly CAL-ACCESS raw-data export. Receipts include monetary "
                   "contributions, loans and other cash receipts as filed; they are not net donations or cash "
                   "on hand, and independent outside spending is excluded. Amendments supersede the statements "
                   "they amend; statement periods opening before January 1, 2025 are excluded rather than "
                   "split. Coverage dates follow each committee's latest filed statement. Amounts are as filed "
                   "and not independently audited. This is a dated snapshot of the raw export, not a live feed."),
    }
    data["ca_ie_finance"] = {
        "provider": "California Secretary of State CAL-ACCESS",
        "cycle_start": snapshot["cycle_start"], "currency": "USD",
        "metric": "independent_expenditures", "checked_on": checked_on,
        "source_id": source_id,
        "method": ("Independent expenditures reported on Form 460 Schedule E with an IND expenditure code and a "
                   "support/oppose code targeting this candidacy since January 1, 2025, from the Secretary of "
                   "State's nightly CAL-ACCESS raw-data export. Committee contributions to candidates (Schedule "
                   "D/E monetary gifts), memo subtotals and late 24-/48-hour Form 465/496 notices are excluded; "
                   "amendments supersede the statements they amend, so recent notice-only spending is outside "
                   "these totals. The spender is the committee that filed the statement. Amounts are independent "
                   "outside spending: they are not campaign receipts, contributions, coordination findings or "
                   "endorsements, and support of one candidate is never treated as opposition to another. This "
                   "is a dated snapshot of the raw export, not a live feed."),
    }

    coverage = data["coverage"]
    printed = [c for p in data["positions"] if contest_key(p) for c in (p.get("candidates") or [])]
    coverage["printed_candidates_with_ca_receipts"] = sum(
        1 for c in printed if isinstance((c.get("ca_finance") or {}).get("receipts"), (int, float)))
    coverage["printed_candidates_with_ca_independent_expenditures"] = sum(
        1 for c in printed
        if (c.get("ca_independent_expenditures") or {}).get("for_total")
        or (c.get("ca_independent_expenditures") or {}).get("against_total"))

    if args.publication_version:
        data["election"]["publication_version"] = args.publication_version

    DATASET.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    state = load_state()
    state["last_attach_at"] = now_utc()
    save_state(state)
    print(json.dumps({"passed": True, "candidates_with_receipts": attached_receipts,
                      "candidates_with_ie_activity": attached_ie,
                      "candidacies_without_calaccess_match": unmatched,
                      "spenders_registered": len(registry), "source_id": source_id,
                      "checked_on": checked_on}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    dl = sub.add_parser("download")
    dl.add_argument("--force", action="store_true")
    build = sub.add_parser("build")
    build.add_argument("--output", default=str(DERIVED_DEFAULT))
    att = sub.add_parser("attach")
    att.add_argument("--snapshot", default=str(DERIVED_DEFAULT))
    att.add_argument("--publication-version")
    att.add_argument("--checked-on")
    att.add_argument("--source-id")
    att.add_argument("--note-id")
    args = parser.parse_args()
    if args.command == "download":
        cmd_download(args)
    elif args.command == "build":
        cmd_build(args)
    else:
        cmd_attach(args)


if __name__ == "__main__":
    main()
