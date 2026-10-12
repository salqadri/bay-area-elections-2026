"""Collect FEC independent-expenditure (Schedule E) data for printed federal candidates.

Deterministic primary-source collection: no LLM, Jev or agent calls are made here.
The scope follows the dataset itself — every printed candidate entry that carries a
``fec.id`` is eligible, so expanding ballot coverage to new counties automatically
expands this layer once those candidates exist in the dataset. County selection only
narrows which eligible entries a run refreshes.

Subcommands (run from anywhere; paths resolve against the repository root):

  plan    [--county NAME ...|--scope bay-area|california]   report eligible entries
  run     [same scope options] [--cycle N]                  fetch + cache Schedule E rows
  export  --output PATH                                    normalized review export
  attach  --publication-version V                            write the dataset layer

Raw API rows are cached in a local SQLite ledger (default .research/ie/fec_ie.sqlite3,
never committed). Re-running ``run`` only refetches candidates whose cache is older than
--refresh-days. The FEC API key comes from FEC_API_KEY or --fec-key-file; it is never
written to the repository, logs or generated HTML.

Aggregation rules (also recorded in the published ie_finance.method):
  * keep only ``most_recent`` rows (amendment supersession handled by FEC);
  * drop memo-child rows when the same link_id also carries a non-memo row on that
    filing (the committee's reported subtotal already includes them); standalone
    memo rows are kept because they are the only itemization of that expenditure;
  * keep only current-cycle election types (P2026/G2026/R2026 for cycle 2026); other
    election types (for example late G2024 disbursements filed in this cycle) are
    counted as excluded and never added to a candidate total;
  * support_oppose_indicator S -> "for", O -> "against"; rows without one are counted
    as unspecified and excluded from totals.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "2026-11-03_Bay_Area_Elections.json"
COUNTY_REGISTRY = ROOT / "research/california-counties.json"
DEFAULT_DB = ROOT / ".research/ie/fec_ie.sqlite3"
API = "https://api.open.fec.gov/v1/schedules/schedule_e/"
BAY_AREA = ["Alameda", "Contra Costa", "Marin", "Napa", "San Francisco",
            "San Mateo", "Santa Clara", "Solano", "Sonoma"]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def fec_key(args) -> str:
    key = os.environ.get("FEC_API_KEY", "").strip()
    if not key and args.fec_key_file:
        key = Path(args.fec_key_file).read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("Provide FEC_API_KEY or --fec-key-file (never commit the key).")
    return key


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS candidates(
        candidate_id TEXT PRIMARY KEY, name TEXT, position_id TEXT,
        fetched_at TEXT, rows_total INTEGER, excluded_prior_cycle INTEGER,
        excluded_nonrecent INTEGER, excluded_memo_child INTEGER,
        unspecified_direction INTEGER)""")
    db.execute("""CREATE TABLE IF NOT EXISTS rows(
        sub_id TEXT PRIMARY KEY, candidate_id TEXT, link_id INTEGER,
        committee_id TEXT, committee_name TEXT, committee_type TEXT,
        support_oppose TEXT, election_type TEXT, amount REAL,
        expenditure_date TEXT, dissemination_date TEXT, filing_date TEXT,
        memo_code TEXT, most_recent INTEGER, purpose TEXT, pdf_url TEXT)""")
    return db


def scope_counties(args) -> set | None:
    if args.scope == "bay-area":
        return set(BAY_AREA)
    names = list(args.county or [])
    if args.scope == "california":
        registry = json.loads(COUNTY_REGISTRY.read_text(encoding="utf-8"))
        return {c["name"] for c in registry["counties"]}
    if not names:
        return None
    registry = json.loads(COUNTY_REGISTRY.read_text(encoding="utf-8"))
    known = {c["name"].lower(): c["name"] for c in registry["counties"]}
    resolved = set()
    for name in names:
        canonical = known.get(name.lower())
        if not canonical:
            raise SystemExit(f"Unknown county: {name}")
        resolved.add(canonical)
    return resolved


def eligible(data, counties):
    out = []
    for position in data["positions"]:
        if position.get("government_level") != "Federal":
            continue
        if counties is not None and not (counties & set(position["counties"])):
            continue
        for candidate in position.get("candidates") or []:
            fec = candidate.get("fec") or {}
            if fec.get("id"):
                out.append((fec["id"], candidate["name"], position["id"]))
    return out


