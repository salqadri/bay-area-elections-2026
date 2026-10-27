# Local Jev playground

The playground runs on this computer, separate from the GitHub Pages readers.
It includes **all active candidates tracked in this repository**, including
nationwide House, Senate and governor races and every active contest serving
Alameda, Contra Costa, San Francisco, San Mateo or Santa Clara County. The full
catalog currently has **1,296 candidacies / 471 races**. **Run Bay Area** targets
**877 candidacies / 340 races** serving the five counties. Shared races appear
once; separate candidacies and roster types remain distinct.

County coverage includes local, district, state and judicial ballot contests,
including statewide contests serving the counties. Shared county races and
House/county overlaps appear once; separate candidacies for the same person
remain distinct. Excluded races stay out; printed, provisional and
qualified-write-in rosters remain distinct (the current snapshot includes one
local qualified write-in). No additional contests are discovered.

## Start

From the repository root, with Python 3.10+:

```sh
python3 scripts/serve_jev_playground.py --jev-key-file /secure/path/jev-key
```

Open **http://127.0.0.1:8787/**. `TYPESAFE_API_KEY` can replace `--jev-key-file`.
The key stays on the local server; it is never sent to the browser, included in
an export, or written into this repository. Without a key, stored results still
load and remain inspectable. `--port`, `--dataset` and `--work-dir` are available;
the server always binds loopback, never the network interface.

GitHub Pages does not serve the local API. Jev rejected a preflight from the
Pages origin, and the owner chose a local test page instead of deploying a relay.
The playground adds no public API or main-reader UI. Its implementation is merged in PR #14; the current canonical dataset includes the source refreshes in PRs #15 and #16.

## Use

1. The page opens **Latest per candidate**: the most recent successful saved
   evaluation of each current candidacy, seeded by the stored 187-House baseline.
   Evaluate A, then B, then select A again: A’s answer remains available, including
   after reloading the page or restarting the server. Candidates with no saved
   evaluation show **Not evaluated yet**. Nothing calls Jev merely by opening the
   page; saved runs are never overwritten. The editor loads the displayed
   evaluation’s saved questions; **Restore defaults**
   loads the owner’s October 27 rubric (`pro-palestine-v5`).
2. Use the candidate picker or previous/next arrows above the workspace. On
   desktop, the Monaco question editor and selected candidate's answers sit
   side by side, with Run controls always above them. On mobile, **Questions**
   and **Results** tabs share the same controls; running switches to Results.
   The textarea fallback works when the pinned Monaco CDN is unavailable.
   The **County** filter above the workspace applies to the candidate picker,
   previous/next navigation, race browser and CAIR comparison. Choose one county,
   **All 5 Bay Area counties**, or **All tracked candidates** including nationwide
   House contests. Shared races appear once in the combined view. This is a review
   filter; **Run Bay Area** still evaluates all five counties.
   **View candidate on election site** opens the corresponding race in the public
   explorer, filtered by the selected candidate’s name and including all roster
   statuses. The public explorer displays that candidate within the race’s roster.
3. Edit the questions, then press **Run selected candidate** or **Ctrl/Cmd +
   Enter** to evaluate exactly that candidate. Each iteration is saved separately.
   Reload restores the selected candidate and county, and loads the exact prompt
   used for that candidate’s displayed saved evaluation. With no unsaved edits,
   selecting another evaluated candidate loads that candidate’s saved prompt.
   Edited questions (including invalid JSON) are preserved across candidate changes
   and result polling, including after evaluating the edited prompt. **Load saved prompt** explicitly restores the selected
   evaluation’s questions; **Restore defaults** loads the preferred owner rubric (`criteria-pro-palestine-v5.json`).
   Drafts stay in the current page session; reloading returns to saved questions.
   For an ungraded candidate, the current editor draft is retained. **Run Bay Area (877)**
   evaluates only the five-county group with the current question text.
   **Run full roster (1296)** includes every active tracked candidate, including nationwide House, Senate and governor races.
   Each action takes a fresh snapshot of current data; a regional batch is labeled
   **Bay Area** in progress/history and downloads. Up to three Jev calls run
   concurrently; `choice`, `score` and yes/no `noul` questions can be renamed/added.
