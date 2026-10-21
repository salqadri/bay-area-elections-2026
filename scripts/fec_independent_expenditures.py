"""Collect official FEC independent-expenditure aggregates for federal candidates.

Plan -> run -> export -> attach; includes printed and provisional FEC-linked
candidacies, with optional county scope for collection. Uses the same endpoint as
FEC.gov candidate pages: /schedules/schedule_e/by_candidate/, cycle explicitly
selected with election_full=false. FEC excludes 24-/48-hour notices and memo
entries, so overlapping reporting streams are never added together locally.

The cycle/method-version cache is separate from legacy raw Schedule E tables.
Old caches must be recollected. A failed or incomplete response never becomes a
zero, and attach requires current-method snapshots for the entire federal scope.
No model is used to calculate financial amounts. Credentials come from FEC_API_KEY
or --fec-key-file and are never stored in exports, the ledger or generated pages.
"""

import argparse
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "2026-11-03_Bay_Area_Elections.json"
COUNTY_REGISTRY = ROOT / "research/california-counties.json"
DEFAULT_DB = ROOT / ".research/ie/fec_ie.sqlite3"
API = "https://api.open.fec.gov/v1/schedules/schedule_e/by_candidate/"
METHOD_VERSION = "fec-by-candidate-v2"
BAY_AREA = ["Alameda", "Contra Costa", "Marin", "Napa", "San Francisco",
            "San Mateo", "Santa Clara", "Solano", "Sonoma"]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def checked_date(timestamp):
    """Publication dates use the project's Pacific timezone, not the UTC day."""
    value = datetime.fromisoformat(timestamp)
    if value.tzinfo is None:
        raise ValueError("FEC snapshot timestamp needs an explicit timezone")
    return value.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()


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
    # Deliberately separate from the v1 raw-row cache: it discarded is_notice,
    # so neither recent timestamps nor reaggregation can make it safe to reuse.
    db.execute("""CREATE TABLE IF NOT EXISTS aggregate_snapshots(
        candidate_id TEXT, cycle INTEGER, method_version TEXT,
        fetched_at TEXT NOT NULL, payload_json TEXT NOT NULL,
        PRIMARY KEY(candidate_id, cycle, method_version))""")
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
        # October 17, 2026: nationwide Senate candidacies carry FEC-registered filers under the
        # provisional roster while ballot status awaits official reconciliation; their outside
        # spending is primary-source data regardless of that status.
        for candidate in (position.get("candidates") or []) + (position.get("filed_candidates_not_confirmed_on_ballot") or []):
            fec = candidate.get("fec") or {}
            if fec.get("id"):
                out.append((fec["id"], candidate["name"], position["id"]))
    return out


def fetch_page(key, params):
    url = API + "?" + urllib.parse.urlencode({**params, "api_key": key})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(min(15 * (attempt + 1), 60))
                continue
            # urllib errors can include the request URL, including its key.
            raise RuntimeError(f"FEC aggregate request failed: HTTP {error.code}") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError("FEC aggregate request failed: network error") from None


def normalize_rows(rows, candidate_id, cycle):
    """Validate the source contract; never turn malformed/missing data into zero."""
    seen = set()
    for row in rows:
        if row.get("candidate_id") != candidate_id or row.get("cycle") != cycle:
            raise ValueError("FEC aggregate candidate/cycle mismatch")
        committee = row.get("committee_id")
        if not isinstance(committee, str) or not re.fullmatch(r"C[0-9]{8}", committee):
            raise ValueError("FEC aggregate has no valid spender ID")
        if not isinstance(row.get("committee_name"), str) or not row["committee_name"].strip():
            raise ValueError("FEC aggregate has no spender name")
        direction = row.get("support_oppose_indicator")
        if direction not in ("S", "O", "Other"):
            raise ValueError("FEC aggregate has an unsupported spending direction")
        identity = (committee, direction)
        if identity in seen:
            raise ValueError("Duplicate FEC spender/direction; pagination may have repeated")
        seen.add(identity)
        if type(row.get("count")) is not int or row["count"] < 1:
            raise ValueError("FEC aggregate has an invalid item count")
        value = row.get("total")
        if type(value) not in (int, float):
            raise ValueError("FEC aggregate has no numeric total")
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount != amount.quantize(Decimal("0.01")):
            raise ValueError("FEC aggregate has an invalid total; review before publishing")
    return rows


