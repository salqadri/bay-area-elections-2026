# Research and development handoff

## Latest update — October 9, 2026: Vote for Peace and AROC Action

Schema **1.15** publishes **386 recommendation records on 197 candidacies** and **245 Gaza evidence items under 82 candidacies**. This pass adds 27 Vote for Peace Ally classifications, 8 oppositions, 29 AROC endorsements, 6 explicit endorsements discovered through linked sources, and 14 attributed guide observations. See [the review](reviews/2026-10-09-peace-guides.md) and [complete source-card manifest](../research/endorsements/peace-guides-2026-10-09.json).

All 152 Vote for Peace cards and 44 AROC cards have dispositions. Five matched Neutral entries produce no recommendation. Panetta remains primary. Five AROC candidate endorsements outside the current roster and ten measures remain in the manifest, without creating ballot contests. CAIR's official labels remain intact; Peter Ortiz is Preferred in both sources. Track AIPAC's three existing endorsements were reverified, not duplicated; a generic badge or funding claim cannot establish its opposition.

Guide assessments use `date_method: source_observed`, the actual inspection date, and a required date note. Both readers label the unknown original date. They are attributed secondary claims, not independently checked funding totals, roll calls or historical statement dates. The importer and publication guard preserve reviewed records and reject unintended changes. Run `check_peace_guides.py` with the full release suite. Candidate rosters, parties, FEC, election-wide dates and prior Gaza evidence are unchanged. Historical sections below retain their original counts.

## Earlier update — October 9, 2026: CAIR Action source correction

The current publication is schema **1.14**, with **316 records on 190 candidacies**: 266 endorsements, 18 preferences, 6 recommendations, 25 other support observations and 1 opposition. This replaces the earlier 15 CAIR secondary reports with **95 recommendations from the supplied official Explore capture**: 76 Endorsed, 18 Preferred and 1 Opposed. Both pages explicitly label negative recommendations, including Marc Cooper's **Opposed by CAIR Action** record.

Read [the correction report](reviews/2026-10-09-cair-action-correction.md) and `research/endorsements/cair-action-2026-10-09.json`. All 200 captured cards are accounted for: 95 published, 2 duplicates, 1 held office mismatch and 102 not matched to the current printed roster. Tomara Hall's source card says District 1; the roster and campaign say Area 2. Resolve this discrepancy before publication. Do not treat the other unmatched names as proof of absence from the ballot.

The official page could not be re-fetched and the PDF was not read. Labels come from the supplied HTML capture. Its selected-election header is absent, so phase remains unspecified with a visible shared note. `import_cair_guide.py` parses captures without network/model calls and applies explicitly reviewed matches; `check_cair_guide.py` and the publication guard protect polarity, completeness, deduplication and source provenance. The former CAIR secondary layer is marked superseded. Election-wide dates, rosters, FEC records, Gaza evidence and every other publisher's records are unchanged by this correction. Historical entries below retain their original counts.


## Earlier update — October 9, 2026: targeted endorsements and publication correction

This update supersedes the earlier 741-candidacy/884-record endorsement counts. The current publication has **236 endorsement/support records on 156 candidacies**: 190 endorsements, 6 recommendations, 40 other support observations. It removes 725 unsupported imports (723 Chronicle directory mentions plus two non-endorser labels) and adds 77 reviewed records covering the requested publishers, Japra/Americans4Hindus and the actual Chronicle editorial list.

Read [the review report](reviews/2026-10-09-targeted-endorsements.md) and the `targeted-2026-10-09.json` source/record/follow-up manifest. The old collector export is filtered, with 1,167 original observation IDs preserved in quarantine; the curated layer is separate. Schema 1.13 and both readers distinguish support ratings, primary/general stage, campaign claims and secondary reports. The collector has shared publisher queries and stricter extraction; a publication guard prevents known bad imports from returning. The apply script is idempotent and refuses conflicting newer records.

CAIR's official dynamic guide and AIPAC's candidate portal remain unreadable from the research environment. CAIR secondary listings are **reported support, original tier unknown**. Hindu American PAC's Murali Srinivasan and Yang Shao entries remain held for cycle/office mismatches. Regional campaign claims still need official confirmation. The remaining older endorsement data is not comprehensively audited. Further work should resolve these source-level gaps, not rerun enrichment across every candidate. The optional Jev task was canceled by the owner.

The election-wide October 4 research date, candidate rosters, party labels and FEC records were not refreshed by this targeted endorsement review. The README has current coverage; historical session entries below retain their original counts.


**Prepared October 6, 2026 (America/Los_Angeles).** This is a handoff of existing work, not a new verification of election facts. Recheck the JSON and Git history before using these numbers as the current state.

The baseline implementation is commit `f2e15251ca44f2baf50e141fd14d77d09f480ed8`, which added address autocomplete. This documentation may be followed by additional commits. The repository contains the maintained project; no prior chat conversation or scratch files are needed to work on it.

## Current state