4. The selected response shows each question key/instructions, answer, type and
   confidence. Choice rows preview the leading returned probabilities; expand
   a row (or **Expand all**) for all options/score levels and their criteria and
   probabilities. **Find in questions** takes you to the editable question.
   Probabilities and confidence are separate. For `noul`, the answer is the
   probability of true, with no invented confidence. There are **no acceptance
   cutoffs or hidden low-confidence answers**.
5. **Inspect generated state & raw JSON** opens the read-only State JSON,
   Answers JSON and Full request with SHA-256. It is collapsed by default.
   Editing a prompt never changes the instructions or state attached to an
   existing result; a visible notice identifies answers from a different saved
   prompt. Latest results can use different prompts: each candidate displays their
   evaluation time, and the inspector/export retains their exact saved request,
   answers and hash. A stale-input notice refers to that candidate’s saved evidence.
   Failed, stopped or interrupted retries keep the previous successful answer and
   show an attempt notice. Unevaluated candidates show only an input preview.
6. **Browse all races** opens the state/district groups and search/state
   filters. Selecting a card brings that candidate into the workspace. Races
   remain sorted by state name and numeric district number.
7. **Saved evaluations** defaults to **Latest per candidate**. Choose an individual
   run to inspect that immutable experiment alone; candidates absent from it are
   not silently filled with other runs’ answers. Returning to Latest preserves the
   current editor draft. JSON downloads preserve exact questions, model alias and
   returned model, frozen states, request hashes, answers, confidence/probability
   distributions, errors, cancellation status and dataset snapshot hash.

Runs are stored under ignored `.research/jev-playground/runs/`. Requests for each
run are also saved in its local cache. Each Run makes fresh calls, even when the
prompt is unchanged; the browser does not reuse old answers as new results.
Individual failures stay visible and do not remove other answers. Stop prevents
queued calls; in-flight calls may finish, including normal provider retries.
After a restart, an unfinished job is labelled interrupted rather than silently
resumed. A new run can be started; existing runs remain available for review.
The default view is the read-only latest-per-candidate projection, including
existing local history. Reload reconnects to an active evaluation. The projection
is served by `/api/latest`, with format `jev-playground-latest/v1`; each evaluated
row has `evaluation` provenance (source run ID, timestamps, dataset hash, input
version and model), plus `latest_attempt` when a newer retry did not succeed.
Rows keep the original full request. The editor uses the selected row’s
`request.questions`; the projection’s top-level questions are a fallback rubric
for candidates without a saved request, not the prompt for every displayed answer.
Only current candidacies appear in Latest; removed/historical candidacies remain
available in their saved runs. Preview rows contain no borrowed answers.

Regional requests use `POST /api/runs` with `{ "questions": {…}, "scope": "bay-area" }`.
Omitting `scope` keeps the existing full-roster behavior. A `candidate_id` and
regional scope cannot be combined. The server chooses membership from current
contest county coverage before submitting any requests; browser filters do not
change a batch’s scope. Snapshot `scope_counts` supply both button counts.

## CAIR Action comparison

Every selected candidate’s results include the CAIR Action recommendations from
that exact candidacy in the **current canonical dataset**, with the recorded tier,
joint endorsement, election phase, source link and checked date. Historical and
primary records remain explicitly labeled. No recorded recommendation means
unknown, not Opposed or a publisher’s explicit No Endorsement. Compact labels
also appear in the race browser.

**Review CAIR differences** opens a dedicated comparison area. It flags current,
nonhistorical **Preferred** or **Endorsed** records (including joint endorsements)
when the selected saved grade is **C, D, E or F**, **or** the selected saved score
is **≤2.5 out of 5**. General-election and phase-unspecified records qualify;
unspecified phases remain labeled. Primary/historical records and Opposed do not
satisfy this positive-recommendation rule. These are review flags under the
owner’s rule, not automatic corrections to grades or recommendations.

