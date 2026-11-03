# PR #22: resume the owner's Jev review

Start here when continuing [PR #22](https://github.com/salqadri/bay-area-elections-2026/pull/22)
from another Codex project, checkout or machine. This handoff supersedes the PR's
initial v8 scoring-policy description. Keep the PR unmerged and production
unchanged unless the user asks to publish.

## November 2 selection guard

The recommendation selector now preserves signed source observations and N/A
candidate context. Opposition-only records from the existing recommendation
sources cannot turn into automatic support recommendations. The PR's plan
withdraws Rob Stump; the local latest-score review also withdraws Rommy Kushner.
Recorded grades, score prompts and thresholds stay exact. Unassessed opponents
stay N/A, with no automatic replacement or new protest choice. Old valid choices
have explicit revalidation receipts, not relabeled Jev answers. This has not
been merged or deployed. Read [the selection contract and replay commands](RECOMMENDATION_SELECTION.md)
before updating a plan or rebuilding the local preview.

## November 2 questionnaire and narrative corrections

The ACJDC refresh adds 53 candidate-authored evidence items from 33 questionnaires
and fills 11 missing official endorsement records (31 current first-party records
in total). Primary/general phases, carry-forward, and ranked preferences remain
explicit. Question preambles, blank answers and inapplicable AB 715 questions are
not converted into candidate positions. The club's own mission supplies its
pro-Israel organization context, with the owner's requested low endorsement-only
weight. Current input state is **candidate-evidence-v24-acjdc-questionnaires**.
[Answer-by-answer report and replay details](../research/questionnaires/acjdc-2026-11-02/README.md).

The owner subsequently requested a targeted rerun of these **44 candidates**, listed
in `state-changes.json`. All 44 now have complete v9 evaluations with unchanged
saved thresholds. **26 letter outcomes change, including 20 N/A → graded**; four
remain N/A. Old exact evaluations remain intact. This is a held review, not a
production publication. [Exact run and comparison](../research/gaza-grading/acjdc-refresh-2026-11-02/README.md).

A separate audit of 249 distinct legislative paragraphs confirms two factual
errors in held Qwen race outputs: Aisha Wahab's aligned No vote was called a
contrary item, and Ro Khanna was incorrectly described as having one contrary
vote. Both receive explicitly labeled factual editorial corrections bound to
unchanged score requests, added as portable review outputs. The original Qwen
text and raw Jev history remain intact. The race writer now gets complete compact
source state, including response plus alignment, rather than a shortened LLM
candidate narrative. [Audit scope, limits and before/after files](../research/reviews/summary-alignment-2026-11-02/README.md).

## Current working settings

- Latest owner-saved questions: [`criteria-pro-palestine-v9.json`](../research/gaza-grading/criteria-pro-palestine-v9.json).
  Exact questions SHA-256: `26fc5b5fda84b99c3f113eec6adb00551cf067c89b3b35d8e62c2df9285d0bc7`.
- Saved thresholds: [`score-grade-mapping.json`](../research/gaza-grading/score-grade-mapping.json).
  Inclusive upper bounds **F 0.74, E 1.4, D 2.3, C 3.3, B 4.4; A ends at 5**.
  Minimum `evidence_score` **0.22 / 1**, with `require_issue_observation: true`.
- Only `pro_palestine_score` and `evidence_score` are requested. The sole letter
  grade, `pro_palestine_score_grade`, derives from the score and saved thresholds.
  The old `gaza_grade` is retired from new calls, visible results, comparisons and
  future explanation inputs. Exact historical requests/responses are retained.
- New state version: **candidate-evidence-v24-acjdc-questionnaires**; the playground
  adds `-local-federal`. California Jewish Democrats appears under
  `organization_context` with identity only:
  > California Jewish Democrats is the renamed Democrats for Israel California (same organization; dfi-ca.org).
  Its actual Support/Strong Support tier remains in the focused endorsement
  observations, as does CAIR Action's original tier. No CJD scoring directive or
  endorsement-offset instruction is injected into state. The editable prompt
  determines weighting. Do not restore `zionist_endorsement_context`.
- CJD old-name aliases normalize to **California Jewish Democrats** in new inputs.
  Fiona Ma’s duplicate campaign claim collapses into CJD’s own **Support** rating;
  no rating is promoted to an endorsement. Distinct phases, historical records,
  opposing directions and differing explicit tiers remain. Raw sources and the
  archived v22 evaluations stay exact. No score was rerun for this normalization.
- The existing low-weight SB 403 caste channel and source evidence are retained.

## Saved results: two prompts, not one homogeneous rerun

The portable review bundle is
[`playground-review-2026-10-30/manifest.json`](../research/gaza-grading/playground-review-2026-10-30/manifest.json).
It hashes seven exact local run files, without credentials or machine-specific paths:

1. **Full roster**, `20261031T012958Z-2ce361f8`: all **1,296 candidates**, zero
   errors. Started **October 30, 2026, 6:29 p.m. Pacific**, completed 6:33 p.m.
   Its exact questions are also saved as
   [`full-roster-criteria.json`](../research/gaza-grading/playground-review-2026-10-30/full-roster-criteria.json).
   Questions SHA: `87822882ad08a3bc0e7016c07c01c64ef46c70d8502ee564ca2f757213669f3d`.
2. **Later Eleni Kounalakis test**, `20261031T013913Z-e318f9d2`: October 30,
   **6:39 p.m. Pacific**. This is the latest saved prompt and becomes default v9.
   The sole change from the full-roster prompt is the addition to score criterion 0:
   **“Don't hold statements made in October 2023 against them though.”**

3. **October 31 Matt Haney update**, `20261031T172141Z-cd7e89bf`: owner-confirmed
   genocide statement from the official CAIR-SFBA video, new evidence **GE-1613**.
   One requested v9 evaluation: **A 4.45 / 5**, confidence **0.61**, evidence
   **0.99 / 1**, replacing his prior local **C 2.89 / 5**. Refreshed Qwen candidate
   and race narratives are held alongside the result.
   [Source qualification, results and both summaries](reviews/matt-haney-genocide-2026-10-31.md).

4. **November 2 ACJDC refresh**, `20261103T034523Z-3d5574c2`: 44 candidates
   across 36 races, zero errors, v24 source state, saved v9 prompt and thresholds.
   Of their previous results, 43 used the earlier roster prompt. Do not attribute
   differences exclusively to new evidence. Exact scores and comparisons are held.

The first three runs use v22 input states; the November 2 Gavilan runs use current v23 input states. The October 31 Haney update supersedes one additional full-roster result.
After the November 2 ACJDC batch, latest-per-candidate contains **1,249** results
with the full-roster prompt and **47** with the newer v9 prompt. Under the saved
mapping its distribution is **A 123, B 41, C 21, D 35, E 80, F 123, N/A 873**. These are **held review results**, not a new public score publication.
The original handoff made no extra evaluations; subsequent owner requests
authorized the targeted Haney, Gavilan and 44-candidate ACJDC refreshes.

Do not rewrite request hashes, replace the prompt attached to old answers, or
claim that all 1,296 candidates used the newest prompt. If the user later wants
one prompt for publication, the other 1,249 candidates still need evaluation
under that exact prompt. The publication validator rejects mixed question JSON.

## Restore and launch from a fresh checkout

From the repository root, after saving any unrelated local work:

Use Python 3.10+; restoring and serving saved results needs only its standard
library. Node.js is needed for the JavaScript checks. The full release gate also
needs `pdfplumber`, as documented in [maintenance setup](MAINTENANCE.md).

```sh
git fetch origin refs/pull/22/head
git switch --detach FETCH_HEAD
python3 scripts/restore_jev_playground.py --work-dir .research/jev-playground-pr22
python3 scripts/serve_jev_playground.py --work-dir .research/jev-playground-pr22
```

Open **http://127.0.0.1:8787/**. No key is required to review saved evaluations.
For new runs, supply a local `--jev-key-file /path/to/key` or `TYPESAFE_API_KEY`;
never commit credentials. If the port is occupied, reuse the existing playground
or use `--port 8788`; do not interrupt an active evaluation.

The restore command validates file hashes, exact requests/responses and candidate
identities. It preserves existing local runs and thresholds; use a fresh work
directory for the exact committed settings. Repeating restoration is safe.
The earlier one-candidate experiments remain on the original machine; the seven runs needed to reproduce the latest result of every candidate are bundled.

The editor deliberately follows the selected candidate's saved prompt. Select
Eleni Kounalakis or press **Restore defaults** to load the latest v9 prompt for
another candidate; other candidates initially show their actual full-roster
prompt. **Current input** previews the next generated state; **State JSON** shows
the exact state used for the displayed saved answer. The generated state is
read-only. No run is started just by opening or restoring the playground.

## Publication boundary and next work

The PR's public score metadata, attached explanations and race picks remain at **2026-10-30.1 / jev-2026-10-30-v8-1**, with the earlier
**0.7** F upper bound and v8 questions. The current review/default F upper bound
is **0.74**. Changing defaults does not alter that frozen publication. GE-1613 and a corrected AD-17 factual race paragraph are added to the PR readers;
the newer score and candidate-grade explanation remain held. The v9 score publication remains held; independent factual corrections have been published on main and the deployed sites. The separate TALL
Firebase guide remains local-only and must not be added to this repository.

Future publication must freeze the approved results and mapping, regenerate or
invalidate explanations and race rationales affected by those results, refresh
recommendations, rebuild the readers, and pass the release gate. Do not attach
old explanations to newly scored candidates. Do not merge, deploy, rerun Jev or
run a paid model batch merely to resume this review.

Useful offline checks:

```sh
python3 scripts/check_playground_restore.py
python3 scripts/check_jev_playground.py
node scripts/check_jev_playground.cjs
python3 scripts/check_organization_context.py
python3 scripts/check_release.py
```

Use Serper.dev exclusively for any web searches, as requested by the owner.
This review restore and its checks make no research or model API calls.

## November 2 targeted source refresh and Qwen status

Shahida S. Merchant (CA2026-153, Gavilan CCD Trustee Area 3) now has the owner-
supplied verified campaign website and five source-quoted general platform
priorities. The registered November 2 review and source packet are under
`research/reviews/shahida-merchant-campaign-2026-11-02.json` and
`research/campaign-issues/shahida-merchant-2026-11-02/`. Her current generated
state gains only `campaign_platform_points`; no Palestine statement was found
in the bounded HTML check. The linked video was not transcribed. No Jev score,
letter grade, frozen request, prompt, threshold or race choice was changed.
This factual patch was also applied independently to latest main and selectively
to the TALL production snapshot; PR #22 remains unmerged.

The local Qwen refresh finished October 31 at 8:42 p.m. Pacific: **401/401
candidate explanations succeeded; 154/176 race summaries succeeded; 22 race
summaries failed the endorser/source-policy validation after retries**. There
is no active worker. Outputs remain held for review under ignored
`.research/summary-refresh-v9-2026-10-31/`; they have not been attached to
production. Do not call the entire batch complete or silently publish failed
or outdated narratives. The status was checked against all 555 saved output
artifacts on November 2.

## Gabriel Gutierrez community confirmation — November 2

GE-1614 adds the owner-relayed report from local Muslim community members that
Gabriel Gutierrez supports divesting from Israel (CA2026-153). It is explicitly
a community report, with November 2 as receipt/observation date, not an asserted
statement date or vote. The source record, generated Jev state and refresh
note are in `research/community-reports/`. Public main and TALL receive the
same narrow factual addition independently of this unmerged PR. Exact saved
evaluations, prompts, thresholds, letter grades and recommendations are unchanged.
The current input contains the new report; archived State JSON stays exact.
Re-evaluate him when requested, then refresh his candidate explanation and the
CA2026-153 rationale. The existing Qwen outputs predate this new report.

## Earlier November 2 Gavilan race evaluations and summaries

Initially, before the USAMPAC correction below, both CA2026-153 candidates were re-evaluated under the exact latest v9 prompt
and saved thresholds: Gabriel Gutierrez **A 4.94 / 5**, confidence **0.99**,
evidence **0.94 / 1**; Shahida S. Merchant **N/A**, evidence **0 / 1**.
The two exact runs are now part of the portable review bundle (six runs total, including the superseded pre-USAMPAC Merchant check).
The first three requests remain exact. At that point, latest-per-candidate contained 1,292
full-roster-prompt results and four v9 results; letter distribution is unchanged.
Qwen regenerated both candidate paragraphs and the race comparison, preserving
community-report attribution and making no Palestine inference from Merchant’s
college platform. [Full results and prose](../research/gaza-grading/gavilan-refresh-2026-11-02/README.md).
These outputs supersede the earlier held CA2026-153 summaries for local review.
PR #22 is unmerged; these two scores/summaries have not changed the frozen
public score publication or the live TALL snapshot.

## Earlier USAMPAC correction supersedes the initial Merchant N/A

The owner then confirmed that USAMPAC endorses Shahida Merchant and is a Muslim
community organization aligned on Palestine. The new reported endorsement is
in both research checkouts, with its context in
`owner-organization-context-v1.json`. USAMPAC’s public directory returned an
error, so the record is not mislabeled as a retrieved first-party statement.
Only exact owner-confirmed aliases are included; candidate religion is not
inferred. State versions add `-owner-org-context` for new requests.

Merchant was re-evaluated with unchanged v9 questions and thresholds:
**A 4.76 / 5**, score confidence **0.87**, evidence **0.69 / 1** (evidence
confidence **0.38**). Confidence is shown, not used as an acceptance filter.
The original N/A run remains exact history; the six-run portable bundle resolves
her latest result to this new A. Gutierrez remains **A 4.94 / 5**. At that point the review
distribution was **A 126, B 41, C 18, D 29, E 70, F 119, N/A 893**.
Both are now A-graded; the existing Gutierrez race pick is retained for review
among highest-grade ties, not replaced by an invented new tie-breaking result.
Fresh Qwen prose must mention both aligned organizations and cannot reuse the
old claim that only Gutierrez has such backing. The exact questions are unchanged;
At that point, 1,292 candidates retained the roster prompt and four used v9. Scores and matching
prose are held for review, and the live sites retain their frozen score
publication. The factual USAMPAC endorsement is published separately.


## Completed ACJDC rerun and local review — November 2

All **44** changed candidates were re-evaluated with the saved v9 questions and
unchanged mapping: **26 letter changes, including 20 N/A → graded; four remain
N/A**. Exact requests/responses are the seventh portable run. Latest-per-candidate
is 1,249 earlier-roster-prompt results plus 47 v9 results; **A 123, B 41, C 21,
D 35, E 80, F 123, N/A 873**. No confidence acceptance rule was added.

Qwen produced 40 candidate and 26 race paragraphs, including a narrative-only
Kevin Park correction; explicit editorial trims and all raw drafts are preserved.
The final 33 legislative-consistency audits have no remaining flags. Race inputs
now preserve N/A context and avoid unsupported absence claims. The ICAN/American
input substring and OC Action/AROC output-boundary bugs are fixed. They affect
narratives, not exact-alias Jev scoring. Kevin Park's frozen PR rationale also
loses its unsupported Korean-organization/Israel association; no choice or grade
changes for that correction. Both research readers are rebuilt.

[Full scope, results, receipts and caveats](../research/gaza-grading/acjdc-refresh-2026-11-02/README.md).
The regenerated local TALL preview has 125 picks versus production's 122; six
picks differ, nine same-pick grades change, and 37 candidate letters change. All
198 graded candidates have matching paragraphs. Nineteen other old race rationales
remain visibly labeled and queued; do not call the entire historical corpus fresh.
The current review is held: no merge or deployment. See the report before using
the additional narrative-only `--additional-races` / `--only-races` flags on
`scripts/refresh_held_review.py`; those flags never request candidate scores.

Validation: **53/53 offline release checks pass**. Live Chrome checks pass for
the 44-row review, questionnaire evidence, N/A suppression, Kevin correction,
desktop/mobile layout, no page errors and no localhost analytics collection.