def fetch_aggregates(key: str, candidate_id: str, cycle: int):
    """Use the same regular-report totals as FEC.gov, with page-number pagination.

    election_full=false is essential for Senate candidates: explicitly request the
    two-year cycle rather than rolling several cycles into a full election total.
    The FEC owns amendment resolution, memo exclusion and election-cycle mapping.
    """
    rows, page, expected = [], 1, None
    while True:
        payload = fetch_page(key, {"candidate_id": candidate_id, "cycle": cycle,
                                  "election_full": "false", "per_page": 100,
                                  "page": page, "sort": "committee_id"})
        batch = payload.get("results")
        pagination = payload.get("pagination") or {}
        count = pagination.get("count")
        if not isinstance(batch, list) or type(count) is not int or count < 0:
            raise ValueError("Incomplete FEC aggregate response")
        if pagination.get("is_count_exact") is not True or pagination.get("page") != page:
            raise ValueError("Unexpected FEC aggregate pagination")
        if expected is None:
            expected = count
        if count != expected:
            raise ValueError("FEC aggregate count changed during fetch; retry the snapshot")
        rows.extend(batch)
        normalize_rows(rows, candidate_id, cycle)
        if len(rows) == count:
            # The by_candidate aggregate occasionally includes 'Other'-direction rows
            # (e.g. individual filers with no support/oppose indicator). This dataset
            # models only support ('for') and opposition ('against'); an Other row can
            # be attributed to neither without inventing semantics, so it is excluded
            # from the snapshot — never recorded as zero or folded into a direction.
            # FEC's own candidate-page for/against totals exclude them identically.
            return [r for r in rows if r.get("support_oppose_indicator") in ("S", "O")]
        if len(rows) > count or not batch:
            raise ValueError("Incomplete or repeated FEC aggregate pages")
        page += 1
        time.sleep(0.3)


def cached_snapshots(db, cycle):
    return {cid: {"fetched_at": fetched, "rows": json.loads(payload)}
            for cid, fetched, payload in db.execute(
                "SELECT candidate_id, fetched_at, payload_json FROM aggregate_snapshots "
                "WHERE cycle=? AND method_version=?", (cycle, METHOD_VERSION))}


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
                "is_notice": "false", "most_recent": "true",
                "min_date": f"{cycle - 1}-01-01", "max_date": f"{cycle}-12-31"}))


def cmd_plan(args, db):
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    entries = eligible(data, scope_counties(args))
    cached = cached_snapshots(db, args.cycle)
    print(json.dumps({
        "eligible_federal_entries": len(entries),
        "unique_candidate_ids": len({e[0] for e in entries}),
        "already_cached": sum(1 for e in entries if e[0] in cached),
        "uncached": sorted({e[0] for e in entries} - set(cached)),
    }, indent=2))


def cmd_run(args, db):
    key = fec_key(args)
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    entries = {cid: name for cid, name, _ in eligible(data, scope_counties(args))}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.refresh_days)).isoformat()
    cached = cached_snapshots(db, args.cycle)
    todo = [(cid, name) for cid, name in entries.items()
            if args.force or cid not in cached or cached[cid]["fetched_at"] < cutoff]
    print(f"{len(todo)} of {len(entries)} unique candidates to fetch "
          f"(method={METHOD_VERSION}, cycle={args.cycle}).", flush=True)
    for candidate_id, name in todo:
        rows = fetch_aggregates(key, candidate_id, args.cycle)
        # Commit only after ALL pages and source fields have passed validation.
        with db:
            db.execute("INSERT OR REPLACE INTO aggregate_snapshots VALUES(?,?,?,?,?)",
                       (candidate_id, args.cycle, METHOD_VERSION, now_utc(), json.dumps(rows)))
        print(f"  {name} ({candidate_id}): {len(rows)} spender/direction totals cached", flush=True)
        time.sleep(0.3)