def fetch_rows(key: str, candidate_id: str, cycle: int):
    """Keyset pagination via pagination.last_indexes.

    The Schedule E endpoint ignores ``page`` (every page returns the same first
    window), so pages advance with the last_expenditure_date/last_index cursor
    the API itself publishes. Rows are deduplicated by sub_id as a guard.
    """
    rows, seen, cursor = {}, set(), None
    while True:
        params = {"candidate_id": candidate_id, "cycle": cycle,
                  "per_page": 100, "api_key": key}
        if cursor:
            params.update(cursor)
        url = API + "?" + urllib.parse.urlencode(params)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    payload = json.load(response)
                break
            except urllib.error.HTTPError as error:
                if error.code == 429 and attempt < 4:
                    time.sleep(15 * (attempt + 1))
                    continue
                raise
        batch = payload.get("results") or []
        fresh = [row for row in batch if row.get("sub_id") not in seen]
        for row in fresh:
            seen.add(row["sub_id"])
            rows[row["sub_id"]] = row
        total = payload.get("pagination", {}).get("count", 0)
        indexes = (payload.get("pagination") or {}).get("last_indexes")
        if not batch or not fresh or len(rows) >= total or not indexes:
            return list(rows.values()), total
        cursor = {"last_expenditure_date": indexes["last_expenditure_date"],
                  "last_index": indexes["last_index"]}
        time.sleep(1.5)


def current_cycle_types(cycle: int):
    return {f"P{cycle}", f"G{cycle}", f"R{cycle}"}


def spender_source_url(spender_id: str, name: str) -> str:
    """FEC committee page when a committee ID exists; FEC data search otherwise."""
    if re.fullmatch(r"C[0-9]{8}", spender_id):
        return f"https://www.fec.gov/data/committee/{spender_id}/"
    return ("https://www.fec.gov/data/search/?search="
            + urllib.parse.quote_plus((name or spender_id).strip()))


def candidate_browse_url(candidate_id: str, cycle: int) -> str:
    """FEC independent-expenditure browse page filtered to this candidate/cycle."""
    return ("https://www.fec.gov/data/independent-expenditures/?"
            + urllib.parse.urlencode({
                "data_type": "processed", "candidate_id": candidate_id,
                "min_date": f"{cycle - 1}-01-01", "max_date": f"{cycle}-12-31"}))


def cmd_plan(args, db):
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    entries = eligible(data, scope_counties(args))
    cached = {r[0]: r[1] for r in db.execute(
        "SELECT candidate_id, fetched_at FROM candidates")}
    print(json.dumps({
        "eligible_federal_entries": len(entries),
        "unique_candidate_ids": len({e[0] for e in entries}),
        "already_cached": sum(1 for e in entries if e[0] in cached),
        "uncached": sorted({e[0] for e in entries} - set(cached)),
    }, indent=2))


def cmd_run(args, db):
    key = fec_key(args)
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    entries = eligible(data, scope_counties(args))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.refresh_days)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    cached = {r[0]: r[1] for r in db.execute("SELECT candidate_id, fetched_at FROM candidates")}
    todo = [e for e in entries if args.force or e[0] not in cached or (cached[e[0]] or "") < cutoff]
    print(f"{len(todo)} of {len(entries)} unique candidates to fetch "
          f"(refresh-days={args.refresh_days}).", flush=True)
    seen = set()
    for candidate_id, name, position_id in todo:
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        rows, total = fetch_rows(key, candidate_id, args.cycle)
        db.execute("BEGIN")
        db.execute("DELETE FROM rows WHERE candidate_id=?", (candidate_id,))
        keep_types = current_cycle_types(args.cycle)
        excluded_prior = sum(1 for r in rows if str(r.get("election_type")) not in keep_types)
        excluded_nonrecent = sum(1 for r in rows if not r.get("most_recent"))
        link_codes = {}
        for row in rows:
            link_codes.setdefault(row.get("link_id"), set()).add(row.get("memo_code") or "")
        memo_child = sum(1 for r in rows if (r.get("memo_code") == "X"
                         and "" in link_codes.get(r.get("link_id"), set())))
        unspecified = sum(1 for r in rows if not r.get("support_oppose_indicator"))
        for row in rows:
            committee = row.get("committee") or {}
            db.execute("INSERT OR REPLACE INTO rows VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                str(row.get("sub_id")), candidate_id, row.get("link_id"),
                committee.get("committee_id"), committee.get("name"),
                committee.get("committee_type_full"),
                row.get("support_oppose_indicator"), str(row.get("election_type")),
                row.get("expenditure_amount"), row.get("expenditure_date"),
                row.get("dissemination_date"), row.get("filing_date"),
                row.get("memo_code"), 1 if row.get("most_recent") else 0,
                row.get("expenditure_description"), row.get("pdf_url")))
        db.execute("INSERT OR REPLACE INTO candidates VALUES(?,?,?,?,?,?,?,?,?)", (
            candidate_id, name, position_id, now_utc(), total or len(rows),
            excluded_prior, excluded_nonrecent, memo_child, unspecified))
        db.commit()
        print(f"  {name} ({candidate_id}): {len(rows)} rows cached", flush=True)
        time.sleep(0.3)