The defaults are `gaza_grade` and `pro_palestine_score`. Question selectors allow
renamed A–F choice and 0–5 score questions, or disabling either comparison.
Scores on other scales are not silently rescaled. The area reports how many
Preferred/Endorsed candidates lack a compatible saved result; missing, failed
or ungraded answers are not treated as low grades. Every qualifying answer is
included regardless of confidence, which is displayed beside the grade/score.

The comparison uses the selected history view (Latest per candidate by default)
and the County filter. Entries remain sorted by state/race and show the saved
model/time, exact rule trigger, current CAIR record/source and an election-site
link. Click a candidate’s name to inspect their saved answers and exact prompt in
the workspace. Editing the draft questions does not change saved comparisons;
rerun explicitly to evaluate a different prompt.

Current recommendation metadata is separate from the frozen Jev request.
A recommendation added after an old evaluation appears for comparison without
rewriting that evaluation or implying the model saw it. Downloads keep exact
model requests/responses and attach a separate derived grade/mapping layer;
`cair_action` metadata in Latest is a current-dataset comparison layer, while each row’s `request` retains what was actually submitted.

## Deterministic score grade

`pro_palestine_score_grade` is a derived row field, separate from the model's
`gaza_grade`. Only a completed numeric `pro_palestine_score` submitted with six
score criteria (0–5) qualifies. Missing/invalid answers, other scales and unrun
candidates get `null`; they are never assigned F by default. No new Jev question
or call is required, and no separate grade confidence is invented. The UI labels
the unchanged source score confidence explicitly.

A compatible saved `evidence_score` (score question with two criteria, 0–1)
strictly below the editable **Minimum evidence_score** suppresses the derived letter
and returns **N/A** instead. The playground default is **0.20 / 1**; evidence
exactly at the minimum qualifies. The minimum accepts values from 0 to 1 and
previews live alongside grade bounds. This applies to the
selected result, race cards, histogram, CAIR cards, API projections and downloads,
without another Jev call. The UI explains the evidence threshold separately from
model confidence. Original scores, `gaza_grade`, probabilities and confidence are
unchanged. A historical prompt without this question (or an incompatible/invalid
answer) does not establish low evidence and retains the existing mapping.
An insufficient-info label is never compared as an A–F grade; independently
selected raw score/model-grade comparisons retain their stated review rules.

Default bands use exact stored bounds, without rounding the source score:

| Grade | Score interval |
|---|---|
| F | 0 ≤ score ≤ 5/6 |
| E | 5/6 < score ≤ 10/6 |
| D | 10/6 < score ≤ 15/6 |
| C | 15/6 < score ≤ 3.2 |
| B | 3.2 < score ≤ 25/6 |
| A | 25/6 < score ≤ 5 |

The **Grade distribution** chart above the workspace shows A–F counts for the
selected county scope and saved-history view (Latest per candidate by default).
Browse-race search/state filters do not change its scope. N/A and candidates
without compatible saved results are counted separately, outside the letter bars;
confidence never excludes a candidate.

Click a grade bar or **Tune thresholds & inspect edges** to open the tuning area.
Edit the inclusive upper bounds for F, E, D, C and B: valid changes immediately
preview the histogram, derived result grades and CAIR comparisons without a Jev
call. Values must be strictly increasing between 0 and 5; A always ends at 5.
Invalid edits retain the last valid preview and disable saving. **Save thresholds**
persists the grade bounds and evidence minimum locally; **Revert preview** restores
both saved settings.
**Restore default mapping** saves the table above. The chart remains visible while
scrolling through its tuning area.