def aggregate(db, cycle: int):
    """Normalize official aggregates; do not sum itemized notices or guess memos."""
    out = {}
    for candidate_id, snapshot in cached_snapshots(db, cycle).items():
        rows = normalize_rows(snapshot["rows"], candidate_id, cycle)
        items, registry = [], {}
        totals = {"for": Decimal(0), "against": Decimal(0)}
        for row in rows:
            direction = "for" if row["support_oppose_indicator"] == "S" else "against"
            key = row["committee_id"]
            registry[key] = {"name": row["committee_name"],
                             "source_url": spender_source_url(key, row["committee_name"])}
            totals[direction] += Decimal(str(row["total"]))
            items.append({"spender_id": key, "direction": direction,
                          "amount": row["total"], "items": row["count"]})
        items.sort(key=lambda i: (-i["amount"], i["spender_id"], i["direction"]))
        out[candidate_id] = {"for_total": float(totals["for"]),
                             "against_total": float(totals["against"]),
                             "items": items, "registry": registry,
                             "fetched_at": snapshot["fetched_at"]}
    return out


def cmd_export(args):
    db = open_db(Path(args.db))
    aggregates = aggregate(db, args.cycle)
    export = {
        "format": "fec-independent-expenditures/v2",
        "method_version": METHOD_VERSION,
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
    expected_schema = json.loads((ROOT / "elections.schema.json").read_text())["properties"]["schema_version"]["const"]
    if data["schema_version"] != expected_schema:
        raise SystemExit(f"Dataset schema must be {expected_schema} before attach; update the schema first.")
    if args.cycle != data["finance"]["cycle"]:
        raise SystemExit("IE cycle must match the dataset finance cycle.")
    required_ids = {cid for cid, _, _ in eligible(data, None)}
    missing = required_ids - aggregates.keys()
    if missing:
        raise SystemExit("No current-method IE snapshot for: " + ", ".join(sorted(missing)) + "; run first.")
    # A partial/failed refresh must not advertise that every candidate was checked
    # today. Use the oldest actual retrieval date, or reject an overstated date.
    dates = [checked_date(aggregates[cid]["fetched_at"]) for cid in required_ids]
    checked_on = min(dates)
    if args.checked_on and args.checked_on != checked_on:
        raise SystemExit("--checked-on must equal the oldest candidate retrieval date: " + checked_on)
    aggregates = {cid: aggregates[cid] for cid in sorted(required_ids)}

    # Shared spender registry: additive, keyed by FEC committee id (or name fallback).
    registry = data.setdefault("ie_spenders", {})
    for agg in aggregates.values():
        for key, meta in agg["registry"].items():
            existing = registry.get(key)
            if existing and existing["name"] != meta["name"]:
                raise SystemExit(f"Spender id {key} already registered with a different name.")
            # The aggregate endpoint supplies names, IDs and counts, not committee
            # types or transaction dates. Preserve known registry types, omit
            # unavailable metadata rather than fabricating it from old raw rows.
            registry[key] = {**(existing or {}), **meta}

    attached = 0
    for position in data["positions"]:
        if position.get("government_level") != "Federal":
            continue
        for candidate in (position.get("candidates") or []) + (position.get("filed_candidates_not_confirmed_on_ballot") or []):
            fec_id = (candidate.get("fec") or {}).get("id")
            if not fec_id:
                continue
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
        "method": ("FEC official independent-expenditure aggregates by candidate for the "
                   f"{args.cycle} two-year cycle (not the full Senate election period). "
                   "These totals use regularly scheduled reports and exclude 24-/48-hour "
                   "notices and memo entries to avoid double counting, matching the FEC "
                   "candidate page for the same two-year selection. Recent notice-only spending "
                   "is not included; newly filed summaries may take up to 48 hours to appear. "
                   "Amendments and election-cycle attribution follow the FEC aggregate. "
                   "Amounts are independent outside spending: they are not campaign "
                   "receipts, contributions, coordination findings or endorsements, and support of "
                   "one candidate is never treated as opposition to another. This is a dated "
                   "snapshot from the FEC API, not a live feed."),
    }

    coverage = data["coverage"]
    # Coverage tracks PRINTED candidacies; provisional filings are counted once their contest is confirmed.
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
                      "federal_entries_cached": len(aggregates),
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
    runp.add_argument("--refresh-days", type=int, default=7)
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
