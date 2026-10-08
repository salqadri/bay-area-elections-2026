# Research and development handoff

**Prepared October 6, 2026 (America/Los_Angeles).** This is a handoff of existing work, not a new verification of election facts. Recheck the JSON and Git history before using these numbers as the current state.

The baseline implementation is commit `f2e15251ca44f2baf50e141fd14d77d09f480ed8`, which added address autocomplete. This documentation may be followed by additional commits. The repository contains the maintained project; no prior chat conversation or scratch files are needed to work on it.

## Current state

| Item | Handoff baseline |
| --- | --- |
| Election | November 3, 2026 California general election |
| County scope | Alameda, Contra Costa, San Francisco, San Mateo, Santa Clara |
| Ballot research snapshot | October 4, 2026 |
| FEC research snapshot | October 6, 2026; individual financial coverage dates differ |
| Schema | Inventory version 1.10, Draft 2020-12 (`x_url`, `secondary_x_url`, `campaign_url`, `gaza_evidence`; evidence `date` is required) |
| X accounts / sites | 135 printed entries (90 people) with verified official X URLs; 10 federal incumbents add a second verified account in `secondary_x_url` (personal vs office handle); 388 with verified campaign/official websites (checked October 6–7, 2026; each has its own evidence source) |
| Gaza stance research | **114 printed candidates across all five counties** (46 Alameda, 36 Contra Costa, 25 San Francisco, 31 San Mateo, 38 Santa Clara) carry dated, linked, **ungraded** `gaza_evidence` items (316 ledger items; checked October 7–8, 2026). Every item has a date: schema 1.10 requires it and the pipeline quarantines undated findings plus audit removals with written reasons (`ledger/undated_quarantine.json`, 93 entries after the October 8 identity audit — see session refresh below). Evidence only — no grades exist in this dataset |
| Inventory | 416 researched contests; 336 confirmed, 80 unresolved |
| Confirmed seats | 439 |
| Printed candidate entries | 869; these are entries, not necessarily unique people |
| Confirmed races with missing roster | 1: `CA2026-381`, East Bay Regional Park District Ward 7 |
| OCD electorate IDs | 188, all currently convention-based; not live API validated |
| Federal finance | 22 printed candidates with FEC IDs; 20 totals, 2 unknown amounts |
| Live address checks | Census and Photon requests were blocked in the original execution environment; fixture checks passed |

The site already includes a downloadable JSON/schema, hierarchical explorer, candidate and FEC details, address-to-ballot estimates, inclusive warnings for unresolved districts and accessible autocomplete. Do not recreate these features before inspecting the existing implementation.

## Suggested next work

These are priorities for the next maintainer, not permission gates or claims that the work has already been done.

1. **Resolve final ballot inclusion and missing rosters.** Start with Contra Costa's final on-ballot proof and `CA2026-381`, then process the unresolved queue. [RESEARCH.md](RESEARCH.md) has exact source pointers and a command to list the live queue. Confirm appointments/cancellations explicitly; a sole filer is not enough evidence.
2. **Verify address services in a real browser.** Test autocomplete and Census lookups using public civic-building addresses across all five counties. Check actual responses, CORS/JSONP behavior, map vintage, mobile/keyboard interaction and failure fallback. Keep `api_validated: false` until evidence justifies a clearly scoped change; a single successful request does not validate every OCD ID or every race.
3. **Refresh time-sensitive evidence.** Check official final candidate/retention materials, qualified write-ins, FEC filings and unresolved incumbent/link assertions. Preserve printed names when campaign withdrawal does not remove them from the ballot. Revisit the two missing FEC totals and the Scott Wiener coverage-period exception.
4. **Audit local geographic coverage.** Validate convention-based OCD IDs, investigate official GIS/precinct-to-ballot sources for council, supervisor, school, college and special districts, and compare with official county ballots. Only narrow alternatives when the evidence is reliable; missing API fields must not suppress plausible races.
5. **Expand coverage to the remaining four counties.** Marin, Napa, Solano and Sonoma are the longer-term goal. Follow the code/data expansion checklist in [MAINTENANCE.md](MAINTENANCE.md); shared districts, countywide flags, FIPS mappings and hardcoded five-county text all need attention.
6. **Continue Gaza stance evidence research.** All five ballot counties have now had a base pass (125 printed candidates, 334 dated ungraded `gaza_evidence` items; schema 1.10 requires dates and the pipeline quarantines undated findings). Remaining opportunities: an `--enrich` deep-dive pass for counties beyond San Francisco, targeted follow-up on high-salience statewide/federal candidates whose dossiers proposed unresolved follow-ups, and manual review of `ledger/undated_quarantine.json` entries that a human could date from context. Run passes via `/workspace/gaza-stance-research` (see its README and AGENTS.md "Gaza stance evidence research"), then re-run `merge_gaza_evidence.py`, rebuild and run the full suite. Grading (A–F) is a separate future step that only begins on explicit user instruction; until then no verdicts enter the data.
7. **Improve maintainability where it helps research.** Candidate opportunities include a reproducible coverage-summary updater, per-record provenance dates, a standard JSON Schema validation gate, a schema for the estimate export, browser smoke checks and CI. These are not implemented promises. Add them in small reviewable changes and avoid making fixture success stand in for factual accuracy.

## Known research exceptions to preserve