def aggregate(db, cycle: int):
    """Return per-candidate aggregates applying the documented rules."""
    keep_types = current_cycle_types(cycle)
    out = {}
    for candidate_id, name, position_id in db.execute(
            "SELECT candidate_id, name, position_id FROM candidates"):
        rows = [dict(zip([c[1] for c in db.execute("PRAGMA table_info(rows)").fetchall()], r))
                for r in db.execute("SELECT * FROM rows WHERE candidate_id=?", (candidate_id,))]
        link_codes = {}
        for row in rows:
            link_codes.setdefault(row["link_id"], set()).add(row["memo_code"] or "")
        counted = []
        excluded = {"prior_cycle": 0, "nonrecent": 0, "memo_child": 0, "unspecified": 0}
        for row in rows:
            if not row["most_recent"]:
                excluded["nonrecent"] += 1
                continue
            if row["election_type"] not in keep_types:
                excluded["prior_cycle"] += 1
                continue
            if (row["memo_code"] == "X" and "" in link_codes.get(row["link_id"], set())):
                excluded["memo_child"] += 1
                continue
            if row["support_oppose"] not in ("S", "O"):
                excluded["unspecified"] += 1
                continue
            counted.append(row)
        spenders = {}
        for row in counted:
            key = row["committee_id"] or f"name:{(row['committee_name'] or '').strip().upper()}"
            entry = spenders.setdefault(key, {
                "spender_id": key, "name": row["committee_name"],
                "committee_type": row["committee_type"],
                "for_amount": Decimal("0"), "against_amount": Decimal("0"),
                "items": 0, "first_date": None, "last_date": None})
            direction = "for_amount" if row["support_oppose"] == "S" else "against_amount"
            entry[direction] += Decimal(str(row["amount"]))
            entry["items"] += 1
            day = row["expenditure_date"] or row["dissemination_date"]
            if day:
                entry["first_date"] = min(entry["first_date"] or day, day)
                entry["last_date"] = max(entry["last_date"] or day, day)
        items = []
        for entry in spenders.values():
            item = {"spender_id": entry["spender_id"], "items": entry["items"],
                    "first_expenditure_date": entry["first_date"],
                    "last_expenditure_date": entry["last_date"]}
            if entry["for_amount"] > 0:
                item["direction"] = "for"
                item["amount"] = float(entry["for_amount"])
            else:
                item["direction"] = "against"
                item["amount"] = float(entry["against_amount"])
            items.append(item)
        items.sort(key=lambda i: -i["amount"])
        out[candidate_id] = {
            "name": name, "position_id": position_id,
            "for_total": float(sum((Decimal(str(i["amount"])) for i in items if i["direction"] == "for"), Decimal("0"))),
            "against_total": float(sum((Decimal(str(i["amount"])) for i in items if i["direction"] == "against"), Decimal("0"))),
            "items": items, "excluded": excluded,
            "registry": {k: {"name": v["name"], "committee_type": v["committee_type"],
                             "source_url": spender_source_url(k, v["name"])}
                         for k, v in spenders.items()},
        }
    return out


