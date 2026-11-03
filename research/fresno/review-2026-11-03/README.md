# PR #23 review — November 3, 2026

This branch prepares Fresno County coverage. **It is unmerged and not deployed.**
The review made no provider calls and changed no scoring questions, thresholds,
saved model inputs, raw answers or scores. Production remains the PR #22 release.

Reviewed original head: `9f96aeb1a5e058a4c3934bde758190e67301bd71`.
Baseline main: `e3ccd3372d96b452dd419552414a511175cb3cd2`.

## Findings and fixes

1. **Recommendation refresh reviewed and accepted.** The county import also
   regenerated 179 existing race summaries and changed four picks: US2026-033
   (no pick → Mark Warner), CA2026-136 (no pick → Sandra Weese), CA2026-241
   (Virginia Cheung → Ryan Hazelton), CA2026-242 (Leah LaCroix → Bunny McFadden).
   After reviewing examples and the prompt/context changes, the owner explicitly
   approved keeping the refresh. These choices and paragraphs are now active.
   The active selector cache matches the original PR; the reason cache retains
   that PR’s records plus the marked Aisha editorial correction described below.
   The `out-of-scope-*.jsonl` files retain their historical names as snapshots of
   the initial review; their records are no longer quarantined from active use.
2. **TALL import failed on Huron.** Confirmed write-in-only CA2026-480 has no
   printed names. `classify()` previously skipped it, and TALL rejected the
   missing recommendation record. Confirmed null-roster contests now get an
   explicit no-information/no-recommendation row. No candidate is invented.
3. **Incumbency was lost in name matching.** Dotted initials were retained while
   undotted initials were dropped; missing middle names also caused mismatches.
   Match only unambiguous county incumbent lines or explicit printed flags.
   The 28 corrected new-record flags are listed in `incumbent-corrections.json`.
   Existing saved evaluation states remain historical inputs, even where they
   predate this source correction; all 222 new evaluations remain N/A.
4. **Saved-run history could not open.** The original Fresno envelope used an
   invalid run ID and a hard-coded 20:15 UTC timestamp after the PR was committed.
   Individual completions actually ended at 16:53:44 UTC. The reviewed envelope
   uses a valid ID and that last saved completion, explicitly identified as a
   reconstructed envelope rather than an execution start. Every original row,
   including its actual completion date, remains unchanged.
5. **A prior immutable archive was edited.** The original PR rewrote
   `earlier-summaries-2026-11-03.json` to advance a publication pointer. Its prior
   bytes are restored. A separate Fresno binding copy now holds the new pointer.
6. **Import checks did not fail closed.** The parser printed count mismatches
   but still wrote output. It now rejects missing/conflicting qualified counts,
   status drift and partial rosters before writing, including with `python -O`.
   Filing counts may exceed qualified counts. Import roster/count/repeat guards
   raise errors rather than relying on assertions; repeated county imports are
   rejected instead of creating duplicates. Validation finishes before data and
   plan replacement, with rollback if either maintained-input write fails.
7. **Revalidation ignored approved release choices.** Existing owner-approved
   carry-forward receipts are now recognized by ordinary plan revalidation,
   alongside provider or legacy receipts. The review test verifies that existing
   choices survive without pretending they are new provider selections.

`extend_county_plan()` in `scripts/build_recommendations.py` checks old rosters,
grades, selection evidence and policy before preserving old rows. New contests
needing a selection decision remain withheld pending review. County additions
must not run nationwide selector or narrative phases as a side effect.

## Accepted refresh and manual correction

The owner’s follow-up instruction was to keep Hermes’s changes and manually
fix Aisha Wahab’s attribution. No new model calls were made. The original PR’s
race plan (`9f96aeb`) supplies the accepted selections, summaries and provider
records; the safe county-extension helper retains those rows while keeping the
Huron row and other source/provenance fixes from review.

CA2026-003 changes only this clause:

- Original: “As a state senator she voted No on defunding universities that boycott Israel”
- Corrected: “In Congress, she voted No on defunding universities that boycott Israel”

The rest of the paragraph is unchanged. Its final cache entry and plan summary
say `qwen/qwen3.8-27b + factual editorial correction` and retain the original
provider prompt hash, original text hash, source commit and exact replacement.
The original unedited output remains earlier in the cache. A normal cache reuse
therefore keeps the correction without rewriting provider history.