- The full Contra Costa August 27 final on-ballot proof PDF could not be retrieved during the prior research. Some official and corroborating material was available, but the county is not certified exhaustive. Retain uncertainty until the actual final evidence is checked.
- EBRPD Ward 7 has confirmed ballot appearance but conflicting roster evidence. Its provisional names are stored separately; do not promote them all to a final roster by copying the filed list.
- Jeff Frese and Charles Hoelter have `fec.receipts: null`, with explanatory notes. These are unknown totals, not zero.
- Scott Wiener's FEC summary has a coverage period beginning in 2023. Preserve the reported period and exception note; do not relabel the same amount as a 2025–2026 subtotal.
- The inventory currently excludes ballot measures and is not a complete official sample ballot. Missing/unverified local IDs and unresolved scheduled elections are separate limitations.
- Some prior exclusions are described in notes/limitations rather than retained as position records. When establishing exhaustive coverage, explicitly audit what is absent as well as what is present.

## Session refresh — October 9, 2026

Work completed after the October 6 handoff (commits `c34c94d`..HEAD; recompute counts from the JSON before treating any figure as current):

- **Explorer UX fix**: candidate links (Campaign site / X / Ballotpedia) are pill chips inside the main column instead of nowrap flex siblings that squeezed names into one-letter-per-line wrapping (`src/index.template.html`, rebuilt pages).
- **Gaza evidence dates are now mandatory** (schema 1.9 → 1.10): `date` required in `$defs.stanceEvidence`; two new schema negative cases; merge refuses dateless items; pipeline resolves dates deterministically and quarantines undated findings (`/workspace/gaza-stance-research`: `date_resolvers.py`, `backfill_dates.py`, `date_first_capture.py`, `date_content_first_seen.py`, `tests/test_date_resolvers.py`). All 22 previously undated SF items resolved or removed: ledger is **97 items / 26 people, zero undated**; removals and dating methods are recorded in `ledger/date_backfill_report.json`.
- **LM Studio current config**: `qwen/qwen3.8-27b` at medium thinking with Parallel/Max Concurrent Predictions = **2** — run the pipeline with `--workers 2`; keep total concurrent model calls ≤ 4; prefer script passes over sub-agent fan-out against this endpoint.
- Docs drift fixed: README/MAINTENANCE schema version claims now defer to the dataset's `schema_version` const; obsolete ChatGPT-connector references removed.

## Session refresh — October 8, 2026 (evening)

Four-county Gaza evidence run completed overnight (`run_counties.sh` in the research directory; logs `county_run.log`, per-person progress resumable via `ledger/state.json`):

- **Collection:** Alameda (273 people), Contra Costa (210), San Mateo (181) and Santa Clara (256) base passes at `--workers 2`; every person marked done, zero LMS failures. Merge applied evidence to printed candidate entries across all five counties.
- **Post-run quality review (findings the pipeline could not catch itself):** 26 ledger URLs were `http://` and failed schema — 25 upgraded after live https verification, 1 quarantined for a broken TLS chain. Quarantine also received same-name misattributions caught by manual scan and one item whose own summary recorded no statement or vote by the person. `merge_gaza_evidence.py` now removes dataset evidence when the ledger entry is gone, so quarantines propagate on re-merge instead of lingering in the data.
- **Pipeline hardening:** a total LM Studio extraction failure now leaves the person pending for resume instead of silently marking them done with no extraction (`gaza_research.py`).

## Session refresh — October 8, 2026 (identity audit after external review)

An external review (Codex) of commit `6ba1537` found systematic wrong-person attribution and other acceptance failures. The in-progress `--enrich` run was **paused at a county boundary** (Alameda + Contra Costa enriched; San Mateo mid-pass; resume state preserved) before any enrichment merged. Response:

- **Confirmed failures quarantined with reasons**, then the *entire* ledger revalidated against new deterministic acceptance rules — not just the listed examples. Removal classes: wrong person / identity not established (Harvard speaker vs Union City trustee; SF supervisor candidate vs Illinois cartoonist; Clayton candidate vs SNP MP; Oro Loma director vs startup cofounder and Australian/UK figures; AC Transit director vs MIT student; LARPD director vs NBA legend; school-board candidate vs Spanish officials; LVJUSD candidate vs Gaza-analyst bylines), roster-inferred co-signatures (the Jewish Caucus statement page carries a *current* roster — first Wayback capture September 2024 — so May-2018 individual co-signature claims are unsupported), absence-of-evidence framed as positions ("$0 from pro-Israel PACs"), failed financial extractions (`$None`), third-party speech about (not by) candidates, attendance-only items, bare X profile URLs and month-archive citations.
- **New acceptance layer** `/workspace/gaza-stance-research/validate_evidence.py`: hard rules quarantine at add time; soft rules write to `ledger/review_flags.json` for human review without dropping the item. `revalidate_ledger.py` applies the same rules over existing output (idempotent). Regression cases in `tests/test_validate_evidence.py` encode every confirmed failure class plus known-valid examples — passing repository tests alone was explicitly insufficient because they accepted these errors.
- **Extraction prompt strengthened:** identity-first rule requiring a source link between the person and this candidate's office/jurisdiction/biography; explicit rejection of attendance, vandalism, ads-about-them, absence claims and roster-inferred co-signatures. `--enrich` is now resumable per person (`stages.enriched`).
- **Net effect:** dataset Gaza evidence coverage 125 → **114 people / 301 printed items** (ledger 316); quarantine registry 93 entries, each with a written reason. Full check suite green; enrichment resumes under the new rules.

## Working agreement

Read [AGENTS.md](../AGENTS.md), then maintain evidence and implementation together. Keep stable IDs, compact shared metadata, official party labels, `incumbent` only when true, and the user's Senate → Assembly → other-state-offices display preference. Both generated HTML files must reflect any data or source-code change.

For each research batch, record the contest IDs checked, evidence/document dates, resulting status changes and unresolved questions. Refresh this handoff after material progress so a future agent can distinguish completed work from the original backlog. Do not merely move a date forward to make stale research appear fresh.