def cmd_export(args):
    db = open_db(Path(args.db))
    aggregates = aggregate(db, args.cycle)
    export = {
        "format": "fec-independent-expenditures/v1",
        "generated_at": now_utc(),
        "cycle": args.cycle,
        "provider": "FEC",
        "api": API,
        "candidates": aggregates,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(export, indent=1), encoding="utf-8")
    print(f"Wrote {args.output}: {len(aggregates)} candidates.")


def cmd_attach(args):
    db = open_db(Path(args.db))
    aggregates = aggregate(db, args.cycle)
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    if data["schema_version"] != "1.18":
        raise SystemExit("Dataset schema must be 1.18 before attach; update the schema first.")
    checked_on = args.checked_on or date.today().isoformat()

    # Shared spender registry: additive, keyed by FEC committee id (or name fallback).
    registry = data.setdefault("ie_spenders", {})
    for agg in aggregates.values():
        for key, meta in agg["registry"].items():
            existing = registry.get(key)
            if existing and existing["name"] != meta["name"]:
                raise SystemExit(f"Spender id {key} already registered with a different name.")
            registry[key] = {"name": meta["name"], "committee_type": meta["committee_type"],
                             "source_url": spender_source_url(key, meta["name"])}

    attached = 0
    federal_seen = set()
    for position in data["positions"]:
        if position.get("government_level") != "Federal":
            continue
        for candidate in position.get("candidates") or []:
            fec_id = (candidate.get("fec") or {}).get("id")
            if not fec_id:
                continue
            federal_seen.add(fec_id)
            agg = aggregates.get(fec_id)
            if agg is None:
                raise SystemExit(f"No cached IE data for {candidate['name']} ({fec_id}); run first.")
            candidate["independent_expenditures"] = {
                "browse_url": candidate_browse_url(fec_id, args.cycle),
                "for_total": round(agg["for_total"], 2),
                "against_total": round(agg["against_total"], 2),
                "items": agg["items"],
            }
            if agg["for_total"] or agg["against_total"]:
                attached += 1

    data["ie_finance"] = {
        "provider": "FEC", "cycle": args.cycle, "currency": "USD",
        "metric": "independent_expenditures", "checked_on": checked_on,
        "source_id": args.source_id,
        "method": ("Itemized independent expenditures (FEC Schedule E) reported for the "
                   f"{args.cycle} two-year period and linked to each printed federal candidate. "
                   "Only current-cycle election types are counted; late filings referencing prior "
                   "elections are excluded from totals. Amendment supersessions use the most recent "
                   "filing, and memo subtotals already included in a reported itemization are not "
                   "added twice. Amounts are independent outside spending: they are not campaign "
                   "receipts, contributions, coordination findings or endorsements, and support of "
                   "one candidate is never treated as opposition to another. This is a dated "
                   "snapshot from the FEC API, not a live feed."),
    }

    coverage = data["coverage"]
    entries = [c for p in data["positions"] if p.get("government_level") == "Federal"
               for c in (p.get("candidates") or [])]
    coverage["printed_candidates_with_independent_expenditures"] = sum(
        1 for c in entries
        if (c.get("independent_expenditures") or {}).get("for_total")
        or (c.get("independent_expenditures") or {}).get("against_total"))

    if args.publication_version:
        data["election"]["publication_version"] = args.publication_version

    DATASET.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "candidates_with_ie_activity": attached,
                      "federal_entries_cached": len(federal_seen),
                      "spenders_registered": len(registry),
                      "checked_on": checked_on}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--cycle", type=int, default=2026)
    parser.add_argument("--county", action="append")
    parser.add_argument("--scope", choices=["bay-area", "california"])
    parser.add_argument("--fec-key-file", default="/root/.cfg/fec_key")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    runp = sub.add_parser("run")
    runp.add_argument("--refresh-days", type=int, default=36500)
    runp.add_argument("--force", action="store_true")
    exp = sub.add_parser("export")
    exp.add_argument("--output", required=True)
    att = sub.add_parser("attach")
    att.add_argument("--publication-version")
    att.add_argument("--checked-on")
    att.add_argument("--source-id", default="S1086")
    args = parser.parse_args()

    if args.command == "plan":
        cmd_plan(args, open_db(Path(args.db)))
    elif args.command == "run":
        cmd_run(args, open_db(Path(args.db)))
    elif args.command == "export":
        cmd_export(args)
    else:
        cmd_attach(args)


if __name__ == "__main__":
    main()