The PR #22 `rationale-refresh-2026-11-03.json` queue is historical and superseded
for the current accepted race plan. Do not replay it against this review: its
publication binding and some selected names are older. Candidate-grade
explanation refresh queues are separate and unchanged.

Why the refresh differed from production: earlier PR #22 changes replaced a
shortened candidate assessment/evidence digest with the full structured Jev
state, and replaced the earlier recommendation-writing instructions with a
factual-comparison prompt. Production intentionally retained older paragraphs.
The original Fresno PR did not itself change that code; its broad generation
picked up the current path. All 179 refreshed prompt hashes match reconstructed
current prompts; none matched the old cache’s prompt hash. Aisha, Matt Haney,
Kevin Park, Ro Khanna and Becerra’s structured candidate states were unchanged
between main and the original Fresno PR. This distinguishes earlier pipeline
changes from newly added Fresno evidence or altered candidate grades.

## Current prepared artifacts

- **County proof:** 106 on-ballot contests (93 new + 13 extended existing records),
  114 excluded determinations. Eleven extensions were already Bay Area records;
  two were previously nationwide congressional records. BOE District 1 is new;
  BOE District 2 is unchanged.
- **Dataset:** 754 positions, 564 confirmed, 691 seats, 1,516 printed entries,
  190 excluded determinations and one confirmed contest without printed names.
- **Plan:** 737 rows (564 confirmed + 173 excluded with names), including 198
  new no-information rows and **179 selected races**. The owner-approved 179
  rewritten race summaries and four changed picks are retained. The accepted
  existing rows are bound by hashes in `approved-race-refresh.json`.
- **Scores:** 1,518 candidacies: 1,296 prior rows unchanged and 222 new N/A
  results. A 119 / B 46 / C 21 / D 34 / E 84 / F 121 / N/A 1,093. Fresno uses
  existing owner criteria v11; previous per-candidate variants stay unchanged.
- **Publication:** `research/gaza-grading/published-2026-11-03-fresno-reviewed.json`
  (`jev-2026-11-03-fresno-reviewed`). New-row evaluation run references point
  at the registered reviewed batch; requests and answers do not change.
- **History:** `research/gaza-grading/fresno-county-2026-11-03/reviewed-run.json`
  (`20261103T165344Z-0f36bd7d`). The portable manifest registers this envelope.
- **Earlier text binding:** `research/gaza-grading/earlier-summaries-2026-11-03-fresno.json`.
  Earlier text and its original request bindings are unchanged.

The original Fresno `run.json` and `published-2026-11-03-fresno.json` remain
audit-only originals. Do not overwrite them, edit their requests, or register
the original future-dated envelope as a fresh run. `review-receipt.json` records
baseline hashes; `../import-manifest.json` records stable IDs and proof mapping.

The five-county Bay Area batch is unchanged. Fresno finance, endorsement,
platform and Gaza evidence enrichment remains a separate follow-up.

## Validation and resuming review

Full offline release gate: **54/54 PASS**, including the new `check_fresno.py`.
It verifies proof counts, failure without output on truncated input, incumbent
ambiguity, preservation of maintained choices/prose during county extension,
approved refresh hashes and editorial provenance, historical release receipts,
immutable archives, unchanged raw grading results, reproducible envelope
reconstruction and portable history lookup. Both research readers were rebuilt.

The separate TALL builder's `project()` and `apply_editorial()` integration
probe accepts **435 contests** and all **11** existing editorial exceptions.
This was a read-only integration check; it did not sync, deploy or alter TALL.

From the repository root, these commands need no credentials or model calls:

```sh
python3 scripts/check_fresno.py
python3 research/fresno/jev-fresno-run.py --plan-only
python3 scripts/check_release.py
```

Use a Python environment with the release gate's PDF dependencies installed.
On the review Mac, the full gate used the bundled Codex Python runtime. Keep
credential files and `.research` working histories out of Git.

The one-time Fresno import/publication scripts already have their outputs in
this branch; rerunning is unnecessary. They refuse repeated imports or existing
archive output paths. `--plan-only` is safe; invoking the grading script without
it requires explicit provider credentials and performs paid evaluations.
`regen-samir-reasons.py` records the original narrative refresh’s retries;
its outputs are retained in the accepted cache. It is not a step of the corrected
county-import workflow. No more model calls,
merge, TALL sync or deployment are needed to resume this review.
