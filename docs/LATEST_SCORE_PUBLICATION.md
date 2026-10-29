# Latest score publication — October 28, 2026

Publication **2026-10-28.5** (current) completes the Hermes follow-up below: all **398**
letter-grade candidacies now carry fresh Qwen explanations generated from their exact
frozen v7 requests under summary-prompt-v3 (`research/gaza-grading/explanations-2026-10-28-latest.json`,
responses in `research/gaza-grading/responses-2026-10-28-latest/`), and the **898** N/A
entries use the editorial insufficiency note. The race-recommendation layer moved into
both readers with fresh Qwen why-paragraphs for all 151 picks; the standalone page and the
old race-only-ID summary cache are retired. See [CANDIDATE_RECOMMENDATIONS.md](CANDIDATE_RECOMMENDATIONS.md).
Sections below describe publication 2026-10-28.4.

Publication **2026-10-28.4**, schema **1.30**, publishes the owner's saved complete
run `20261029T043045Z-42f63b2f` (UTC), without rerunning candidate scorecards.
All **1,296 active candidacies / 471 races** have successful evaluations, zero
errors, one exact prompt, and inputs identical to the current v18 state builder.
The 68 excluded inventory races remain outside candidate scoring.

## Exact saved prompt and thresholds

- [v7 questions](../research/gaza-grading/criteria-pro-palestine-v7.json) preserve
  the rerun's exact JSON. Relative to v6, the evidence question says
  "recommended by Muslim community" instead of "part of the Muslim community".
  The other questions and criteria are unchanged. CLI/server defaults now use v7.
- Saved upper bounds, inclusive: **F 0.7, E 1.4, D 2.3, C 3.3, B 4.4**; larger
  eligible scores are A. Minimum evidence is **0.22 / 1**, inclusive.
- `require_issue_observation: true` prevents identity-only or unrelated-platform
  inputs from qualifying. Confidence is shown but never used as an acceptance gate.

Counts: **A 120 · B 44 · C 12 · D 33 · E 66 · F 123 · N/A 898**.
There are **398 displayed letter grades**, 26 changed grade labels.
Every saved request and raw answer is retained; no candidate source research,
finance, endorsements or public evidence was changed by this publication.
The CAIR Action / Vote for Peace recommendation checks pass: no directional
recommendation in the saved input has an N/A grade.

## Immutable score archives

- [Published requests and answers](../research/gaza-grading/published-2026-10-28-latest.json),
  ID `jev-2026-10-28-latest`.
- [Source-bound candidate explanation queue](../research/gaza-grading/explanation-queue-2026-10-28-latest.json).
- [Grade distribution and all 26 grade changes](../research/gaza-grading/publication-review-2026-10-28-latest.json).

The full batch completed at `2026-10-29T06:08:57+00:00`; the publication date
is October 28 in the owner's local timezone. Historical score, request and
explanation archives are preserved exactly.

## Hermes follow-up: candidate explanations

The owner explicitly chose **publish scores now; queue explanations for Hermes**.
The new publication has no candidate explanation layer. Both main readers show
current grade badges and source evidence, without old paragraphs attached to new
scores. N/A candidates continue to have no political explanation panel.

Use the new queue and published archive above. Each item binds candidacy identity,
roster and exact request SHA. Generate fresh explanations for the **398 eligible
letter-grade candidates** using the complete frozen record, v7 rubric and recorded
answer. If the importer requires all 1,296 entries, use non-political insufficiency
notes for N/A archive entries, which the readers never render. Follow
`summary-prompt-v3.txt` and `summary-policy-v3.json`: assess all supplied evidence,
retain stated intentions and accurate chronology, give JStreetPAC little weight,
and omit missing-record disclaimer padding. Keep Hermes's Qwen defaults; no
GPT model was added to the repository's generation configuration.

The prior owner-approved Khanna paragraph remains in the historical explanation
archive. It has not been silently rebound to a new scoring request.

## Refreshed race recommendations

[Current plan](../research/candidate-recommendations/recommendations-2026-10-28-latest.json)
uses the current dataset and score publication. Counts over all 539 inventory races:
**12 community-rule picks, 139 Jev picks, 103 no-good-candidate, 285 no-information**.
Five category changes follow directly from the updated grades. Seven selected
names change overall: two previous picks become no recommendation, and five tied
grade races receive different Jev choices. The exact selector requests and answers
are [archived separately](../research/candidate-recommendations/jev-answers-2026-10-28-latest.jsonl).
There were 70 multi-candidate calls and 69 deterministic single-graded-candidate
selections; these calls choose among existing grades and do not rerun scorecards.

The selector now follows the documented **published-letter-grade-only** policy.
Previously, its code also supplied a truncated evidence digest despite the docs
saying grades only. Cached choices previously matched only race IDs; they now
require the exact request and SHA, and stale rosters/grades fail the build.
Offline builds need no API key. Provider calls accept `JEV_API_KEY` or
`--jev-key-file`; no machine-specific credential path is required.

Old race paragraphs are also withheld. The plan's `pending_summaries` lists the
**151 recommended races** requiring fresh Qwen paragraphs. Generate them after
candidate explanations so they can reuse the current assessments if appropriate;
do not restore the old race-only-ID summary cache. Future summary caches bind
the exact prompt hash. Historical plans and caches remain unchanged.

```sh
# Rebuild the already-frozen current page without provider calls.
python3 scripts/build_recommendations.py build
# Validate current dataset/plan/page bindings and stale-cache regressions.
python3 scripts/check_recommendations.py
```

For a future score publication, use `refresh` with new versioned `--plan`,
`--jev-cache` and `--summary-cache` paths. It reclassifies current races, refreshes
only unmatched Jev choice requests, and publishes without stale summaries.

## Verification

All **49/49 offline release checks pass** against the exact published dataset,
including immutable score projection, recommendation/page bindings, stale-cache
regressions, source/endorsement consistency and both readers. The separate
recommendations display check also passes. Headless Chrome verifies publication
2026-10-28.4 in both readers, Liccardo D (2.18 / 5), 539 recommendation cards,
no stale candidate/race paragraphs and no uncaught browser errors. The local
playground was restarted while idle and verifies v7 defaults, 1,296 completed
results, zero errors and the unchanged saved thresholds.