For the selected grade, the boundary panel lists up to three closest scored
candidates on each side of each cutoff, including neighbors across empty buckets.
Click a candidate to inspect their saved answers and inputs; question drafts are
preserved. Expand the full bucket list to inspect other members in score order.
**Back to grade distribution ↑** in selected results returns to the chart.
Previewing or saving thresholds does not rewrite model answers, saved runs or
published main-site grades. Downloads use the current preview mapping.

The CAIR grade selector also offers `pro_palestine_score_grade (derived)`;
`gaza_grade` remains the default comparison. Each CAIR comparison card also
always displays `pro_palestine_score_grade` alongside its selected grade and score,
using the current mapping and the source score confidence, or the low-evidence
explanation when suppressed. Selecting the derived
grade for the comparison shows it once. Missing/incompatible scores are labeled
without assigning a grade.

The tracked default is `research/gaza-grading/score-grade-mapping.json`.
The optional `minimum_evidence_score` property travels with the mapping in local
API responses and downloads. Existing playground settings without it use 0.20
while retaining their custom grade bounds. Archived publication/CLI mappings
without that property retain their historical 0.10 rule, so opening the playground
does not change published grades or archived results.

Overrides persist under the server's `--work-dir/score-grade-mapping.json`
(default `.research/jev-playground/score-grade-mapping.json`), via the same-origin
`POST /api/score-grade-mapping` endpoint. API views and downloads include
`score_grade_mapping` and the derived field on each row so the grades can be
reproduced. Saved run files and provider responses are never rewritten. The raw
Answers/Request inspector remains the exact model response/request. A new CLI
`grade_gaza.py grade` batch also stores the derived field and mapping; use
`--score-grade-mapping /path/mapping.json` to override its default. Existing
archived batches stay unchanged.

## Compact candidate input

New inputs include optional boolean `part_of_muslim_community` only when explicitly
confirmed by the owner. Public-source research can nominate questions but cannot
overwrite an owner value. Unknowns stay absent, not
false. This is a community observation, not a Gaza policy inference. Confirmed
values are recorded with exact candidacy provenance and no special annotations. See
[CANDIDATE_COMMUNITY.md](CANDIDATE_COMMUNITY.md) for coverage and source review.

The playground wraps `grade_gaza.build_state` with versioned local/federal
context (`candidate-evidence-v14-local-federal-organization-context`) for new requests and previews.
Historical requests remain unchanged. The shared CLI builder uses `candidate-evidence-v14-organization-context`:

- Identity/party, jurisdiction, office category, government level, seat, counties,
  election date/type, partisan status, incumbency when recorded, and exact roster
  category. Nonpartisan status comes from the contest metadata, not a missing
  party field. The core evidence includes the top 12 supporting and opposing IE spenders
  plus every registered relevant spender, with exact dollar amounts and explicit relevance
  references; CAL-ACCESS lists follow the same rule. FEC and California spender
  registries remain separate. [Organization context](ORGANIZATION_CONTEXT.md) supplies
  sourced roles and dated funding links, including the owner's UDP funding criterion.
  Recorded USCPR grades, up to eight platform summaries, a
  reviewed Gaza-platform statement when present, and up to twelve dated Gaza
  evidence summaries.
- Focused endorsement/recommendation observations only. The versioned exact-name
  registries are `research/gaza-grading/endorsement-focus-v3.json` and the reviewed
  `organization-context-v1.json` aliases: owner-named
  Track AIPAC, Vote for Peace, HAPAC and CAIR Action, plus AIPAC, DMFI, J Street/JStreetPAC,
  RJC and JDCA context selected by Jev from the organizations' own material.
  Selection evidence/actual Jev answers are in the sibling `.review.json`.
  Related parent/PAC names are included for context without merging entities or
  assigning them the same position. CAIR Action was explicitly added by the owner
  in registry v3; its Preferred/Opposed relations and joint flags are retained.
  Earlier registry v2 and stored requests remain unchanged. Actual source names and relation types,
  ratings, phases, verification and historical flags remain intact.