| Item | Handoff baseline |
| --- | --- |
| Election | November 3, 2026 California general election |
| County scope | Alameda, Contra Costa, San Francisco, San Mateo, Santa Clara |
| Ballot research snapshot | October 4, 2026 |
| FEC research snapshot | October 6, 2026; individual financial coverage dates differ |
| Schema | Inventory version 1.11, Draft 2020-12 (`x_url`, `secondary_x_url`, `campaign_url`, `gaza_evidence`; evidence `date` is required and calendar-valid, with optional `date_method`/`date_note`) |
| Endorsements (new) | **741 of 869 printed candidacies** carry cited current-cycle `endorsements` records (884 total; schema 1.12 `$defs.endorsementRecord`) from verified endorser pages, collected October 9 via `scripts/research_endorsements.py`; snapshot at `research/endorsements/endorsements-export-2026-10-09.json`. Ongoing: bot-walled platforms and ~128 candidacies still uncovered |
| X accounts / sites | 135 printed entries (135 distinct names) with X URLs; 27 are explicitly probable matches. 10 secondary X URLs; 383 candidate-specific campaign/official URLs retained after five generic homepage claims were removed. |
| Gaza stance research | This review branch retains 231 items for 81 candidates after 44 manual rewrites and 69 documented quarantines (the 69th, Chan GE-0019, failed the deterministic relevance gate on post-merge reconciliation). All 300 input summaries have dispositions. Jev assessment is pending; see the post-enrichment review. |
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
6. **Gaza stance evidence research — base and enrichment passes complete.** All five counties have had a base pass *and* an `--enrich` depth pass under the post-audit acceptance rules (113 printed candidates, 300 dated ungraded items; schema 1.11 requires dates plus `date_method`). Remaining opportunities: targeted follow-up on high-salience statewide/federal candidates whose dossiers proposed unresolved follow-ups, and manual review of `ledger/undated_quarantine.json` entries that a human could date from context. Run passes via `/workspace/gaza-stance-research` (see its README and AGENTS.md "Gaza stance evidence research"), then re-run `merge_gaza_evidence.py`, rebuild and run the full suite. Grading (A–F) is a separate future step that only begins on explicit user instruction; until then no verdicts enter the data.
7. **Improve maintainability where it helps research.** Candidate opportunities include a reproducible coverage-summary updater, per-record provenance dates, a standard JSON Schema validation gate, a schema for the estimate export, browser smoke checks and CI. These are not implemented promises. Add them in small reviewable changes and avoid making fixture success stand in for factual accuracy.

## Known research exceptions to preserve

- The full Contra Costa August 27 final on-ballot proof PDF could not be retrieved during the prior research. Some official and corroborating material was available, but the county is not certified exhaustive. Retain uncertainty until the actual final evidence is checked.
- EBRPD Ward 7 has confirmed ballot appearance but conflicting roster evidence. Its provisional names are stored separately; do not promote them all to a final roster by copying the filed list.
- Jeff Frese and Charles Hoelter have `fec.receipts: null`, with explanatory notes. These are unknown totals, not zero.
- Scott Wiener's FEC summary has a coverage period beginning in 2023. Preserve the reported period and exception note; do not relabel the same amount as a 2025–2026 subtotal.
- The inventory currently excludes ballot measures and is not a complete official sample ballot. Missing/unverified local IDs and unresolved scheduled elections are separate limitations.
- Some prior exclusions are described in notes/limitations rather than retained as position records. When establishing exhaustive coverage, explicitly audit what is absent as well as what is present.

## Session refresh — October 9, 2026 (second external review: acceptance rules + provenance)

A second Codex review of `6ba1537` drove fixes beyond the first audit; all items below are implemented and re-validated against the full dataset:

- **Co-signature/attribution rule hardened** (`validate_evidence.py`): collective statements, current rosters and navigation do not establish individual signature — contemporaneous membership plus explicit attribution required. Quarantined under it: Pellerin's 2018 Jewish Caucus co-signature (she took office Dec 2024), Ahrens GE-0415/GE-0416-class collective-council claims, Le's "unanimous council statement" item, Dalton minutes-attendance re-add, Harder aggregate-scorecard item. Pellerin GE-0309 was **verified and kept** — the caucus page itself names her among the signatories of the Jan 2024 letter (contemporaneous + explicit).
- **Campaign URLs**: repaired to full verified paths where the candidate page lives under a path (Lin `linktr.ee/votemikelin`, Yip-Chuan `/my-site-1`, Woods `/sites/joel-woods/`, Guardado `linktr.ee/guardadoforccc`, Bernet rossforberkeley.com, Nowinski 2votes4changeec.com — each re-fetched live and confirmed to name the candidate). S974's provenance collision split into per-candidate sources S1083/S1084/S1085; unverifiable generic-homepage claims removed entirely (Ortiz, Roche) → **386** campaign_urls.
- **Chronology**: schema 1.10 → **1.11** adds `date_method` enum (`source_stated`, `page_metadata`, `x_snowflake`, `wayback_first_capture` = upper bound, `event_recorded`) + optional `date_note`; merge carries both; the five Wayback-bounded items carry explanatory notes. Connie Chan's duplicated 8–3 vote items all now read 2024-01-09 (the correct date).
- **Failed financial extraction**: GE-0288 (`$None`) was already quarantined in the first audit; `validate_evidence.py` BROKEN rule rejects `$None`/`nan`/could-not-retrieve artifacts and donation claims need transaction-level provenance.
- **Relevance + dedupe**: explicit Israel/Gaza/Palestine relevance regex (page-text fallback keeps paraphrased-but-valid items with a review flag — e.g. Van Le's Block the Bombs pledge); Wiener anti-trans post and Cohen Armenian-genocide item quarantined; `normalize_url()` (fragments, tracking params, trailing slash) dedupes in pipeline and revalidation.
- **Calendar validity**: `check_schema.py` now rejects impossible dates (`2026-13`, `2026-02-30`) for evidence `date`/`checked_on`; negative cases added; all current 300 items pass.
- **List semantics**: `src/ballot-page.js` appends the evidence `<details>` inside its candidate's `<li>` (was a sibling of `<li>` in `<ul>`); `check_ballot_page.cjs` asserts the nesting.
- **Documentation honesty**: README/HANDOFF now state that 27 X-account entries are "probable match, indirect evidence" per their cited sources rather than blanket-verifying all accounts.

Ledger after this pass: **300 items / 113 people**, quarantine **111**. Full suite (build --check, check_data, check_schema 37 negatives, six node harnesses) passes.

## Session refresh — October 9, 2026 (endorsements published, schema 1.12)

Codex PR #2 merged the endorsement collector; Hermes ran it live (Serper works here) to completion: all 904 planned searches, **3,671 source pages parsed** (~2,780 explicit fetch failures — bot-walled Facebook/Instagram/Ballotpedia and junk hosts, checkpointed as limitations), publisher verification registered 9 verified endorsers / 10 sources, and **1,328 accepted observations** exported. A final drain pass added zero new accepted records: the re-attached export is byte-identical to what was published, so the live site is current through October 9 collection. Integration into the public dataset:

- Schema 1.11 → **1.12**: `endorsements` array on candidates (`$defs.endorsementRecord`: endorser/kind/relation/phase/url/checked_on/optional quote; `unspecified` allowed where sources don't state kind or phase). New negative cases (bad relation, missing url) and a positive case; coverage metric `printed_candidates_with_endorsements`.
- Dataset: **741 candidacies / 884 records** attached by (position_id, name) match from the export; deduped per endorser+relation+phase. Both UIs render an "Endorsements" details block inside each candidate card/li with source links and checked dates.
- Snapshot published at `research/endorsements/endorsements-export-2026-10-09.json` (evidence.context stripped for size; full context stays in the local SQLite ledger).
- Known gaps: ~128 candidacies have no record yet; Facebook/Instagram/Ballotpedia pages are bot-walled to plain HTTP and need browser/provider imports (`research_endorsements.py import`); the review queue holds **~27.6k pending items**, overwhelmingly name-match ambiguities harvested from low-quality hosts (playpotus/civoren noise) — the right treatment is bulk reject-by-source after confirming those hosts are not credible endorsers, not per-item review.

## Session refresh — October 9, 2026 (enrichment resumed and completed)

The paused `--enrich` depth passes were resumed under the new acceptance rules (`run_enrich.sh`, ~40 min for the remaining county; Alameda/Contra Costa/San Mateo were already enriched pre-pause). **All 861 tracked people across all five counties are now marked enriched.**

- **Yield:** exactly one new candidate item (John Craig, PAUSD board) — and it was **quarantined**: no source connects the candidate to the "John Craig"/"JC Craig" author of the Gaza Memorial Quilt Substack, his campaign bio/platform never mention Gaza or the quilt, and a "coming soon" placeholder states no position anyway. Enrichment under strict rules adds almost nothing because the base pass already captured what is publicly attributable; that is the expected result, not a pipeline failure.
- Ledger unchanged at **300 items / 113 people**; quarantine now **111** (2 pipeline undated findings + this identity rejection). Re-merge produced byte-identical dataset output — no published record changed.
- Remaining opportunities are unchanged: targeted follow-up on high-salience statewide/federal candidates with unresolved dossier follow-ups, and human dating of `ledger/undated_quarantine.json` entries. Further enrichment passes have hit diminishing returns.

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


## Post-enrichment manual review — October 8, 2026 (America/Los_Angeles)

After upstream `d0ee70b`, all 300 evidence summaries were screened manually. This branch rewrites 44, quarantines 69 with original records/reasons (68 from the review plus one relevance-gate removal during external-ledger reconciliation), and retains 231 items under 81 candidates. It also repairs filtered-download coverage, displays archive-date bounds, closes the year-zero validator gap, and removes three remaining generic campaign homepage links. Core contests, candidates, and structured FEC records remain unchanged. See [the detailed review](reviews/2026-10-08-post-enrichment-review.md) and its per-item log for scope and unresolved issues.

The requested Jev pass is not complete. Serper was blocked by the execution environment and Jev's endpoint/protocol was unavailable. The packet-preparation script does not call an API. Future work must obtain source text for held title-only entries, establish ambiguous identities, reconcile the external ledger with the repository quarantine, and complete the documented model assessment. Earlier counts and “verified” wording in historical session entries below/above are snapshots, not current certification.