- Vote for Peace's exact **Ally**, **Opposed** and **Neutral** source labels now
  appear as `source_label`, with source URL/date, in new compact states. Canonical
  Ally/Opposed observations were already included, but the October 9 import
  deliberately held five matched Neutral cards out of public endorsements.
  The shared builder now includes those exact reviewed candidacy mappings from
  `research/endorsements/peace-guides-2026-10-09.json` as context-only
  `relation: neutral`, `rating: Neutral` observations. It does not infer Neutral
  from missing data or fuzzy-match names, change public endorsement records,
  duplicate existing records, or override newer canonical recommendations.
  Primary observations retain their phase (including Jimmy Panetta's).
  Saved older states remain exact; rerun a candidate to submit this enriched
  context. This uses the recorded October 9 evidence, not a fresh guide crawl.
- Before adding CAIR Action, the expanded roster had **62 focused observations on 43 candidacies**,
  at most three each. The original House archive had 41 on 23, instead of all
  3,690 House endorsement observations. The published October 23 CAIR source refresh plus
  registry v3 had 147 focused observations on 107 of the original 685 candidacies,
  including CAIR ratings for 85 candidacies. The expanded five-county catalog
  had 177 focused observations on 133 candidacies before the v6 Vote for Peace
  change; v6 has 182 on 134 candidacies, including 40 Vote for Peace observations
  (27 Ally, 8 Opposed, 5 Neutral). Other names
  are omitted for context budget, not declared unimportant or absent. No category
  is inferred from religion or ethnicity. Neutral image observations are not
  converted into named endorsements.
- Recorded congressional actions resolve `action_id` against the shared action
  registry and include the actual response, title/kind, date and Congress. The
  old builder read nonexistent title/date fields from response rows, resulting
  in blank action summaries; that is corrected before grading Bay Area members.
  Source-selected actions remain distinct from a complete voting history.

The October 23 local ceasefire refresh also reaches new input previews and runs, including Kevin Park’s two attributed records. The committed 187-candidate baseline and each saved local run retain their original evidence; rerun a candidate explicitly to evaluate updated facts.

Inspect the JSON to see the exact available evidence. Missing fields do not
establish a neutral position. These are experimental model answers, not verified
candidate findings or grades published into the election dataset.

## Stored runs and CLI

The immutable default is
`research/gaza-grading/house-all-focused-2026-10-23/results.json`:
**187/187 answers, zero call errors**, `jev-latest` resolving to `jev-1.14.0`.
All answers are shown, including low confidence. Questions are in
`research/gaza-grading/criteria-pro-palestine-v2.json`; the prior v1 archive is
unchanged. Its historical cutoff flags are not imported into this playground.

To create a new CLI batch, use a fresh batch name:

```sh
python3 scripts/grade_gaza.py plan --scope house-all --batch house-all-YYYY-MM-DD
python3 scripts/grade_gaza.py grade --scope house-all --batch house-all-YYYY-MM-DD --jev-key-file /secure/path/jev-key --force
python3 scripts/grade_gaza.py report --batch house-all-YYYY-MM-DD
```

The CLI retains all valid answers/confidences too. `--force` bypasses exact-request
cache reuse; without it the CLI may reuse identical validated requests. The local
Run button always uses fresh calls. Do not overwrite committed historical batch
files. No command in this workflow writes to the canonical dataset, builds the
readers or publishes political grades.

## Verification

`check_jev_playground.py` covers question/answer contracts, focused input context,
all-active selection with five-county isolation, regional batch isolation and API validation,
shared-race deduplication, local jurisdiction and
CAL-ACCESS context, congressional metadata, frozen snapshots, low-confidence
retention, cancellation,
failure isolation, single-candidate isolation, repeated prompt iterations,
latest-per-candidate restoration/restarts, chronological selection, failed/stopped
retry fallback, unevaluated/interrupted candidates and current-roster filtering,
stale-selection rejection, persisted history, same-origin/Host checks and credential
redaction. `check_jev_playground.cjs` covers numeric ordering, custom questions,
confidence display, immutable state during delta updates, CAIR threshold boundaries,
missing/incompatible/custom questions and county selection predicates. Both are in the
39-check offline release gate. Browser coverage includes real Monaco loading at
desktop/mobile sizes and, using a fixture transport, full Run/Stop/history/export
flows with custom questions, low confidence and a failed candidate. The iteration
workspace is checked at 1440×900, 1024×768 and 390×844 for adjacent editing/results,
mobile tabs, selected-candidate keyboard runs, expandable distributions, input
inspection, old-prompt labeling, history and exports. The actual
187-candidate default batch was run against Jev, not the fixture transport.

## Publishing a reviewed final batch

The October 27 publication freezes the latest evaluations of all 1,296 active
candidacies using the exact owner-edited v5 questions after the Vote for Peace refresh; both readers show that snapshot.
See [published score methodology](PUBLISHED_GRADES.md). The publisher refuses a
mixed prompt, missing active candidate, changed source hash or identity mismatch.
Local iterations do not change the public snapshot. The public badge uses the
derived score grade and numeric score; the model's separate `gaza_grade` is not
shown. **Restore defaults** now loads the owner's complete v5 questions, while
selecting a saved evaluation still restores that evaluation's actual questions.

## Education-policy input refresh (October 26, 2026)

The default inspector tab, **Current input**, shows the state that a new evaluation
would receive. **State JSON** still shows the exact saved input; **Full request**
and **Answers JSON** also retain historical provenance. Inspecting new research
never submits a request or replaces the displayed saved answers.

All records tagged `antisemitism_education` now enter the separate
`antisemitism_education_policy_evidence` channel with source URLs and date
qualifications, outside the generic twelve-item budget. The source refresh added
129 records across 104 candidacies, including Wiener; all saved scores, preferred
v3 questions and grade explanations remain unchanged. See
[the evidence workflow](EDUCATION_POLICY_RESEARCH.md).

## Legislative alignment and date scope (v9 history)

The v9 format (superseded by v10 below) carried each source response alongside
`sheet_assessment`, `alignment_with_tracker` (aligned / not_aligned / neutral /
unknown), `assessment_basis`, action ID and source tab. An explicit source/perspective
key let Jev use the assessment without interpreting Yes or No itself.

New legislative-tracker inputs omit actions before **2023-12-01**, unknown dates
and periods that may start before that date. Exact dates sort newest first;
period-only observations follow with their original labels.
[Full source/date contract](GAZA_VOTING_RECORDS.md#reader-ordering-and-jev-input-assessments-october-26-2026).
The v10 projection preserves this alignment and date scope without rewriting
saved requests, scores or explanations.

## Compact model inputs v10 (October 26, 2026)

New requests use compact projections; the canonical dataset, main-site evidence,
audit records and historical saved requests retain their original detail.
Legislative entries contain only `date`, `title`, `kind`, `response` and
`alignment`, plus `note` when the source supplies an additional qualification.
`vote` identifies a roll-call vote; sponsorships, committee votes, letters and
statements retain distinct kinds. Alignment is mapped from the sheet assessment
by code: positive → aligned, negative → not_aligned, neutral → neutral,
unclassified → unknown. One short context string supplies the tracker perspective
and date-range caveat. Worksheet mechanics, IDs, Congress/tab identifiers,
precision tags and duplicate assessment labels are excluded from model input.

The December 1, 2023 cutoff and newest-first order are unchanged. An identical
entry is collapsed only when its primary action URL and all projected meaning
(including response, alignment and any note) match. Different URLs, titles,
responses, alignments or notes remain separate. The canonical record keeps all
source entries. The current projection has 505 legislative entries, versus 596
before this exact-duplicate reduction; Garamendi has 51 versus 64.

Focused endorsements retain endorser, relation, phase, rating and historical/joint
qualifiers. Duplicate publisher labels, URLs and check-date/verification mechanics
are omitted. Campaign claims and reported/unverified claims remain explicitly
marked, rather than being presented as direct endorser statements. CAIR Action
and Vote for Peace recommendation publication checks still pass for every current
candidate. The underlying full `focused_endorsements()` observations are unchanged.

Education-policy observations retain the full date and summary, with meaningful
chronology/source qualifications under `context`. Repeated quotes, URLs and
capture-method fields are excluded. XML/transcription mechanics are removed;
report dates, earlier bill versions and independent-verification limits remain.
Other factual evidence summaries and funding amounts are unchanged.

The model keeps candidate, office/seat, state, party, jurisdiction, election date,
incumbency, owner-confirmed community values and non-general election type where
recorded. County filters, grouping and race categories use catalog metadata outside
the model input. Duplicate seat/category/government-level/partisan/general-election
metadata is omitted from the model state. Exact roster identity remains for
publication binding. Explicit false community observations remain false.

[Measured payload sizes](../research/gaza-grading/state-compaction-2026-10-26.json)
use UTF-8 bytes of compact serialized state JSON, not a claim about Jev's tokenizer:
all 1,296 states shrink from 2,078,499 to 1,695,829 bytes (18.4%); Garamendi's state
shrinks from 27,669 to 13,122 bytes (52.6%). No scoring calls were made. Reload and
open **Current input** to inspect the compact state; **State JSON** preserves the
exact input that produced the selected saved result.


## Funding input scope v11 (October 26, 2026)

New states use only reviewed organization contribution/spending amounts with an
explicit period wholly from **2024-01-01** onward. A page analysis date, an
as-of date or a 2026 candidacy does not date an underlying donation. A 2024
cycle can include 2023; it is not automatically eligible. A range crossing the
cutoff cannot be prorated. Individual donors, individual employer affiliations,
earmarked individual receipts and mixed aggregates do not become organization
donations. Outside spending stays distinct from receipts.

The complete funding-observation audit is hash-bound to each exact current
record; missing/changed observations default to held. Nonfinancial policy,
refusal and endorsement statements retain reviewed projections, including
narrow versions of mixed sentences. Relevant historical nonfinancial observations
keep their dates. One short `funding_scope` line prevents omitted amounts from
being read as zero funding. Filtering occurs before the twelve-item budget.
Current-cycle structured FEC/CAL-ACCESS independent spending remains available.

This refresh does not rerun scores. Reload **Current input** to see the new
projection; the saved **State JSON** remains the exact historical request and
can contain the old Haney total. [Full policy and review](FUNDING_EVIDENCE.md).


## October 27 publication defaults

The preferred questions are now the owner’s exact **v4** prompt from the latest
full-roster run. The inclusive C upper bound is **3.2**, B begins above 3.2,
and the other bands retain their previous boundaries. These defaults are shared
by Python, browser presentation and the local persisted mapping.
New v12 input adds one short context note for directional CAIR Action / Vote for
Peace observations: these are concrete stance evidence under the owner’s rubric,
including Ally and Opposed, even without a direct quotation. Tier, phase,
verification limits and historical/Neutral qualifiers remain intact.
Two conflicting low-evidence results were re-evaluated with unchanged v4 questions;
other saved provider results were not rewritten. [Current public archive](PUBLISHED_GRADES.md).

## Vote for Peace refresh — October 27, publication 2026-10-27.2

Current inputs use v13 and canonical first-party Ally/Opposed/Neutral observations
from the new nationwide source capture. A current Neutral record supersedes the
held October 9 context without implying support; old states remain exact.
All 1,296 active candidacies were rerun with the latest saved owner questions (v5)
and updated observations, followed by two corrected-prose evaluations. Saved
bounds 0.7 / 1.4 / 2.5 / 3.2 / 4.4 and evidence minimum 0.20 are frozen in the new
public archive; playground edits still preview locally until explicitly published.
[Current methodology and archive](PUBLISHED_GRADES.md).
