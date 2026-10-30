# Research and development handoff

Firebase Hosting is live (October 29): [tall-bay-area-research-tool.web.app](https://tall-bay-area-research-tool.web.app/).
The requested Web App and dedicated Hosting site are registered in
`tall-bay-area-voter-guide`; current scores, fresh explanations and in-reader
recommendations are published. **50/50 release checks pass**, both production
domains match the tested bundle, and live Chrome checks pass.
[Setup, deployment and verification](FIREBASE_HOSTING.md).

Publication **2026-10-29.1** lowers the recommendation floor to **D** on owner
instruction: races whose best graded candidate is a D now receive a pick and a
Qwen why-paragraph (21 new races, e.g. Sam Liccardo, CD-16), for **172 recommended
races** (12 Muslim-community + 160 Jev). Races where every graded candidate is
E or F stay unrecommended (82). Classification gate, Jev prompt cache and both
reader maps refreshed; the standalone recommendations page stays retired.
[Rules, pipeline and provenance](CANDIDATE_RECOMMENDATIONS.md).

Previous publication **2026-10-28.5** completes the Hermes follow-up from publication
2026-10-28.4: all **398 letter-grade candidates** carry fresh source-bound evidence
explanations (generated from each exact frozen v7 scoring request under
summary-prompt-v3; `qwen/qwen3.8-27b`), and **898** N/A candidacies carry the editorial
insufficiency note. Recommendations now render **inside both readers** — every race card
and ballot result shows the pick with a Qwen why-paragraph written under the owner
framework, or the explicit no-recommendation line; the standalone recommendations page
is retired. [Rules, pipeline and provenance](CANDIDATE_RECOMMENDATIONS.md).

Display follow-up (owner request): the why-paragraph now auto-expands with a remembered
collapse preference across races, its note shows only the recommendation-set date (model
attribution removed), and the federal-race "Campaign money" explainer panel was removed as
redundant real-estate. Display-only changes; the dataset and plan bytes are unchanged.

Publication **2026-10-28.4** publishes the owner's completed full-roster
run: **1,296 evaluations**, exact **v7** questions and current **v18** inputs.
Saved bounds are **0.7 / 1.4 / 2.3 / 3.3 / 4.4**, minimum evidence **0.22**,
with the issue-observation gate. Counts: **A 120 · B 44 · C 12 · D 33 · E 66 ·
F 123 · N/A 898**. Candidate and race explanations from the previous run are
held, per the owner's choice; fresh source-bound queues were ready for Hermes.
The recommendations page also uses the new grades. [Current archives, validation
and Hermes follow-up](LATEST_SCORE_PUBLICATION.md). Older publication notes below are historical.

Publication **2026-10-28.3** fixes Census geography-service failures with a bounded fallback to Census address coordinates and direct TIGERweb polygons. Both paths retain real district labels, cancellation and privacy behavior. Candidate data and scores are unchanged. [Address recovery policy and live checks](ADDRESS_LOOKUP_RECOVERY.md).

Publication **2026-10-28.2** corrects BAMC opposition to **Steve Raspe and Heidi Owens**,
removes race-wide guide context from every candidate input, and assigns the Samir
comment about Sam Liccardo to Sam. Peter Sundin Soulé retains only his own
protest-vote recommendation. New/edited comments require an exact subject review.
Published scores and explanations remain unchanged; current inputs use v18.
[Correction and current-input policy](COMMUNITY_GUIDE_CLEANUP.md).


## Community-guide source update

Publication **2026-10-27.13**, schema **1.29**, adds BAMC Action's **16 supports /
2 oppositions**, two comment-only entries, and Samir Laymoun's **38 supports /
38 oppositions**. All **21 candidate comments** are preserved. New v17 Jev inputs
include these alongside CAIR Action and Vote for Peace, retaining differing race
selections and tactical comment context. Existing saved scores and explanations
are unchanged; no candidate evaluations were rerun. [Import and source policy](BAMC_ACTION.md).


## Current editorial publication

Publication **2026-10-27.12**, schema **1.28**, manually cleans **336 visible
explanations** and makes four unrelated-platform-only candidates N/A. All raw
numerical model evaluations and the owner-approved Khanna paragraph are unchanged.
Current counts: **A 121 · B 44 · C 13 · D 30 · E 67 · F 125 · N/A 896**.
Use the `published-2026-10-27-editorial.json` score snapshot and matching
`explanations-2026-10-27-editorial.json` / `explanation-queue-2026-10-27-editorial.json`.
The versioned issue-observation gate supplements the unchanged **0.22** evidence
minimum; historical mapping snapshots remain reproducible. Future paragraphs must
omit missing-record disclaimer padding and give JStreetPAC little weight.
Use the hash-bound **summary-prompt-v3.txt / summary-policy-v3.json** while retaining
Hermes's Qwen defaults. The Liccardo Sol Low comparison remains held for review.
[Full policy, audit and exact changes](SUMMARY_EDITORIAL_REVIEW.md).

Older sections below describe earlier publications.

## Evidence minimum and unknown-candidate display — October 27, 2026

Publication **2026-10-27.11** applies the owner's saved minimum evidence **0.22**
without re-running models. Grade bounds remain **0.7 / 1.4 / 2.3 / 3.3 / 4.4**.
Rommy Kushner (0.21), Angel Rodriguez (0.20), Dean Abrams (0.20) and Thomas
McMasters (0.21) change from D to N/A. All **556 identity-only inputs** now have
N/A; a regression prevents publishing a political grade for this input class.
False community membership and party/office identity are not stance evidence.

Both readers hide the explanation panel for every N/A candidate and omit the
meaningless saved directional score/confidence from N/A tooltips. The four prior
political paragraphs are replaced with archival editorial insufficiency notes;
these notes are not rendered as public explanation panels. Other paragraphs,
including Khanna's approved 78-word text, remain exact.

The mapping-only publication is `published-2026-10-27-evidence022.json`, with
matching explanation archive and queue. Its derivation identifies the untouched
v6 source archive; raw requests, answers and evaluation metadata are identical.
Counts: **A 121 · B 44 · C 13 · D 34 · E 67 · F 125 · N/A 892**. Browser, CLI
and local server defaults inherit the saved 0.22 minimum. Historical mappings
remain reproducible. No source research or model calls were performed.

Validation: **47/47 release checks pass**, including all 556 identity-only
cases, inclusive 0.22 boundaries, historical custom mappings, and N/A panels
that hide even a stale political paragraph. Every raw request/answer/evaluation
row matches the prior scoring archive. Only the four newly insufficient
paragraphs changed; the approved Khanna text is exact. The restarted local
playground uses 0.22 for both saved and default mappings.


## Approved concise Khanna summary — October 27, 2026

Publication **2026-10-27.10** uses the owner-selected Sol Low comparison draft,
**78 words** after the recorded clarification “U.S. military aid to Israel.”
The model received the same complete current record, rubric and recorded result
as the Qwen comparison, with a strict **45–80-word** paragraph rule. One-off
comparison models are not changes to Hermes's Qwen defaults.

Archive: `research/gaza-grading/explanations-2026-10-27-v6-concise-khanna.json`.
Its refresh metadata binds the separately archived concise generation input and
matching output, which preserves both raw model text and the explicit editorial
replacement. All numerical evaluations, source data,
thresholds, historical archives and **1,295 other summaries** remain exact.
Both readers are rebuilt. No new model calls were made for this publication.

Validation: **47/47 release checks pass** against this dataset. The recorded
editorial replacement reproduces the 78-word final text exactly. Only Khanna's
paragraph and publication/archive metadata differ from the previous release;
all evidence, numerical evaluations and other summaries remain exact.


## Historical evidence and Khanna narrative — October 27, 2026

Prepared publication **2026-10-27.9** adds source-reviewed November 21 and 26,
2023 Khanna evidence and qualifies the February 2024 repost. Initial research
missed November; it was not deleted by a date cutoff. The public-history audit
found no date-cutoff deletions among 14 missing Q4 records; legitimate source
holds/dedupes remain intact. [Full findings](HISTORICAL_GAZA_EVIDENCE.md).

New v16 legislative inputs start **2023-11-01** (95 more actions across the changed
state set); date qualifications reach the compact model input. Public histories
are never filtered by this projection. No numerical scores were rerun.

The owner's requested single **GPT-6.1 Sol / low** narrative refresh applies only
to Ro Khanna. It is bound to separately archived current input/output and the
unchanged saved score; 1,295 other paragraphs match main exactly. Hermes's Qwen
defaults remain unchanged. Discovery and summarizer guidance now guard against
mistaking the earliest collected report for the candidate's first position.

Validation: **47/47 release checks pass**, including expanded November boundaries,
public-history preservation, date qualifications and refresh-input/output tamper
guards. The live local playground serves v16 with the new scope. Every numerical
projection and 1,295 other summaries match main; original scoring/Qwen archives
are byte-identical. The Sol output has one audit row for every supplied evidence
item/action (100 rows, no duplicate IDs).


## v6 voter explanations published — October 28, 2026

Publication **2026-10-27.8**, schema **1.27**, reattached explanations to the v6
scores. The 408 letter grades carry fresh voter-voice paragraphs generated
under the owner's final summarizer prompt (temperature 1.0, thinking enabled,
grade-letter leak guard) from each candidate's exact frozen v6 record; the 888
N/A candidacies keep the hand-written editorial note. Frozen archive
`research/gaza-grading/explanations-2026-10-27-v6-prompt3.json` (1,296 entries,
each bound to candidate_id + v6 request_sha256). The v5 explanation archives
are superseded but immutable. Full release gate passes (47 checks) with the
dataset hash pinned in `.checks/release-checks.json`.

## Owner full-roster v6 scoring publication — October 27, 2026

Prepared publication **2026-10-27.7**, schema **1.27**, freezes all **1,296**
successful owner evaluations from `20261027T224704Z-cc6d4be3`. Exact revised
questions are saved as `criteria-pro-palestine-v6.json`; the archive and new
Hermes queue use the `2026-10-27-v6` suffix. Every frozen input matches current
v15. Saved inclusive bounds: **0.7 / 1.4 / 2.3 / 3.3 / 4.4**, minimum evidence
**0.20**, no confidence gate. Counts: **A 121 · B 44 · C 13 · D 38 · E 67 ·
F 125 · N/A 888**.

The previous five-candidate rerun task is complete. Wiener is D (2.08), Liccardo
C (2.67), Khanna A (4.71), Kiran Mohammad A (4.86), Jamal Khan A (4.88).
No new Jev calls were made during freezing. Tracked browser/CLI defaults now
match the owner's saved bounds. Both readers are rebuilt with the new projection.

**Hermes next:** regenerate explanations against the new queue with the owner's
latest Qwen summarizer prompt. Previous summaries are preserved in immutable
archives, but their old request bindings are not displayed as explanations of
new v6 results. [Current task and inputs](tasks/HERMES_GRADE_EXPLANATIONS.md).

Validation: **47/47 release checks pass**. Every frozen request, provider response
and evaluation provenance matches the owner's saved full run; all 1,296 state
objects match current generated input. Browser/Python grade defaults and live
playground defaults match the saved thresholds and v6 questions. Historical
score and prompt3 summary archives remain byte-identical. No new model calls
were made to freeze or publish this snapshot.


## Latest-main reconciliation and targeted reruns — October 27, 2026

Merged main `5d35c5c` into PR #19, preserving the final-prompt Qwen explanations
from publication 2026-10-27.5. Rebuilt both generated readers to resolve their
merge conflicts; prepared evidence publication is now **2026-10-27.6**.
Neither published numerical scores nor Hermes's latest explanations changed.

[Targeted rerun review](JEV_RERUN_REVIEW.md) recommends just **Scott Wiener,
Sam Liccardo, Ro Khanna, Kiran Mohammad and Jamal Khan** as the small batch.
Kiran and Jamal are currently N/A despite confirmed alignment. Ro is already A,
so his numerical refresh is less urgent but addresses the owner's explicit concern.
Aisha Wahab's new primary source reinforces existing sponsorship and an A.
Other PR changes do not require a full-roster rerun. The linked machine-readable
manifest includes every changed candidacy and exact input hashes.

The shared builder updates **Current input** for all 1,296 candidacies; saved
scoring requests and results stay immutable until explicitly rerun. Retain the
latest owner-approved summarizer prompt and Qwen runtime from main; the v2
full-evidence audit material below is supplementary guidance, not a replacement
for the newer final-prompt summary batch.

## Context follow-ups and Hermes handoff — October 27, 2026

Prepared publication **2026-10-27.6**, schema **1.27**, adds eight Jev-reviewed
observations and retires Liccardo's obsolete guide prose while retaining Ally.
Wiener's debate refusal, criticism and later statement now remain linked; so do
Khanna's initial Yes, attributed explanation, later No and separate UNRWA
restoration cosponsorship. Official XML dates Liccardo and Wahab's Block the
Bombs cosponsorships. [Sources, limitations and workflow](EVIDENCE_CONTEXT.md).

State v15 carries the pro-Palestine community meaning as affirmative general
alignment, retains all eligible Gaza evidence, and guards new community-positive
N/A publications. Discovery adds context/follow-up queries and verified secondary
X accounts, plus official bill-status parsing and an all-candidate lead audit.
Exact registered retirements can reconcile to the collector without permitting
unrelated deletions.

**Hermes:** keep using `qwen/qwen3.8-27b` with the improved
`summary-prompt-v2.txt` and its hashed `summary-policy-v2.json`, with full item
audits. This policy does not change model runtime settings. No scores or explanations
were rerun; old inputs and responses remain exact. Jamal Khan's old N/A requires
a new evaluation with the clarified community meaning.

Validation: **47/47 offline release checks pass**, including eight new context
regressions. The local playground serves v15 for all 1,296 candidacies; 11 have
linked reviewed context. Frozen published scores and explanations remain
byte-identical. Generated readers match the prepared dataset exactly.

## Organization context for future evaluations — October 27, 2026

State v14 now supplies sourced organization roles/relevance alongside exact spending
amounts and preserves all registered relevant spenders below the top-12 cutoff.
FEC IDs and CAL-ACCESS IDs remain separate; unmatched spenders explicitly have
unestablished relevance. The 15-entry Jev-reviewed registry covers the owner-named
organizations, distinct J Street/AIPAC committees, DMFI, and UDP funding links to
BOLD America, EDW Action Fund, 314 Action Fund (2024), and donor-reported Palmetto
Action (2026). The owner's criterion explicitly treats a documented UDP funding
connection as a negative organizational signal without requiring earmarking.

A reusable FEC transfer discovery script captures held leads for later source/Jev
review. [Details and maintenance](ORGANIZATION_CONTEXT.md). No candidate scorecard
reruns, dataset/public-page edits, or changes to archived requests/explanations.
Hermes must not present newly supplied organization context as something an old
evaluation already considered.

Validation: **46/46 offline release checks pass**, including eight organization
regressions and 48 playground API/state checks. The restarted local server serves
v14 for all 1,296 candidacies; 227 have organization context. All 16,724 saved local
JSON files retained their hashes. No public page rebuild was needed.

## Final-prompt explanations published — October 27, 2026

Publication **2026-10-27.5**, schema **1.27**, republishes all 1,296
explanations under the owner's final summarizer prompt at temperature 1.0
(thinking enabled) with `qwen/qwen3.8-27b`: comprehensive current-stance
capture, candidate-specific openings with boilerplate lines banned, strict
factual-accuracy and relevance rules, 40–100-word soft range (validator
20–130). The 405 letter-grade paragraphs regenerate from each candidate's
exact frozen v5 record; the 891 N/A editorial notes are unchanged in substance.
Frozen archive `research/gaza-grading/explanations-2026-10-27-vfp-prompt3.json`
(1,296 entries); the interim 2026-10-27.3 archive remains immutable. All 405
generation prompts were audited to contain every prompt section; one transient
generation error (Jimmy Panetta) was retried to completion by the driver.
Validation: full release gate passes (46 checks, including
`check_organization_context.py` from merged PR #18) with the dataset hash
pinned in `.checks/release-checks.json`.

## Voter-voice grade explanations published (interim batch) — October 27, 2026

Publication **2026-10-27.3**, schema **1.27**, publishes grade explanations for
the current **jev-2026-10-27-vfp** score snapshot. All **405 letter grades**
carry a short voter-voice paragraph written from the project's openly
pro-Palestine, pro-justice, anti-genocide standpoint, generated by LM Studio
`qwen/qwen3.8-27b` (temperature 0.1) from each candidate's exact frozen v5
record, rubric and recorded Jev result — the paragraphs never mention scores,
bands or methodology. The **891 N/A candidacies** get one uniform hand-written
editorial note (no LLM): the public record is too thin to judge and no stance
is inferred from silence. Frozen archive:
`research/gaza-grading/explanations-2026-10-27-vfp.json` (1,296 entries, bound
by request hash); queue: `explanation-queue-2026-10-27-vfp.json`. Both readers
show the paragraph under the collapsed **Why this grade?** panel; the N/A panel
displays the editorial note with no model attribution.
`scripts/check_pro_palestine_grade_display.cjs` now asserts that editorial
wording. The upstream Jev archive was re-verified unchanged against `main`
before attach. Validation: the full release gate passes (43 checks) with the
dataset hash pinned in `.checks/release-checks.json`.

## Vote for Peace refresh and current scores — October 27, 2026

Publication **2026-10-27.2**, schema **1.27**, supersedes the score snapshot below.
The reusable `sync_vote_for_peace.py` captures 1,429 first-party source cards and
accounts for every card. Exact name/prior-reviewed alias + state + office/seat
bindings publish 132 observations: 103 new and 29 refreshed, including Garamendi
Opposed → Ally. Four Neutral observations are explicitly neutral in both readers
and Jev state; primary recommendations retain their phase. Other organizations'
aggregated badges are not copied. Unclear identities/seats and out-of-scope cards
stay held, with existing observations preserved. Two stale prose notes (Garamendi
and Liccardo) were refreshed through separate registered before/after reviews;
the Gaza collector ledger is reconciled.

The latest owner-saved prompt is archived as **v5** from
`20261027T084211Z-eec4530d`. Fresh full run `20261027T085927Z-01877b08` evaluated
all **1,296** active candidacies with **zero errors**; two follow-up calls use
corrected guide prose. Every exact saved state matches the current generated input.
Saved bounds are **0.7, 1.4, 2.5, 3.2, 4.4**; evidence minimum **0.20**, inclusive.
The publisher/schema/tooltips now carry that threshold rather than hardcoding 0.10.
Archive: `published-2026-10-27-vfp.json`. Distribution:
**A 125, B 41, C 7, D 40, E 71, F 121, N/A 891**; no confidence gate or
directional CAIR/Vote for Peace recommendation/N/A conflicts.

**Hermes next:** use `explanation-queue-2026-10-27-vfp.json` and v5 to regenerate
all explanations. Earlier queues, requests and provider responses remain intact.
Finance and ballot-research snapshot dates are unchanged. Validation: **45/45
release checks pass**, plus desktop/mobile checks of both readers and the local
playground. All 1,296 frozen requests/responses match their saved runs exactly;
all 190 prior run files retain their hashes. Unrelated candidate/roster/finance
data is unchanged.


## Editable playground evidence minimum — October 27, 2026

**Minimum evidence_score** joins the grade tuning controls, defaulting to **0.20 / 1**.
Evidence strictly below it produces N/A; the exact minimum qualifies. Valid edits
preview histogram counts, boundary neighbors and derived grades immediately;
Save thresholds/Revert preview persist or restore both settings. Local API views
and downloads include `minimum_evidence_score` in `score_grade_mapping`.
Existing local grade bounds are preserved when this new default is added.
Historical publication/CLI mappings without this optional field retain 0.10;
no published dataset, model responses, prompt or saved evaluations are rewritten.
No Jev calls were made. Tests cover exact boundaries, 0/1 extremes, invalid values,
legacy settings, persistence, exports and desktop/mobile live preview/save/reload.
Validation: **45/45 release checks pass**; all 186 prior local evaluation files
retain their hashes.


## Local grade distribution and threshold tuning — October 27, 2026

The local playground now charts A–F counts for its county scope and selected
saved-history view. N/A and missing/incompatible evaluations are separate counts.
Threshold edits preview immediately, with explicit Save thresholds/Revert preview;
no model call or published-score change occurs. Selecting a bar shows up to three
nearest candidates on both sides of each cutoff plus an expandable full bucket
list. Names open the existing inspector while preserving question drafts.
The chart stays visible within the tuning area, and results link back to it.

Validation covers inclusive cutoffs, count conservation, low evidence versus missing
results, zero-confidence inclusion, empty buckets and immutable source rows.
Desktop/mobile browser checks cover preview, invalid edits, revert, save/reload,
boundary links, draft preservation, county/history scope and overflow, using
intercepted APIs without Jev calls or changes to real local thresholds.
The complete offline release gate passes **45/45 checks**. All 169 prior local
run files retain their hashes. Canonical data, published readers, archived grades
and prompts remain unchanged.
See [playground workflow](JEV_PLAYGROUND.md).

## Latest Jev grades published — October 27, 2026

Publication **2026-10-27.1**, schema **1.26**, freezes all 1,296 latest successful
evaluations using the exact owner-edited v4 prompt. Archive: `published-2026-10-27.json`;
criteria: `criteria-pro-palestine-v4.json`; C upper bound **3.2** (inclusive).
Counts: A 126, B 24, C 13, D 37, E 64, F 140, N/A 892. No confidence gate.
1,293 rows use the latest full run, one uses the owner’s later Haney evaluation,
and two use narrowly repaired endorsement-evidence inputs with the same prompt.
Wagner/Priforce had low evidence despite Vote for Peace signals; v12 now makes
the owner’s directional-endorsement evidence rule explicit. All recommendation/N/A
guards pass. Existing saved runs remain exact; only two repair runs were added.

**Hermes next:** regenerate all grade explanations from
`research/gaza-grading/explanation-queue-2026-10-27.json` and the new frozen archive.
Old explanations are archived and removed from public cards; do not reuse them.
[Task](tasks/HERMES_GRADE_EXPLANATIONS.md), [methodology](PUBLISHED_GRADES.md).
The abandoned AB 715/2159 research was not applied; candidate evidence, finance
and endorsements remain the previous publication’s data.
Validation: **45/45 release checks pass**; desktop/mobile browser checks confirm
the v4 prompt, C=3.2 boundary, new public badges and absence of stale explanations.
All 1,296 archived requests/responses match saved run files exactly; 154 prior
local run files retain their hashes.

## Funding periods and donor scope — October 26, 2026

Publication **2026-10-26.8**, schema **1.26**, corrects seven public Track-JPAC
observations and their collector entries. Haney’s California Jewish PAC row is
**$25,700 for 2021–2023**, not 2025; the old $47,700 mixed total no longer appears
in current evidence or new Jev state. New v11 model inputs hold historical,
individual/mixed, and period-unestablished funding claims. Of 221 reviewed
observations across 151 candidacies, 185 are held; 34 nonfinancial projections
and two dated organization-spending projections remain. These are not findings
of zero funding. Authoritative current-cycle FEC/CAL-ACCESS independent spending
and nonfinancial evidence remain separate. No scores or archived explanations
were rewritten or rerun; both readers flag older funding-based saved explanations.

[Workflow, audit artifacts, and limitations](FUNDING_EVIDENCE.md). Future source
changes require renewed review; the hash-bound input gate holds unreviewed claims
out automatically. The collector now excludes individual/employer matches,
pre-2024 receipts, memo/earmarked receipts, and unknown donor types.
Validation: **45/45 release checks pass**. Browser checks verify corrected Haney
evidence and saved-grade notices on both readers at desktop/mobile sizes, exact
saved versus current playground inputs, and county filtering. All 146 prior
local run files retain their hashes; no scoring requests were made.

## Compact Jev state — October 26, 2026

Publication **2026-10-26.7** keeps model input focused on decision-relevant
content. Legislative rows have five fields (date, title, kind, response,
alignment), plus a note when needed. Identical linked observations collapse;
conflicts and qualifications remain. County/race metadata stays in the catalog
for filters, while URLs and capture mechanics stay in canonical/audit records.
Endorsement levels, phase/history/joint flags, non-primary claims, date limits,
community booleans (including false), scores and exact historical inputs remain
intact. No scorecards were rerun.

[Full v10 contract](JEV_PLAYGROUND.md#compact-model-inputs-v10-october-26-2026),
[measured payload sizes](../research/gaza-grading/state-compaction-2026-10-26.json):
18.4% less JSON across 1,296 inputs; Garamendi 52.6% smaller. This measures
serialized bytes, not provider token counts. Current input previews v10.
Validation: **44/44 release checks pass**; desktop/mobile browser checks verify
compact current input, unchanged saved input and complete public history. All
123 local saved run files retain their pre-change hashes.

## Legislative assessment and date ordering — October 26, 2026

Publication **2026-10-26.6** is a display/input-only change. Jev now receives
exact sheet assessments plus explicit tracker-alignment labels and provenance.
The source's positive No votes remain aligned; neutral/unknown are not converted
to opposition. Its legislative-tracker input uses an inclusive 2023-12-01 cutoff,
excluding unknown dates and ranges that may precede it. Garamendi retains 64 of
113 source entries, with the original 32 positive / 27 negative / 5 neutral
assessments. No scorecards were rerun and historical requests remain exact.

Both readers retain all historical tracker entries and sort exact action dates
newest first across tabs, followed by separately labeled period-only/undated
entries. Per-action source tabs, notes and sheet-cell links remain intact.
See [the source/date contract](GAZA_VOTING_RECORDS.md#reader-ordering-and-jev-input-assessments-october-26-2026).

## Education-policy evidence refresh — October 26, 2026

Publication **2026-10-26.5**, schema **1.26** adds **129 reviewed evidence
records across 104 candidacies** after a Serper-only discovery pass over all
1,296 active candidacies. Scott Wiener now has AB 715 coauthor/vote evidence,
CAIR's attributed June-version objections and the separate AB 1468 proposal.
The pipeline covers IHRA/antisemitism definitions and Israel/Palestine education
policy, preserving support, opposition, amendments, nonvotes and bill versions.
AB 715's retrieved chaptered text does not explicitly name IHRA; do not replace
that distinction with an assertion of literal IHRA adoption.

[Workflow and limitations](EDUCATION_POLICY_RESEARCH.md),
[sweep archive](../research/education-policy/sweep-2026-10-26.json), five
registered reviews and source-bound Jev audits are committed. Source failures
and ambiguous surname/date matches remain held. The new state channel retains
all `antisemitism_education` evidence beyond the generic twelve-item budget.

**No scorecards were rerun.** Numeric scores, grades, exact v3 prompts, raw
provider responses and Hermes's frozen explanations are unchanged. Playground
**Current input** previews regenerated state; **State JSON** retains the exact
saved input. The owner must request a rerun before refreshing the score archive
and its explanations. New source-review decisions use Jev only.

## Grade evidence explanations published — October 27, 2026

Publication **2026-10-26.2**, schema **1.25**: all **1,296 grade summaries**
(docs/tasks/HERMES_GRADE_EXPLANATIONS.md) were generated with LM Studio
`qwen/qwen3.8-27b` (temperature 0.1, concurrency 2) from each candidate's exact
frozen request state, v3 rubric and recorded answers; per-request caches remain in
the ignored `.research/grade-explanations/responses/`. The frozen archive is
`research/gaza-grading/explanations-2026-10-26.json`, attached by
`scripts/attach_grade_explanations.py`; `scripts/check_grade_explanations.py`
re-validates every binding in the release gate. Both readers show a collapsed
**Why this grade?** panel; N/A paragraphs state only insufficient evidence
(below 0.10 / 1) with no stance implied. Four initial generation failures were
retried to completion (two truncated replies, two validator-guard refinements:
inline `#` inside quoted hashtags is allowed; word ceiling 110).

## Public Jev scores and uniform final prompt — October 26, 2026

Publication **2026-10-26.1**, schema **1.24**, adds colored score badges to both
readers: for example **E (1.36 / 5)**, or gray **N/A** for insufficient evidence.
The owner required the exact supplied question JSON for every evaluation and
expanded scope to **all 1,296 active tracked candidacies / 471 races**. A fresh
Jev run `20261026T071836Z-15420e33` completed 1,296/1,296 with zero errors under
that identical v3 JSON. **A 128 · B 21 · C 16 · D 33 · E 36 · F 176 · N/A 886**.
The playground now includes all active tracked candidates; Bay Area remains
877 candidacies / 340 races. Saved history and original provider responses remain
intact. Restore defaults loads v3; saved evaluations retain their actual prompts.

See [published methodology](PUBLISHED_GRADES.md), the immutable full request/response
archive and the candidate-bound publication checker. The publisher rejects a
mixed rubric, incomplete coverage, changed request hashes or identity mismatches.
Published scores do not feed back into future input states. Model `gaza_grade`
is not displayed. The public snapshot retains scores/confidences even for N/A;
only the short badge suppresses the numeric display in that case.

[Hermes's next task](tasks/HERMES_GRADE_EXPLANATIONS.md) is to summarize the evidence
supporting each published grade. A portable 1,296-item queue supplies exact IDs
and request hashes; all input states and the final owner JSON are committed.
That follow-up is now complete in the explanation publication recorded above.

Validation: **42/42 release checks pass**, plus desktop/mobile Chromium checks
on both readers and the final preferred-default/history prompt regression. All
104 saved runs predating the new 1,296-candidate batch remain byte-for-byte intact.


The publication check also requires captured nonhistorical CAIR Action and
Vote for Peace recommendations to appear in the exact saved input. A derived
N/A alongside a directional endorsement, preference, support or opposition is a
blocking evidence-review discrepancy. Primary recommendations remain explicitly
labeled observations. Vote for Peace Neutral/no-endorsement records do not imply
a directional stance. This guard never fabricates a score or rewrites a model
answer; repair the input or rerun Jev with the same preferred questions. The
fresh 1,296-candidate batch has zero CAIR Action recommendation/N/A conflicts,
and zero N/A cases with recorded Vote for Peace observations.

## October 26 publication

PR #17 is merged as `b472045ad6c7ac88ef2e9d037768776aa8d17719`, and its
GitHub Pages deployment succeeded for publication version **2026-10-25.2**. The [release manifest](reviews/2026-10-26-publication.md) records
the public Fiona Ma evidence addition, local playground scope and evidence
sufficiency behavior, 40 passing release checks and exact artifact hashes.
GitHub Pages publishes the election readers; the Jev server remains local.
Research/finance observation dates and all saved grading inputs remain unchanged.
Actual downloads of both public readers and the canonical JSON match the release
manifest. Desktop/mobile Chromium verifies Fiona Ma’s evidence/source link with
no page errors or overflow. The local playground now runs from merged main; all
104 saved run files present at restart are unchanged.

## Evidence sufficiency and Fiona Ma divestment — October 25, 2026

The derived `pro_palestine_score_grade` now returns **Insufficient Info** for a
saved, compatible 0–1 `evidence_score` strictly below 0.10. Exactly 0.10 is still
graded. This applies to Python/API/CLI projections and browser race/selected/CAIR
results and downloads. Original model grades, scores, confidence, requests and
run files are unchanged. A suppressed label is not an A–F comparison value;
independently selected model-grade/raw-score review rules remain intact. Legacy
prompts without this evidence question retain their prior mapping.

The missing Fiona Ma stance was a research gap, not state truncation. Historical
logs record a timeout/empty follow-up passes despite a done/enriched flag. The
current Serper-only discovery workflow now separately searches divestment and
BDS and retains those leads. A May 16, 2024 POLITICO interview explicitly records
Ma opposing divestment from Israel. Actual captured HTML, identity, meaning and
publication date passed Jev source review. Review `fiona-divestment-2026-10-25`
adds GE-1288; the ledger/coverage and generated readers are synchronized for
publication version 2026-10-25.2. See the
[full diagnosis](reviews/2026-10-25-evidence-sufficiency-and-fiona-ma.md).

The local server now reads this development worktree's updated dataset and keeps
the existing main-checkout history directory. All 102 preexisting run files were
verified unchanged. Fiona Ma's saved evaluation retains its old input; a new run
is needed to evaluate the new evidence. No candidate grading calls were made.

## Selected evaluation prompt restoration — October 25, 2026

The question editor now initializes from the selected candidate’s actual saved request, rather than the latest projection’s historical batch-default questions. Candidate/county selection persists locally across reloads. Clean navigation follows each displayed evaluation’s saved prompt; unsaved and invalid drafts survive selection changes and result polling. **Load saved prompt** restores the displayed evaluation explicitly; **Restore defaults** retains its original-rubric meaning. Reload discards the session draft and restores saved questions. No provider calls or history rewrites are required for restoration. Validation: **40/40 release checks pass**, plus Chromium regressions covering both Monaco and fallback editors, reload/selection persistence, edits during polling, prompt carry after evaluation, explicit restoration, saved-history switching, disabled storage and narrow mobile layout. All 82 existing saved run files remain unchanged.

## Derived grade in CAIR comparison cards — October 25, 2026

Every CAIR comparison card now displays `pro_palestine_score_grade` alongside the selected model grade and score, with its source score confidence and current tunable mapping. Selecting the derived grade as the comparison grade displays it once. Missing/incompatible source scores stay labeled. Review selectors still control the flagging rule. Node checks and desktop/mobile Chromium checks cover the extra metric, duplicate avoidance, mapping updates and unsupported scores. This is local presentation only; no new evaluations or saved-history changes.

## Candidate community state — October 25, 2026

New shared/playground requests include optional boolean `part_of_muslim_community` from an exact candidacy registry of owner-confirmed values. The final registry has 12 true and 12 false values, with no special annotations; the other 1,272 active repository candidacies remain unknown/absent. Ballot-name variants Jamal Khan and Raeena S. Lari are bound to their supplied office identities. Public religion/source research cannot set this owner-defined community field or overwrite a confirmed value. Published election JSON and both public readers are unchanged.

The repeatable collector searched all 1,285 initially unconfirmed candidacies with 1,277 distinct Serper queries, plus 15 accessible-source follow-ups and six public-guide queries. Jev triages discovery and separately reviews captured source text; snippets never establish the field. Every source-review question was resolved by owner input. Full per-candidacy coverage is archived with the registry; raw captures and exact model decisions remain in the ignored research work directory. See [CANDIDATE_COMMUNITY.md](CANDIDATE_COMMUNITY.md).

New state versions are `candidate-evidence-v7-community-observations` and `candidate-evidence-v7-local-federal-community`. The live local server reload preserved all 82 original run files byte for byte; no grading runs were submitted. The new offline community check covers exact identity, unknown/false semantics, provider/source separation, cache invalidation and protection of owner values. The final focused suites have nine community regressions and 38 playground regressions, with live-browser verification of current input previews and exact saved requests. The complete final offline release gate passes **40/40 checks**.

## Derived score grades and Vote for Peace context — October 25, 2026

The local playground adds deterministic `pro_palestine_score_grade` alongside Jev answers: six equal-width bands over 0–5, F through A, with each upper bound inclusive (0 through 5/6 is F). **Score → grade mapping** edits the five F–B bounds for nonlinear mappings; overrides persist under the server work directory. Results, race cards and optional CAIR comparisons refresh without model calls. API/download projections include the exact mapping and row field; original requests/responses, confidence, run files and archived batches remain unchanged. New CLI batches include the same field and accept `--score-grade-mapping`.

Vote for Peace was already in the focus registry, but the October 9 source import intentionally omitted Neutral cards from public endorsements. New shared/playground state versions now include the five exact reviewed Neutral candidacy mappings as observations, preserve Ally/Opposed labels and source provenance, retain primary/historical context and avoid duplicates or overriding newer canonical records. Public election data is untouched; rerun explicitly to submit the enriched state. See [JEV_PLAYGROUND.md](JEV_PLAYGROUND.md).

Validation: **39/39 release checks pass**, plus 38 focused Python regressions and Node boundary/comparison/export tests. Chromium verified nonlinear mapping, validation, reset/reload persistence, exact raw inputs/answers, reproducible downloads, immediate CAIR updates, missing/incompatible results and desktop/mobile layout. The live roster has 40 Vote for Peace observations (27 Ally, 8 Opposed, 5 Neutral). All 82 saved run files present at restart remain byte-identical; no live Jev calls were made.

## CAIR comparison and county filters — October 25, 2026

The playground shows each candidacy’s current CAIR Action recommendation, source, checked date and election phase beside its saved results. **Review CAIR differences** flags nonhistorical general/phase-unspecified Preferred or Endorsed records when the selected saved A–F grade is C–F **or** the selected 0–5 score is ≤2.5. Confidence remains visible without a cutoff. Question selectors support renamed questions; missing or incompatible answers are counted separately. Clicking a flagged candidate opens their saved prompt/answers; current recommendations never rewrite frozen Jev requests.

A global County filter applies to candidate selection/navigation, the race browser and CAIR comparison: each of the five counties, all five combined, or the full tracked roster. Shared contests are shown once. The Bay Area batch button continues to cover all five counties. See [JEV_PLAYGROUND.md](JEV_PLAYGROUND.md).

Validation: **39/39 release checks pass**, including 32 playground Python regressions and Node comparison-boundary tests. Browser fixtures cover CAIR/source/joint/primary/historical/unknown display, inclusive C and 2.5/5 boundaries, confidence without filtering, missing/incompatible/custom question contracts, all county modes, shared-race deduplication, empty selections, comparison navigation, live updates, exact saved inputs and desktop/mobile/Monaco behavior. Live checks find 109 candidacies with CAIR records and 3 review flags in the current saved evaluations, and preserve all 79 run files present at restart byte for byte. No live Jev calls or election-data edits were made for this display/review change.

## Five-county playground batches — October 25, 2026

The playground catalog now includes all five researched Bay Area counties (Alameda, Contra Costa, San Francisco, San Mateo, Santa Clara), plus nationwide House contests: **1,042 candidacies / 401 races**. The dedicated **Run Bay Area (877)** button submits only the 877 current candidacies in 340 regional races; **Run full roster (1042)** retains the nationwide House option. Shared county races are deduplicated by contest/candidacy identity, while provisional and qualified-write-in categories remain separate. Regional batch membership and questions freeze before calls begin, and progress/history/downloads label the scope `bay-area`. Existing evaluations remain available in Latest per candidate. No new live Jev batch or election-dataset edit is part of this capability change. See [JEV_PLAYGROUND.md](JEV_PLAYGROUND.md).

Validation: **39/39 release checks pass**, including 30 playground Python regressions. Chromium submitted a complete 877-candidate regional batch to a fixture transport and verified county-only membership, shared-race deduplication, edited questions, history labeling and desktop/mobile controls. The updated live local server exposes both counts and preserves all 79 saved run files present at restart; no live Jev batch was triggered by verification.

## Playground candidate history — October 25, 2026

The local playground now defaults to **Latest per candidate** across its stored baseline and saved local history. Switching A → B → A retains A’s latest successful evaluation, including after reload/restart. Failed or stopped retries show an explicit notice alongside the prior answer; differing prompts and stale evidence remain labeled. Each displayed answer keeps its exact saved request/hash and source-run provenance, while individual history entries remain isolated immutable experiments. A new **View candidate on election site** link opens the selected race and candidate-name filter in the published explorer. No new Jev grading batch or published election-data change is part of this fix. See [JEV_PLAYGROUND.md](JEV_PLAYGROUND.md).

Validation: **39/39 release checks pass**, including 28 playground Python regressions and the Node presentation checks. Browser checks cover A → B → A, reload persistence, exact saved prompts, failure fallback, history/latest switching, desktop/mobile layout, real Monaco editing and the live Kevin Park explorer link. Reading the existing 69-run history produced the current 685-candidate view without modifying any saved run.

## Firebase Analytics — October 25, 2026

Both public readers now share optional production-only Firebase Analytics for `G-QKNPZZ1CDJ`; local previews and the Jev playground are excluded. Canonical analytics URLs omit query strings/fragments and referrers, address values are not passed to Firebase, and advertising personalization/Google signals are disabled. The public pages disclose analytics cookies. See [ANALYTICS.md](ANALYTICS.md) for configuration, privacy boundaries and verification. This is a runtime/documentation change; the latest October 24 finance data is retained and the dataset publication marker is unchanged.

Validation: **39/39 offline release checks pass**. Chromium checks captured page views for both readers with the correct measurement ID and canonical URLs, with no test query/search/address values in analytics payloads. Local previews made no Firebase requests; blocking the SDK left both readers usable without page errors. Test collection requests were intercepted rather than sent to the production property.

## FEC money refresh — October 24, 2026 (2026-10-24.1) + cron failure root cause

Full scheduled refresh of both federal money layers: the independent-expenditure layer was refetched for all **268** FEC-linked printed and provisional federal candidacies via the official by-candidate Schedule E aggregates, and candidate-level receipt totals were re-read with the coverage-start guard; `finance.checked_on`/`ie_finance.checked_on` now certify October 24. Publication **2026-10-24.1** passed the complete offline release gate (38 checks) before push and was verified live on both readers.

**Why the daily cron appeared to fail:** the October 24 scheduled run executed on a checkout 16 commits behind `origin/main` (PRs #13–#16 merged after its base). It completed all FEC fetching, committed on that stale base, then its own pre-push divergence guard refused to push — leaving an orphan local commit while the cron itself reported success. No published data was affected; the run's work is fully re-derivable from live FEC APIs and today's refresh supersedes it. `scripts/refresh_fec_money.py` now fetches origin and applies a fast-forward-only merge before any API work (`f59f6f8`): a stale checkout advances automatically, and a genuinely diverged history fails in seconds for manual reconciliation instead of after an hour of fetching. The daily job continues through November 3 unchanged.

## Merged release — October 23, 2026 (2026-10-23.3)

At the owner's request, PRs [#14](https://github.com/salqadri/bay-area-elections-2026/pull/14), [#15](https://github.com/salqadri/bay-area-elections-2026/pull/15) and [#16](https://github.com/salqadri/bay-area-elections-2026/pull/16) are merged into main. The stacked #16 was retargeted to main after #15. Final content merge: `2a9a9be311dd468389bd479084af8c3a4fb84433`; schema remains 1.23. The combined tree passes **38/38 offline release checks**, including all playground, CAIR and local-ceasefire regressions. See the [publication record](reviews/2026-10-23-publication.md) for merge/deployment evidence and artifact hashes.

The public readers include the CAIR Action refresh (109 records: 81 Endorsed, 27 Preferred, 1 Opposed) and 36 new attributed Gaza records across 35 candidacies. Printed Gaza coverage is **1,049 items / 332 candidacies**; Kevin Park has CAIR Action Preferred plus the December 19 tracker report and December 26 opinion attribution about the blocked ceasefire effort. His two Gaza records are not endorsements, and no successful ceasefire passage is claimed. Source/identity/date holds remain explicit. Follow [CAIR_ACTION.md](CAIR_ACTION.md) and [LOCAL_CEASEFIRE_RESEARCH.md](LOCAL_CEASEFIRE_RESEARCH.md) for systematic future refreshes.

The Jev playground remains **local** at http://127.0.0.1:8787/, with all 685 tracked candidacies / 268 races and confidence-only display. New runs use current canonical evidence; historical results and local run history are unchanged. GitHub Pages serves the election readers and does not provide the local Jev API. No new grading batch or finance/roster refresh was run for this publication. Research and finance snapshot dates remain unchanged.


## Merged update — October 23, 2026: local Jev playground, confidence-only House and county evaluation (#14)

Owner chose a local workspace instead of a public Pages area/relay. New `scripts/serve_jev_playground.py` serves http://127.0.0.1:8787 with Monaco question editing (plain-text fallback), Run selected candidate / Run all / Stop, history/downloads, state groups with numeric district sort, all answers/confidences, and exact per-candidate State/Answers/Full request JSON. Keys remain server-side; only loopback Host/same-origin JSON writes are accepted. The iteration workspace puts the question editor next to a formatted selected-candidate response; a shared toolbar contains candidate selection, Run and history. Mobile uses Questions/Results tabs. Response rows expand for criteria/probabilities; generated State/Answers/Full request JSON is collapsed by default. Ctrl/Cmd+Enter runs the selected candidate. Single-candidate iterations make exactly one fresh call, retain the full roster for selecting another example, and label unrun candidates as input previews. Run history identifies each single-candidate target; old answers never carry into a new prompt. Runs freeze questions/current dataset and persist under ignored `.research/jev-playground/`; no canonical dataset or main-reader change.

Playground scope now unions all tracked nationwide House contests with every non-excluded race serving Alameda or Santa Clara County: **685 candidacies / 268 races**, adding 498 candidacies in 196 races. Shared county/House races appear once; local/state/judicial, provisional and qualified-write-in rosters remain distinct. New requests use `candidate-evidence-v5-local-federal-cair`: jurisdiction, office category, government level, county/seat/election/roster context and incumbency, plus separate CAL-ACCESS supporting/opposing spenders. Existing House results and histories remain exact; the additional candidates start unevaluated. Registry v3 also includes owner-requested CAIR Action with Preferred/Opposed/shared flags intact; old registry v2 and archived requests remain exact. The pre-CAIR expanded scope had 62 focused observations / 43 candidacies. 24 playground Python regressions and mixed-race label assertions pass.

Grader now supports `house-all` (187 candidates / 72 active tracked races, including Bay Area), uses the owner's exact October 23 JSON (`pro-palestine-v2`), and applies **no acceptance cutoffs or grade filtering**. Focused endorsement registry supplies only owner-named Track AIPAC/Vote for Peace/HAPAC plus five source-backed Israel-related organizations selected by Jev: **41 observations on 23 candidates, max three**, versus 3,690 full endorsement observations. Exact original relationships/phase/history stay intact; religion/ethnicity do not determine selection. Congressional states now resolve action IDs and preserve actual responses instead of blank title/date strings.

New immutable default `research/gaza-grading/house-all-focused-2026-10-23/results.json`: **187/187, zero call errors** on jev-1.14.0; A 22 · B 4 · C 2 · D 47 · E 2 · F 110. All answers/confidences remain visible, including low confidence. Historical v1 archive is untouched. See [workflow](JEV_PLAYGROUND.md), [implementation review](reviews/2026-10-23-jev-playground.md) and grading README. Release gate added Python/Node playground checks (36 at that base); merged as PR #14. The combined release above has 38 checks.


## Published update — October 23, 2026: endorsement image / HAPAC / AZ-01 evidence repair (2026-10-23.1)

Based on latest `d6238fe`. Fixes the image builder’s obsolete empty-county exclusion, adds an explicit image-publication draft to the batch runner, and supplies current-roster missing/older-image planning. The House pass retrieves 63 known endorsement pages: 59 initially ready; a responsive lazy-image parser fix (v3) resolves Bouchard as a 60th. Publishes **1,384 neutral image observations on 43 candidacies**, including Shah’s **31 organization logos plus one introductory image**. Three source-layout holds remain explicit. Existing v2 archives still replay exactly; current exports require v3 recrawl.

New `import_hapac.py` refreshes all 17 explicit current cards: **3 additions** (Shah, Pia Dandiya, current Murali Srinivasan), Melissa Hernandez corroborated once, Yang Shao held for office conflict, 12 outside the tracked printed roster. Old historical observations remain intact. New `research_gaza_gaps.py` audits current publication gaps rather than old done flags, includes nested topical platform URLs, uses Serper only for discovery and Jev alone for judgments. Publishes **Shah 3 dated records; Feely 2 dated records plus his current campaign statement**. Original 2023/2025 dates, article dating and guide observation limits are preserved; collector dossiers are synchronized. Held grades remain unpublished.

See [workflow](RESEARCH_GAP_RECOVERY.md), [audit](reviews/2026-10-23-az01-research-gaps.md), four new registered reviews, complete source/image dispositions and actual Jev responses. Schema stays 1.23. The 34-check gate includes 23 gap regressions; Chrome desktop/mobile loaded all 31 Shah organization logos and verified both Gaza disclosures. Structural comparison recovers the full baseline after removing exactly the additive research and publication metadata. At the owner’s request, Astra reviewed PR #13 and fixed two additional batch issues: capture reruns now refuse existing output directories before requests or writes, and multi-candidate Gaza guides retain separate candidate-bound source entries. Both regression cases failed before the fixes and pass afterward. Research records remain unchanged from the original PR. PR #13 merged as `a9a6795`; its GitHub Pages deployment succeeded. Live HTML and JSON matched the reviewed files byte for byte, and the live desktop/mobile browser pass loaded all 31 Shah organization logos and both Gaza disclosures. See the audit for the deployment link.

## Published update — October 23, 2026: state-aware race labels, State filter, district-number sort, split IE for/against (display-only)

Owner batch of reader fixes, all display-layer (dataset JSON untouched, no publication bump per the display-only precedent):
1. **State in race identifiers.** Shared `src/contest-label.js` renders ambiguous district/statewide races with their state — `CA CD-17`, `TX CD-35`, `AL — Statewide` — from each contest's OCD division; used by both readers' sidebar rows, search results and section groups. Stored `district_or_seat` values unchanged.
2. **State filter.** Sidebar adds a multi-select State filter derived from the same OCD parsing (Bay Area local contests are California); it composes with the existing status/party/incumbent filters and resets with them.
3. **District-number sort.** District races sort by natural number within each state (`CA CD-1` before `CA CD-17`) — numeric-run-aware comparison, no more lexicographic CD-11-before-CD-2.
4. **State in the opened panel.** The contest panel subtitle and meta grid now name the race's state.
5. **Opposing IEs rendered.** The IE section was a rendering gap only — the dataset has carried `direction: against` items for every FEC-linked candidacy since the Oct 20/21 collector work (no cron changes needed; the daily refresher already refreshes both directions). `src/finance-display.js` now renders two explicitly labeled blocks, **Supporting this candidate** and **Opposing this candidate**, each with its own spender list and subtotal, for every candidacy with activity in either direction.
New offline regression `scripts/check_contest_label.cjs`; explorer + finance display checks extended; release gate now **33 checks**, green on the rebuilt pages (`build_site.py --check` exact).

## Held batch — October 23, 2026: Jev Gaza grades for all 165 printed nationwide House candidates (NOT published)

New reusable `scripts/grade_gaza.py` (plan → grade → report; see [workflow](../research/gaza-grading/README.md)). Rubric is a versioned criteria file (`gaza-grade-v1` = the owner's Oct 22 JSON, always yielding `pro_palestine_score` + `gaza_grade`); scopes select races/regions for future runs. Per-candidate Jev state kept succinct by design: identity line, top spenders supporting/opposing with amounts, USCPR scorecard grades, platform points, reviewed Gaza statement, dated Gaza evidence, tracked congressional actions — no boilerplate notes. First batch `house-2026-10-22`: **165/165 graded, zero errors** on `jev-latest` (score questions need the current flagship; it resolves to jev-1.14.0) — A 16 · B 2 · C 1 · D 48 · E 1 · F 97, 83 accepted at confidence ≥0.75. **79 candidates have no direct Gaza evidence**; their grades are inferred from outside-money/platform context only and carry `has_gaza_evidence: false` — never present those as documented positions. Portable archive `research/gaza-grading/house-2026-10-22/results.json` (per-request decision cache stays in gitignored `.research/`). **Publication requires owner review of how grades should display** — nothing was written into the dataset.

## Published update — October 22, 2026 (night): X profile re-pass over the remaining queue (2026-10-22.5)

Re-ran `scripts/research_x_profiles.py` plan → collect → enrich → draft against the post-PR-#12 dataset: **290 missing-X candidacies with recorded campaign sites** (the earlier pass's cache had expired and a few candidates gained websites since). 268/288 URLs captured, 17 profile-metadata lookups via fxtwitter. Jev (`jev-1.13.0`, identity ≥0.90 / ownership ≥0.95) accepted **1 new account** — Shivraj Singh, Dublin City Council (footer social link on his own campaign site; profile name/location corroborate) — printed X coverage **446 → 447**. Holds stay explicit and unchanged in kind: 8 ownership + 7 identity holds, 20 unavailable captures, 254 captured pages with no profile link, and the same 558 missing-X candidacies without any recorded campaign site (still not searched — this remains a first-party self-link pass). Immutable review: `research/x-profiles/2026-10-22-pass2/review.json`; source S1505.

## Published update — October 22, 2026 (PR #12): missing X profile recovery (2026-10-22.4)

Pulled `87bbe2c` after Hermes merged/published PR #11. Xavier Becerra's recorded campaign site directly links `https://x.com/XavierBecerra`; the old local X sweep did not use campaign self-links, while the nationwide scaffold runner excluded California's existing race and skipped cached null outcomes. Historical search logs do not establish the precise original search failure. New `scripts/research_x_profiles.py` inventories current missing fields across all offices, captures recorded campaign pages, optionally corroborates linked handles via profile metadata, and uses Jev alone for candidate/ownership judgments. No searches were called. Old script is labelled historical.

Attempted **all 299 sites for 301 missing-X candidacies with campaign URLs**: 258 readable / 41 unavailable; 25 pages have direct profile links. Source-bound additive review recovers **11 accounts**, including Becerra; 8 identity + 6 ownership holds remain explicit. Printed X coverage **435 → 446** of 1,294. **558 missing-X candidacies have no recorded campaign site** and were not searched; 235 have no profile link in the captured page. This is a first-party recovery pass, not exhaustive account discovery. Existing primary/secondary accounts and all other research remain intact.

See [workflow](X_PROFILES.md), [audit](reviews/2026-10-22-x-profiles.md), and `research/x-profiles/2026-10-22/review.json` for actual source/model evidence and every disposition. Apply uses a focused exact before/after dataset-hash adapter for scalar X links; an identical rerun is a no-op. The release gate adds `check_x_profiles.py` (31 checks total, 21 new regressions). Hermes reviewed PR #12 independently — the full 31-check gate passed on the branch, a structural revert recovered main byte-for-byte after removing exactly the 11 additions plus S1494–S1504 and coverage/version metadata, and the review's base/post-state canonical hashes bind to main and the merged dataset — then merged and published it; schema remains 1.23.

## Published update — October 22, 2026 (late): candidates sorted by money, endorsements, party (display-only)

Per owner request both readers now order each race's printed roster: a verified incumbent always leads, then higher reported total receipts (FEC or CAL-ACCESS; a reported zero outranks an unknown amount — unknown is never treated as zero), then more endorsement records, then Democratic/Republican affiliation (DFL counts as the Democratic ballot line) before other parties and nonpartisan candidates, finally the collated name. Shared `src/candidate-sort.js` (`CandidateSort.sortRoster`) is applied at render time in `rosterSection` (explorer) and the address reader's candidate loop; the dataset's stored roster order is untouched, so no publication-version bump (display-only precedent). New offline regression `scripts/check_candidate_sort.cjs` (release gate now 32 checks) covers the rule order, incumbent ties, non-mutation, both generated pages embedding the module, and that every printed roster renders as an incumbent-leading permutation.


## Published update — October 22, 2026: Ballotpedia endorsement supplement (PR #11, 2026-10-22.3)

New `scripts/ballotpedia_endorsements.py` supplies plan → fetch/import → extract → Jev review → draft → archive, using only recorded Ballotpedia profile URLs and explicitly current-year Endorsements sections. The parser preserves cycle/phase/category boundaries and the polling-chart heading exception. Shared `endorsement_identity.py` prevents exact cross-source duplicates in both collectors; Jev resolves name variants and screens all proposed new entities against existing names/curated publishers, including acronyms. Older/general/primary context and curated relationship controls are preserved. New rows are `reported` secondary evidence with source-section links and observation-date notes.

All 934 unique recorded URLs were attempted: **236 readable / 698 empty or challenge responses**. The reviewed publication adds **200 records (103 endorsements, 97 recommendations) on 54 candidacies**, retains **167 corroborations** without adding displayed duplicates, and holds **857 parsed rows plus 47 source-layout fragments**. Unavailable URLs and unsupported layouts remain explicit queues; saved HTML imports support Hermes's existing captures. **Mike Rogers: 1 → 8**, with Donald Trump retained once, seven new endorsements, and four guide entries held for relationship/entity uncertainty. This is a scoped source supplement, not exhaustive endorsement certification.

See [workflow](BALLOTPEDIA_ENDORSEMENTS.md), [audit](reviews/2026-10-22-ballotpedia-endorsements.md), registered review `research/reviews/ballotpedia-endorsements-2026-10-22.json`, and portable source/model archive `research/endorsements/ballotpedia-2026-10-22/`. Schema remains 1.23. Roster facts, finance, platforms and Gaza records are preserved. The release gate now includes the Ballotpedia regressions (30 checks total). Hermes reviewed PR #11 independently — the full 30-check gate passed on the branch, a structural revert recovered main byte-for-byte after removing exactly the 200 additions plus version/coverage metadata, and the archive's review SHA-256 binding was verified — then merged and published it.


## Published update — October 22, 2026: California state campaign finance from CAL-ACCESS (schema 1.23, publication 2026-10-22.1)

New `scripts/ca_campaign_finance.py` (download → build → attach) publishes the Secretary of State's nightly raw export (`dbwebexport.zip`; zip/TSVs/derived snapshot stay gitignored under `.research/ca-finance/`, run timestamps in `run-state.json`). **41 of 50 printed CA state candidacies carry `ca_finance` receipt totals and 36 carry `ca_independent_expenditures`** across Governor, statewide, Senate, Assembly and BOE races (attach: 8 candidacies without a match — e.g. AD-18 Sandford files only a Form 496 notice; Andre's committee statements are genuinely absent). Schema 1.23 adds `ca_finance_settings`, `ca_ie_finance`, numeric-keyed `ca_ie_spenders` (51 spenders), candidate `ca_finance`/`ca_independent_expenditures` and two coverage metrics; source S1493; the shared renderer shows CA boxes beside FEC ones. Method mirrors the federal layer: Form 460 line-13 receipts since 2025-01-01 (amendments supersede, pre-cycle periods excluded not split); IND + support/oppose Schedule E/D rows with a parseable EXPN_DATE (the date requirement dedupes coalition memo rollups against dated schedule-D detail; notices stay out). Matching fixes found during build: dataset jurisdictions read `California State Senate`/`California State Assembly`/`California State Board of Equalization` (prefix match now — the exact-equality check silently dropped all legislative/BOE races); nickname groups (Hilton files as Stephen); hyphenated-surname variants (Bauer-Kahan stored `BAUER-KAHAN`). Governor sanity: Becerra $34.51M receipts / $20.64M IE-for; Hilton $26.41M / $1.03M against — consistent with published reporting. Full release gate green after rebuild (`build_site.py --check` exact). Follow-ups: optional `note_id` for null-receipt candidacies once a note is registered; consider BOE-2 Pimentel/Lieber zero-period edge (Lieber receipts 0.00 is a reported zero); re-run cadence — the export refreshes nightly, so a weekly download+build+attach before November 3 keeps amounts current.

## Published update — October 21, 2026 (late): Governor split out as its own category within State (2026-10-21.9)

Per owner request the State section now groups **Governor → State Senate → State Assembly → Other state offices** on both readers (`sectionLabel`/`priorityCompare` + `subgroup`/`compareRaces`; Governor leads as top-of-ticket, mirroring Senate-first in Federal). Grouping is display-only — `office_category` stays `Statewide executive` and the JSON positions array order (Senate→Assembly→statewide per check_data) is untouched; all 37 governor races (36 statewide + CA's) move into the new block. `check_explorer.cjs` State assertions rewritten for the new group keys/order — note its DOM fixture must be regenerated (`prepare_dom_fixture.py`) after any ballot.html change or it tests stale markup. README ordering paragraph updated; House platform batch published earlier as .8 (99 candidacies / 725 quoted positions via review `campaign-platform-positions-2026-10-21-house`).

## Published update — October 21, 2026 (late night): nationwide House platform positions published (2026-10-21.8)

Closed the last House follow-up from the .7 batch: platform positions for the 108 new US2026 House campaign sites. Driver `.research/run_house_platform_20261021.sh` crawled + extracted all queued sources overnight (crawl 14 batches + retry sweep; extract drained to remaining=0 at 03:54Z). Imported the **108** new responses via `research_campaign_issues.py import-reviewed` and published through registered review `research/reviews/campaign-platform-positions-2026-10-21-house.json` (distinct ID from the morning Senate/governor review of the same date — IDs must be unique in `publication-reviews.json`): **99 candidacies / 725 mechanically gated, verbatim-quoted platform points** (98 `positions_found`, 1 scoped `no_positions_found`). Held back: 641 `no_website` + 554 `unavailable` inventory states (never findings of absence). Nationwide US2026 platform coverage is now **250 candidacies / 1,847 points** (House 99/725 + Senate/governor 151/1,122). Printed coverage metric `printed_candidates_with_platform_positions` = 578. Full release gate green (`passed: true`).


## Published update — October 21, 2026 (night): nationwide U.S. House races added (2026-10-21.7)

**61 in-play nationwide House contests** (`US2026-071..131`, 165 printed candidates) joined the dataset alongside the Senate/governor compilations: all 435 districts triaged from each race's Ballotpedia page — mechanical ratings pass + **Jev System One** in-play classification marked 62 races; DC's non-voting delegate excluded (same class as territories). Rosters confirmed against BP general-election blocks with per-contest provenance. The Federal section now groups **U.S. Senate first, then U.S. House** on both readers (`sectionLabel`/`priorityCompare` + `subgroup`/`compareRaces`; asserted in `check_explorer.cjs`). Layers: FEC candidate-level receipts (60 published totals; 72 filers without a summary stay null + N905 — never zero; the committees refetch must NOT pass `cycle=2026`, which hides P/A committee IDs on new filings and had blocked 18 receipt attaches); IE layer extended to **all 268 FEC-linked federal candidacies** (attach: 176 with activity, 453 spenders; collector now tolerates FEC's unclassifiable `Other`-direction aggregate rows by validating then excluding them from for/against snapshots — encoded in `check_fec_money.py`); verified links via the same mechanical gates (+108 campaign sites, +122 X accounts). **Provenance repair:** link tags moved from S1101 (which was always the scaffold FEC-summary source — 17ec4e4's registration silently no-op'd) to dedicated Serper source **S1492** across all 320 previously-tagged candidacies; note N910 shared. Gaza nationwide pass extended to House scope: 419/419 people, 763 items — 86/165 printed House candidates now carry evidence (dataset coverage 221→307); five collector summaries rewritten as concise third-person summaries per the publication guards (raw `X post:` excerpts / field-limit truncation), quotes preserved verbatim. Endorsement batch for the 108 new sites: crawl 645/6 → extraction 109/109 ok → quote gates 26,471 proposed / 1,844 held → **Jev System One** classified the 4,133 new proposals (242 API calls; 12,294 accepts, 14,177 attribution holds kept explicit) → attach added **2,147 reviewed records on 62 candidacies** (+96 dated campaign-claim notes); printed endorsement coverage 455→516. `invalid_endorser_name` fixed: 'cookie' now blocked only in banner phrasing — FL endorser **Cookie Kennedy** was a substring false positive. Follow-ups: platform positions for the House sites not yet run; optional spot-check of the four CA nationwide CDs against SOE certification when reachable. Scripts live in `.research/house_2026/` (fetch_bp, parse_bp, triage_inplay, match_roster, build_house_positions, integrate_house, discover_links_house, attach_links_house, fill_receipts, promote_attached); ledgers there are gitignored but must survive until the platform batch publishes.

## Published update — October 21, 2026: final nationwide platform batch (2026-10-21.1)

Completed the Oct 20 nationwide crawl queue (all 162 US2026 campaign sites crawled + extracted; driver `.research/run_nationwide_platform_20261020.sh`). Imported the **84** new nationwide responses via `research_campaign_issues.py import-reviewed` and published through registered review `research/reviews/campaign-platform-positions-2026-10-21.json`: **79 candidacies / 591 mechanically gated, verbatim-quoted platform points** (all `positions_found`). Five sources stayed held as `unavailable` (Moore AL-Sen, Christensen AZ-Gov, Paxton TX-Sen, Bailey IL-Gov, Dixon AL-Gov — their crawls yielded no usable pages: robots.txt unavailable or a page-limit stop before any policy page was captured; never findings of absence). Nationwide US2026 platform coverage is now **151 candidacies / 1,122 points** across printed + filed rosters. Printed coverage metric `printed_candidates_with_platform_positions` = 479. Full 29-check release gate green (`passed: true`).

## Published update — October 20, 2026 (evening): nationwide queue closed — all 70 Senate/governor contests confirmed (2026-10-20.13)

All **70** nationwide U.S. Senate and out-of-state governor records moved from `unverified` to `confirmed`; the dataset now has **zero unresolved scheduled contests** (486 positions: 410 confirmed / 513 seats / 76 excluded; 1,091 printed entries). Waves 1–11 reconciled 34 contests against captured official state lists (raw captures under `research/federal_2026/official_reconcile/raw/`). The final 36 used a simplified pipeline (`adjudicate_bp.py`): serper.dev → the race's Ballotpedia page → mechanical parse of its November 3, 2026 general-election candidate block (ticket-aware for governor pages: only each `/` ticket lead is the gubernatorial nominee; `(Write-in)` and withdrawn/disqualified entries separated) → **Jev System One** per compiled name (candidate_row acceptance ≥ 0.75) plus one extra-detection question per page-listed name outside our roster. 35 contests flipped FULL with zero active extras; write-in slates are recorded in contest notes (e.g. GA Ossoff race: three certified write-ins). A follow-up pass re-adjudicated all 12 earlier BALLOT-tier contests against their Ballotpedia pages: every one is now FULL (**zero confirmed contests lack a complete roster**). The wave-1 'extras' were office-block window noise (address fragments, other-office rows); CT Governor's Adgers/Noe tickets are write-ins per Wikipedia (write-in candidates section) and are noted on the contest rather than printed. Roster corrections on documented evidence: NH Kiper withdrew (Villee L added), IA Wilson did not qualify (petition litigation lost; Wikipedia "did not qualify"), WY Kibler withdrew pre-certification (Bextel C added per the SOS general roster) — Kiper's orphaned Gaza item GE-0846 quarantined as `candidate_withdrew_off_ballot`; AK Senate's compiled 'Dan J. Sullivan' was a mis-compilation of **Daniel J. Sullivan Jr.** (AK SOS cert lists both him and incumbent Dan S. Sullivan; FEC ID S6AK00326 follows the rename, ledger file renamed to match). Ballotpedia is a secondary source: each flip's note says which source class verified it, and captures.json keeps per-contest provenance (`wave2` official captures vs `wave2_bp`). Remaining follow-up: none blocking — optional spot-checks of CT independents and OH Levy (Independent, PSL-filed) against state certification when those portals become reachable.

## Published update — October 20, 2026 (afternoon): official-source reconciliation wave 1 (2026-10-20.2)

17 of the 70 nationwide Senate/governor contests moved from `unverified` to `confirmed` against captured official state candidate lists (raw captures under `research/federal_2026/official_reconcile/raw/`, content-addressed). Eight reached FULL tier (roster complete, candidates promoted): NM- and SD-Senate, CO-, FL-, MD-, NM-, OH- and SD-Governor; nine more are ballot_status-only (BALLOT tier — official list shows extra active names so the printed roster stays provisional). Where Jev excerpt windows drifted or misjudged wide-table rows (CO Marx/Weiser, MD Ellis/White, OH Kissick full-name rows), a mechanical office-row extraction override was applied with per-candidate evidence recorded in `adjudication.json` (`override_evidence`). FL Governor carries two certified write-ins (Kathy Anderson, Erik Morris) noted on the contest. Remaining 53 unresolved: OK/NH/HI captures were primary-stage or lacked a general-election marker; IA-Wilson, NH-Kiper and WY-Kibler compiled names do not appear on their official lists at all (independent/Constitution filings possibly certified later — needs per-state follow-up). Also fixed: template artifact in candidate name "Cinde Warmington }}" across dataset + 10 research files (review registry re-pinned), empty `filed_candidates_not_confirmed_on_ballot` arrays removed (schema minItems=1), explorer unresolved-count pin updated 70→53.

## Published update — October 20, 2026: FEC independent-expenditure totals (2026-10-20.1)

Merged as PR #10 (Codex). Publication `2026-10-20.1`, schema unchanged (1.22). The shared collector previously added overlapping 24-/48-hour notices and regularly scheduled reports; `most_recent` resolves amendments within a report, not overlap between report streams. It also used a filing-wide memo heuristic instead of FEC's memo exclusion. UDP against Abdul El-Sayed reproduces exactly: $20,140,908.74 regular + $20,423,765.29 notices = $40,564,674.03 published. Correct UDP total: $20,140,908.74 — independently re-verified against the live by-candidate API during Hermes review (El-Sayed card: $2,422,492.19 for / $20,829,487.24 against).

The collector now uses the same official by-candidate aggregates as FEC.gov with an explicit two-year cycle. All **136** FEC-linked candidacies were refreshed October 20; **69** have changed amounts (12 printed House, 57 provisional Senate). Current totals and per-spender deltas are in the [review and reproducible audit](reviews/2026-10-20-fec-ie-reconciliation.md). These are regular-report totals: recent notice-only spending remains outside them. Do not call the full snapshot reduction duplicate dollars or unique national spending. Receipts, ballot records and political evidence are unchanged. Earlier finance methods/counts below are historical and superseded.

After merging, use the ordinary refresher; its shared adapter now uses a separate cycle/version-tagged cache. Existing raw caches cannot be reattached as corrected data. Attach refuses missing current-method coverage; an explicit check date cannot exceed the oldest actual candidate retrieval. The audit includes Jev decisions, exact UDP source rows and all candidate snapshots for Hermes.


## Published update — October 19, 2026 (night): Senate FEC matcher fix (2026-10-19.3)

Owner reported missing FEC money on nationwide Senate cards (e.g. Abdul El-Sayed MI despite an active FEC page). Root cause: `research/federal_2026/build_positions.py` matched printed names against FEC filers by comparing only the **first token of the FEC surname** to the **last token of the printed name**, so hyphenated/compound surnames never matched — "Abdul El-Sayed" (last token `SAYED`) vs FEC `EL-SAYED, ABDUL` (first token `EL`). Four real 2026 filers were silently dropped from both money layers (receipts and the IE layer, which keys off `fec.id`): El-Sayed MI S6MI00418 ($45.18M), Cindy Hyde-Smith MS S8MS00261 ($4.51M), Ashley Hinson IA S6IA00314 ($13.47M; FEC legal name "ARENHOLZ, ASHLEY HINSON" — added as a reviewed override), Rachel Fetty Anderson WV S6WV00188 ($137K; compound surname). The fix compares the **full normalized FEC surname** against all trailing 1–3 token sequences of the printed name (`surname_forms`), plus the Hinson override. Re-running the matcher changed exactly six candidacies — the four above plus the two Alaska Sullivan names whose reviewed overrides existed in the script but had never been re-run into the draft (challenger S6AK00326 $30K; incumbent S4AK00214 $11.16M) — with zero changes to the other 108 matches and no new collisions. The remaining nine unmatched Senate names were verified live against the FEC API: genuinely no 2026 filing (minor-party/independent non-filers; note N907). `research/federal_2026/apply_fec_match_fix.py` (committed, idempotent) attached the six FEC records with candidate-level totals + authorized committees (retrieval dated October 19 to match `finance.checked_on`; new shared note N1300), dropped contest-level N907 from the five races where every filed candidate now has an FEC record, then `fec_independent_expenditures.py run + attach` added Schedule E snapshots for all six (Senate totals rise to 114/123 with filings, 58 published totals; IE activity on 61 candidacies, $545.4M for / $1,215.3M against). The "Unresolved" label the owner saw is **unrelated and intentional**: all 70 US2026 compilations stay `ballot_status: unverified` (N903) until official state-source reconciliation — that queue is unchanged by this fix. Full 29-check release gate green; README Senate paragraph updated to the corrected counts.

## Published update — October 19, 2026 (evening): explorer defaults to All contests (2026-10-19.2)

Owner reported the nationwide races "not visible" on the live site: the data was published, but the explorer's ballot-status filter defaulted to Confirmed, and all 70 US2026 compilations are `unverified` until official reconciliation — so they were hidden behind a click. Per the original spec (unfiltered view shows every federal race), the default is now **All** (`state.status:'all'`, matching button markup; `resetFilters()` too). County filters unchanged: nationwide contests have empty counties and correctly disappear when a county is selected. Fixture updates in check_explorer.cjs: default count asserts `positions.length`; county-count loops no longer pre-filter confirmed; party/incumbent loops union `candidates` + `filed_candidates_not_confirmed_on_ballot` (nationwide records can carry null printed rosters); the State-order assertion uses relative positions because excluded contests now appear under All.

## Published update — October 19, 2026 (late): nationwide platform positions (2026-10-19.1)

The campaign-site crawl cache was drained to 459/459 sources; the `research_campaign_issues.py` pass over the ~78 newly crawled nationwide sites produced **531 mechanically gated, verbatim-quoted policy points across 72 provisional Senate/governor candidacies**, published via registered review `research/reviews/campaign-platform-positions-2026-10-19.json`. Remaining filed candidacies are `no_website` inventory (93) or unreviewed/unavailable captures (90) — never findings of absence. Publication-path extension landed with this release: `reviewed_updates.prepare`, `publication_reviews.check_registered_reviews` and the reconstruction fixture now accept targets in `filed_candidates_not_confirmed_on_ballot` for empty-county Federal/Governor contests explicitly referenced by a review, while all `printed_*` coverage metrics stay printed-roster-only (matching check_data). Note: `research_campaign_issues.py extract` processes 25 sources per invocation — loop it until processed=0.

## Published update — October 19, 2026: endorsement batch published (2026-10-18.2)

The full campaign-site batch finished: all 543 tracked sites re-crawled and extracted (nationwide first), quote gates → Jev review → recorded decisions (22,943 accepts / 4 rejects / 2,273 attribution holds kept explicit). Attach added 9,499 reviewed records — printed coverage is now 19,258 relationship records on 391 of 875 candidacies, plus 2,879 records on 64 nationwide filed-but-unconfirmed candidacies. Three publication-integrity fixes landed with this publish: (1) `attach` no longer seeds empty `endorsements` arrays when every accepted proposal dedupes against published records (schema requires non-empty); (2) campaign-page claims from curated-capture endorsers — CAIR Action, Vote for Peace/AROC Action, California Jewish Democrats (whose own reviewed capture expresses support ratings, not endorsements) — are held rather than attached as new `endorsed` records; (3) the historical-reconstruction fixture no longer resurrects a retired record when newer reviewed evidence already refilled that endorsement slot. Wiener regression: 69 text + 50 images (campaign page legitimately grew from 53 to 63 campaign-claim endorsers on the refreshed crawl); display fixtures updated to match.

## Published update — October 18, 2026 (late): unified endorsements list + batch audit archive

Both readers now render text and image entries in one **Endorsements and recommendations** list. Scott Wiener is the regression case: 59 text records plus 50 image entries, with source links and collapsible metadata. There is no separate campaign-image disclosure. This is a presentation change; source observations, political relationships and published data remain unchanged. A follow-up (PR #9) renders each text endorsement as its own bordered row with the endorser's image beside the text — display only, with fixture assertions that each entry keeps exactly its own image and note.

The original 381-site local collection/extraction/Jev run is complete; see the portable batch audit and report under `research/endorsements/batch-2026-10-18/`. Machine acceptances are proposals, not new published claims: title variants, duplicate sources, office/cycle attribution and quote attribution require a publication review. The 162 distinct campaign sites added for provisional nationwide candidates were refreshed through the current parser and fully extracted on October 18; their proposals ride the same batch runner gates (Jev review + record-decisions) and publish with the same reviewed pass. Do not merge proposals directly into published records or treat failures/holds as evidence of no endorsements.

## Latest update — October 18, 2026: external image URLs

Publication **2026-10-18.1**, schema **1.22**. Campaign-image evidence now loads original external campaign/CDN URLs directly, with an always-visible **View image** link and lazy preview. Copied image assets and the downloading/archiving option have been removed. The 463 evidence URLs, October 17 source dates and dispositions are unchanged; the 176 reviewed current-grid observations retain full page metadata and the other 287 retain explicit legacy-placement limits. The [registered correction](../research/reviews/external-endorsement-image-urls-2026-10-18.json) preserves the prior review history. See [the deterministic workflow](ENDORSEMENT_IMAGES.md) for URL-only batch updates and worker instructions.

## Latest update — October 17, 2026: campaign image evidence (schema 1.22)

Publication **2026-10-17.4**. See [the repeatable image workflow and worker instructions](ENDORSEMENT_IMAGES.md). All 315 explicitly filename-derived assertions were retired into neutral image observations; 14 text-based Gun Sense designations are now distinctions. Four primary pages were checked: Wiener (50 grid images, 53 named people), Panetta (23 images), Pellerin (20), Connie Chan (83). All 176 selected image URLs are preserved with source-page fingerprints, every source-image occurrence has a disposition, and exact before/after changes are registered. The dataset retains 287 older image URLs with explicit unreviewed-placement limits. Fresh broad collection can run deterministically from the campaign ledger (`export-ledger` → `build-queue`) or be split into capture-based worker tasks. Named proposals require source-local text and immutable capture bindings; old filename decisions and URL-only shortcuts cannot republish. No roster, finance or Gaza research was changed. The nationwide scaffold below is retained.

## Latest published update — October 17, 2026: nationwide Senate + governor scaffold (schema 1.21)

Publication version **`2026-10-17.3`**, schema **1.21**. The dataset now carries **all 35 contested 2026 U.S. Senate races** (33 Class 2 + FL/OH specials, terms ending January 3, 2029) and **35 out-of-state governor races** as `US2026-001…070` with empty `counties` arrays: they appear only when no county filter is selected (explorer cards show the state in the district chip; the address matcher cannot match them by design — an empty-county record never intersects a voter). Schema changes: `counties.minItems 1→0`, OCD pattern widened from California-only to any US state, and the party registry extended for minor ballot parties (I/L/C/DFL/LMN/NLP/PSL/SWP/WCP/UCP/AFP/AVP/FWD/UP/AZIP/GMPJ/OPP/PGP/NWPP).

Rosters were compiled from each state's certified candidate lists as aggregated by the cited Wikipedia race-summary tables (S1099/S1100, cached wikitext + parser in `research/federal_2026/`) and are held **`ballot_status: unverified`** with names under `filed_candidates_not_confirmed_on_ballot` per the research contract — official-source reconciliation is the open queue (N903). FEC money for Senate filers uses the existing pipeline: candidate-level 2026 receipts (108/123 candidacies have filings; 52 published totals; null ≠ zero) and Schedule E IE snapshots attached through `fec_independent_expenditures.py` extended to provisional federal filings ($476.1M for / $981.6M against across 57 candidacies with activity; per-opposed-candidate counting inflates the "against" side by design). The daily FEC cron and both IE paths now cover provisional filings; the coverage metric stays printed-only until contests are confirmed. Governors have no FEC data (state elections) — money research there needs separately cited state sources. Alaska's two printed Sullivan names were disambiguated against FEC filing evidence; the collision guard in `build_positions.py` holds ambiguous mappings instead of guessing.

**Open queue for this layer:** (1) reconcile all 70 rosters against official state SOE/certification pages, flipping contests to confirmed with printed rosters as evidence allows — per-state `.gov` certified-list leads are cached in `research/federal_2026/official_leads.json` (68/70 have direct hits); the sweep scripts and link ledger live in `research/federal_2026/`. (2) Candidate research layers: verified X accounts + campaign sites DONE (162 sites / 181 X handles, note N908, Serper source S1101), Ballotpedia pages DONE (135, S1102), Gaza stance collector run DONE (478 items across 140 candidacies; merge + sync-published clean); DONE: endorsement batch published (see Oct 19 section) and nationwide platform positions published via registered review campaign-platform-positions-2026-10-19.json (531 points on 72 candidacies; rest no_website inventory or unreviewed sites). (3) Governor money from state sources — owner deferred these races' money layer on October 18; unknown stays null, never zero.

## Previous published update — October 17, 2026: campaign-platform round 2 (Gaza platform)

Publication version **`2026-10-17.1`**, schema unchanged (1.20). Round 2 of the Gaza platform workflow deep-re-crawled the **114 sites** whose first-pass crawls were page-limited or partial (`crawl --source ID --max-pages 24 --max-depth 3`) and re-reviewed every refreshed packet under mechanical gates. Published through registered review `research/reviews/campaign-platforms-2026-10-17.json` (**50 changes**): coverage rises from 171 to **221 printed candidacies with `gaza_platform`** — now **5 `statement_found`** (new: Jamie Joyce's Gaza blog page refusing pro-Israel PAC money; Aisha Wahab's campaign attack-ads rebuttal affirming her "yes" forum answer that Israel committed genocide in Gaza; Aaron Tiedemann's positions page crediting him with creating Albany's 2024 Gaza Ceasefire Resolution) and **216 scoped silences**. Reviewer passes: LLM source review via direct `qwen/qwen3.8-27b` chat/completions calls (≤2 concurrent, whole-packet prompts ≤30K chars else chunked extract→decide, gate-mirror validated with one repair round) plus a deterministic keyword-scan + **Jev System One** classification pass (`accept choice+probability ≥ 0.75`, entries in per-question instructions) that resolved the oversized sites — Jev handled Jamie Joyce's 1.4MB capture (77 snippets → 9 accepted) where LLM prompts overflowed. `.research/round2_build_review.py` regenerates the review manifest from `held-export.json` with mechanical gates (HTTPS capture whose checked_on == record date; statement sources must be the statement page itself; name tokens on site).

Remaining held: **161 candidacies `unavailable`** — failed captures barring silence and JS-rendered shells (e.g. votekanani.com) needing browser/Wayback exception captures via `scripts/render_failed_sites.py`; one scoped silence (Cheris Crocker-Root) barred by the HTTPS provenance guard; ~90 JS-only/bot-walled sites still need headless-render re-capture before their packets can flip from unavailable to reviewed. The issues-layer round consumed the same recrawl: `research_campaign_issues.py import-reviewed` is current as of this round.

## Previous published update — October 16, 2026: general campaign platform positions (schema 1.20)

Publication version **`2026-10-16.2`**, schema **1.20** (new `platform_positions` candidate field; see [CAMPAIGN_PLATFORMS.md](CAMPAIGN_PLATFORMS.md) "General platform positions"). **328 printed candidacies published**: 327 with up to eight of the campaign's own top policy points (2,099 points total — each a fixed topic label + plain summary + quote mechanically verified as an exact substring of a hash-verified capture + source page) and 1 scoped `no_positions_found` silence. Registered review: `research/reviews/campaign-platform-positions-2026-10-16.json`. Extraction ran the local `qwen/qwen3.8-27b` (medium reasoning, ≤2 concurrent) over all 381 crawled sites via `scripts/research_campaign_issues.py`; a 40-candidacy/249-point random audit against captures found zero quote failures; two conservative holds were caught by the review builder's extra gates (HTTP-only capture; candidate name absent from site text).

Held follow-up queue: **53 candidacies `unavailable`** — page-limited crawls needing deeper re-crawl, JS-only/bot-walled sites needing headless-render exception captures (shared with the Gaza platform round), plus Shivani Tripathi's scoped silence whose "My Priorities" section is JS-rendered and worth a rendered re-check. Rerun anytime: `import-reviewed` all responses → spot-audit → `research/campaign-issues/build_review.py` (fresh dated output; immutable once written) → `reviewed_updates.py preview/apply` → bump publication version → rebuild → 26-check gate → push + verify live.

## Previous published update — October 16, 2026: first campaign-platform publication pass

Publication version **`2026-10-16.1`**, schema unchanged (1.19). The deferred bounded website pass from [CAMPAIGN_PLATFORMS.md](CAMPAIGN_PLATFORMS.md) was executed across all 381 planned sites and published through the common review workflow as registered review `research/reviews/campaign-platforms-2026-10-16.json` (171 changes, each bound to a hash-verified capture). Coverage: **171 printed candidacies now carry `gaza_platform`** — **2 `statement_found`** (Alex Behrend, SF Supervisor D6: own policy page calling for full divestment from Israel and no city contracts with companies doing business with Israel; Connie Chan, CA-11: campaign-controlled page adopting pro-ceasefire/anti-Gaza-invasion framing plus site-wide AIPAC-money refusal pledge) and **169 scoped `no_statement_found`** silence findings. Every silence states its bounded scope (URLs, capture dates, crawl limits) and asserts nothing about statements elsewhere.

Method: plan → sequential crawl (`--max-pages 12 --max-depth 2`) → per-source packets reviewed by subagents under the guide contract → `import-reviewed` held export → deeper re-crawl (`--max-pages 24 --max-depth 3`) of the 116 sources that stopped at page limit with queued links, then packet regeneration and re-review of those sources. Silence findings were only accepted where the crawl exhausted its linked scope with zero failed captures; page-limited or partially failed sources stay `unavailable` with concrete follow-ups (382 candidacies held). 492 inventory records remain `no_website`. One subagent-fabricated identity quote (Connie Chan) was caught by the mechanical containment gate and corrected from the actual capture — a reminder that packet-hash validation catches invented citations.

Still held for follow-up at that time: ~114 sources whose deeper re-crawl review was then in progress (completed and published October 17 as round 2 — see the latest update), JS-only/bot-walled sites needing browser-render or Wayback exception captures (~90, still open), HTTP-only captures (e.g. Cheris Crocker-Root) that the HTTPS provenance guard bars from publication, and the Tom Ramsey wrong-person `campaign_url` inventory correction. The held export at `.research/campaign-platforms/held-export.json` remains the working queue for a future third platform review round.

## Previous published update — October 15, 2026: congressional records, official publisher grades and platform workflow

Merged as PR #6 on October 15, 2026 (merge commit `36e4305`) after the full 24-check release gate passed on the branch; Pages deployment verified live at publication version `2026-10-15.1`.

Schema **1.19**, publication version **`2026-10-15.1`**. This PR adds a separate local congressional legislative capture and official USCPR Action grade capture. It binds **11 printed candidates to 18 tab member records** and **nine official grade profiles**, including Barbara Lee's prior House record under her Oakland mayoral candidacy and Aisha Wahab's new House record. The existing **245 prose evidence items under 82 candidacies** remain separate. Both readers show one collapsed **Gaza evidence** disclosure with distinct USCPR Grade, congressional voting/legislative record, reviewed campaign platform and web/social/guide sections. The initial PR contains no published platform results and does not claim a broad website pass.

The source tracker capture covers all four current/historical House/Senate tabs: **523 tab member records, 150 tracked action columns and 25,830 member/action cells**. Preserve each tab's context, action date, source wording, kind and assessment; some actions repeat across tabs and current tabs include older dates. These counts do not mean unique people/votes or a complete career history. Pale green/red/gray UI labels follow the sheet's response assessments, with accompanying text. **Column A is ignored for grades**. Grades come exclusively from the separately captured official USCPR feed and retain 119th Congress versus publisher Lifetime periods. The feed still names Swalwell while the Clerk confirms successor Wahab; do not transfer a grade by reused identifier. See [GAZA_VOTING_RECORDS.md](GAZA_VOTING_RECORDS.md) for identity proofs, normalized snapshots, source limits and adapter commands.

`scripts/sync_gaza_records.py capture --checked-on YYYY-MM-DD` captures both sources. `review` drafts exact old/new candidate/shared changes using the reviewed identity links; `review --apply` can apply a newly generated review locally after source review. To inspect a written draft before applying, use `reviewed_updates.py apply` as documented in [MAINTENANCE.md](MAINTENANCE.md). Neither script commits, pushes or deploys. Source snapshots, source hashes and the immutable registered review belong together. Roster decisions, ballot/finance snapshot dates and existing endorsement/prose-evidence fields are preserved. The final build, complete **24-check** release gate and desktop/mobile Chromium checks on both readers pass; see the [implementation review](reviews/2026-10-15-gaza-records.md). Hermes re-ran the 24-check gate independently on the merged branch before publication.

Hermes can now execute the deferred platform workflow from [CAMPAIGN_PLATFORMS.md](CAMPAIGN_PLATFORMS.md), starting with a bounded batch:

```sh
python3 scripts/research_campaign_platforms.py plan
python3 scripts/research_campaign_platforms.py status
python3 scripts/research_campaign_platforms.py crawl --max-sites 20 --max-pages 12 --max-depth 2 --max-requests 100 --delay 2
python3 scripts/research_campaign_platforms.py packets
```

Assign the packets listed in the current `.research/campaign-platforms/packets/manifest.json` by source, using the exact subagent instructions in the guide. Keep one sequential crawler per work directory. Inspect complete captured pages and preserve qualifications, identities and actual checked scope. Import explicitly reviewed response files with `research_campaign_platforms.py import-reviewed PATH...`; its export remains **held pending publication review**, including unreviewed/unavailable entries. Review the source context and exact before/after changes before adding any platform field through the common review workflow. The initial PR runs no broad crawl, model call or platform subagent pass.

## Latest published update — October 14/15, 2026: finance fixes and Gaza/ceasefire audit

Publication version `2026-10-14.2`, schema 1.18 (PR #5, merged October 15). Fixes cover safe/functional automated Git publication, preserving each outside spender's support and opposition separately, fully dated first receipts totals, finance checks that tolerate refreshed snapshots and the local timezone, and the missing campaign-money disclosure on the address page. Both pages share `src/finance-display.js`. Ballot decisions, endorsement records and finance snapshot amounts/dates are unchanged.

The [audit report](reviews/2026-10-14-gaza-and-finance-review.md) records 198 Serper queries, including Gaza and ceasefire searches for all 72 federal/state candidacies, plus ceasefire searches for all 39 existing local dossiers, and source-retrieval/summary triage of all 245 existing items. Three official Panetta statements are restored; Scott Sakakihara, Alex Lee and Sally Lieber gain evidence. Six entries are quarantined or deduplicated with originals retained. The net remains 245 items under 82 candidacies. Lieber's 2024 guide assessment is explicitly a source-observed historical assessment. Seema Badar's stronger leads remain held for a retrieved identity bridge. The collector added in upstream `cc0af8c` is reconciled to the published evidence and quarantine, with merger guards and offline regression checks. The registered change manifest and separate audit inventory are under `research/reviews/`.

Run `python3 scripts/check_release.py` for the complete 19-check gate. New fixed regressions cover the finance bugs while integration checks read current snapshot values. The review also documents a real endorsement-classification error: a Gun Sense Candidate Distinction is labeled an endorsement; the user requested an example only, so the endorsement layer remains unchanged. Historical handoff sections below retain their dated claims.

## Previous published update — October 14, 2026: final six unresolved contests resolved (queue empty)

Dataset **schema 1.18**, publication version `2026-10-14.1`. The last **six unresolved scheduled contests** are **excluded — confirmed not on the November 3 ballot**; the dataset now has **zero unresolved records** (416 positions: 340 confirmed / 76 excluded). Santa Clara (**CA2026-225–228**: Lion's Gate CSD full + short terms, San Martin County Water District, Silver Creek Valley Country Club GHAD): the ROV Contest/Candidate Proof List (CFMR001 printed 8/7) shows Num Cands 0 / Num Qualified 0 for all four; the Final Qualified List of Local Eligible Candidates (9/28, extraction verified complete at Grand Total 287) contains no row for any of them — not even an "On Ballot: No" removal row; the Unofficial Write-In Candidate List (CFMR028 printed 9/24) shows zero write-ins; ballot/CVIG materials finalized 8/28; ROV district pages now list holdover/appointed incumbents. San Mateo (**CA2026-302** Bayshore ESD short term, **CA2026-308** Colma Fire PD Director): scheduled in the Candidate Guide but absent from all three prints (7/31, 8/4, 9/3) of the exhaustive "All Contests / Qualified Candidates Only" Roster — every other scheduled local office appears — with no later list and Sample Ballot mailing begun 9/25. **CA2026-302 seats corrected 1 → 2** per the Candidate Guide's scheduled-offices table (note N892). This follows the Alameda precedent (explicit county determination sufficed; underlying cancellation resolutions were not required) and Contra Costa's exhaustive-certification-omission pattern; how each seat is filled remains deliberately **not asserted**. Evidence packet, raw Jev adjudication (`exclude_confirmed` at p=0.98/0.79/0.78; `seats_2` at p=0.87) and the idempotent apply script are committed at `research/unresolved_2026-10-14/`; sources **S1091–S1098**, notes **N890–N892** replace retired N167/N218/N222. Fixtures updated: `check_explorer.cjs` asserts the unresolved filter is empty, `check_address_matcher.cjs` asserts excluded Lion's Gate races drop from estimates (East Side Union HSD 146/147 carry the distinct-term assertions), and `check_schema.py`'s provisional negative case now synthesizes its shape. Full release gate passes.

## Previous published update — October 13, 2026: Alameda final-ballot reconciliation

Dataset **schema 1.18**, publication version `2026-10-13.1`. All **19 remaining unresolved Alameda contests** (CA2026-204–216 school/college districts; CA2026-218 AC Transit Ward 7; CA2026-220 DSRSD Division 4; CA2026-221/222 Eden Township Healthcare Areas 1+5; CA2026-223 BART District 6; CA2026-224 Washington Township Health Care District) are **excluded — confirmed not on the November 3 ballot**. Primary evidence: the Registrar of Voters' official Candidate List application (`alamedacountyca.gov/rov_app/candidatelist`, election "General Election - 11/03/2026 (Official)", electionId=260) prints an explicit per-race **Race Status** for all 134 races; each of the 19 is labelled **"Not On Ballot"** with its filers listed beneath — an affirmative county determination, not absence-from-list inference. Corroboration: full-text check of the official November 2026 Voter Information Guide (sha256 `5b1e32e3…`, retrieved October 13) finds no candidate statement for any of these filers while contested sibling seats in the same districts appear. Every race had at most numerus-equal completed filings (mostly sole uncontested incumbents), consistent with Elections Code 10515/9008 no-contest outcomes; the Registrar's application does not print the underlying cancellation/appointment resolution, so how each seat is filled is explicitly **not** asserted (`research/alameda_2026-10-13/apply_alameda_exclusions.py`, committed, re-runnable and idempotent; findings with quotes at `research/alameda_2026-10-13/*.json`; sources **S1089/S1090**, shared note **N889**). Filers are retained under provisional filing. Obsolete single-use "final ballot status was not confirmed" notes were retired from these records; shared notes N152/N153/N155/N158 remain for their other users. Coverage after: **340 confirmed / 443 seats / 6 unresolved / 875 printed entries**; Alameda is now fully resolved (0 unresolved). The remaining queue is Santa Clara's four districts and San Mateo's two races; partial research packets with resume checklists are committed at `research/unresolved_2026-10-13/` — both trend toward no-filings/appointment-in-lieu but need adopted cancellation/appointment resolutions before status changes.

## Previous published update — October 12, 2026 (evening): endorsement dedupe

The campaign-site scan had written duplicate endorsement records: one per logo *asset* rather than per endorser. `research/clean_duplicate_endorsements.py` (committed, re-runnable) removed **180 mechanically provable duplicates** — artifacts whose quote is a bare filename sharing a logo with a named sibling (112), abbreviation aliases like HAPAC→Hindu American PAC or BPOA→BART Police Officers Association (50), and named-vs-named pairs sharing one logo asset where one name contains the other, keeping the richer record (18). Artifacts without any sibling were kept (sole evidence); judgment-required pairs (e.g. IAFF Local 1974 vs Livermore-Pleasanton Firefighters) were deliberately left alone. Coverage: **12,953 records on 387 candidacies**; logo-bearing records now 1,877.

## Previous published update — October 12, 2026 (afternoon): Contra Costa final-ballot reconciliation

Dataset **schema 1.18**, publication version `2026-10-12.5`. The long-missing Contra Costa final on-ballot proof was located and retrieved: the county's **Contest/Candidate Proof List** (CFMR001, printed 8/27/2026, header "Contests On Ballot", exhaustive — Total Contests 58 / Candidates 171) plus the certified **Candidate List** (CFMR011, printed 8/14/2026; 253 qualified candidates). Both PDFs are archived under `research/contra_costa/` and cited as sources **S1087/S1088**; note that contracostavote.gov serves these files at bare `/wp-content/uploads/` URLs that its own pages no longer link — the Wayback CDX index was how they were found.

`research/contra_costa/apply_final_proof.py` (committed, re-runnable; asserts both parses equal the PDFs' stated totals before writing) reconciled every local Contra Costa record: contests present in the proof are **confirmed** with its roster (4 solo-candidate offices stayed printed); contests absent from that exhaustive list are **excluded — confirmed not on the ballot**, their unopposed filers elected at certification, names retained under provisional filing with dated notes (51 records, including Canyon Elementary SD and Rodeo Sanitary District which appear in neither file). **CA2026-381 EBRPD Ward 7 is resolved**: complete roster Colin J. Coffey (incumbent, appointed in lieu) + Inderprit "Indy Rishi Singh" Sekhon; Mushda Faiez remains recorded as filed-but-not-certified. A reverse audit confirmed all 53 previously-confirmed Contra Costa local contests appear in the county proof — no contradictions. Coverage after: **340 confirmed / 443 seats / 25 unresolved / 875 printed entries / 0 confirmed contests missing rosters**; Contra Costa is now fully resolved (0 unresolved). The same certified-list pattern is the recommended template for Alameda's remaining queue. `check_explorer.cjs` Ward 7 assertions and `check_address_matcher.cjs`'s county-fallback expectation were updated to the new states (excluded contests are hidden from voter results by design).

## Previous published update — October 12, 2026: federal independent-expenditure layer

Dataset **schema 1.18**, publication version `2026-10-12.2`. Every printed federal candidate now carries `independent_expenditures`: FEC Schedule E itemized outside spending for the 2026 two-year period, with **for/against totals and one row per spender** (name + committee type resolve through the new shared `ie_spenders` registry; shared settings in `ie_finance`, source S1086). Collection is fully deterministic — `scripts/fec_independent_expenditures.py` plan/run/export/attach against the FEC API, cached in `.research/ie/fec_ie.sqlite3` (never committed), resumable via `--refresh-days`. **The scope follows the dataset**: every printed candidate entry with a `fec.id` is eligible, so county expansion automatically extends this layer once federal candidates exist there; `--county/--scope` only narrow a refresh. No LLM or Jev call is involved — primary-source API data needs no model triage.

Aggregation rules (recorded in `ie_finance.method` and enforced by `check_data.py`): current-cycle election types only (late G2024 disbursements filed this cycle are excluded, not zeroed); most-recent amendment rows; memo subtotals never added twice; S→for, O→against. The Schedule E endpoint ignores `page` — pagination uses the API's own `last_indexes` keyset cursor (documented in the script). October 12 snapshot: all 22 federal candidates cached, **13 with current-cycle activity** ($12,514,624 for / $2,587,950 against; largest single flows: Equality PAC $2.13M for Wiener, UDP $1.64M against Wahab). Both readers show an "Independent outside spending" card on federal candidates with a per-spender breakdown and the snapshot caveat; zero-activity candidates display an explicit no-report line. The receipts and independent-spending cards sit together inside one collapsed **Campaign money** disclosure per candidate, so rosters stay compact until a reader opens it (`2026-10-12.2`). Spender names link to their FEC committee pages (registry `source_url`, required by schema; FEC data-search fallback when no committee ID exists) and each card links to the FEC IE browse page for that candidate (`browse_url`). A scheduled run of **`scripts/refresh_fec_money.py`** now refreshes both money layers weekly through November 3: receipts update only on a matching coverage start (Wiener's multi-cycle exception is preserved, never relabelled), then rebuild + full gate must pass before any push. `check_data.py` verifies spender registry resolution, direction rows and total arithmetic; `check_schema.py` adds two negatives plus two positives; `check_explorer.cjs` asserts Wiener's totals, the committee-page link, the candidate browse link, that the campaign-money disclosure starts collapsed, and the zero-activity line on Jeff Frese.

## Previous published update — October 11–12, 2026: campaign-site endorsement scan

Dataset **schema 1.17**, publication version `2026-10-11.4`. Every printed candidacy with a known campaign site was crawled (381 sites; the October 12 pass recovered all 15 previously bot-walled/TLS/JS-only failures via browser-UA retry, Internet Archive captures and a headless-Chromium render step — `scripts/render_failed_sites.py`), scanned by LM Studio `qwen/qwen3.8-27b` for endorsement sections, mechanically quote-gated against cached snapshots, and triaged entry-by-entry by the TypeSafe Jev decision model. A follow-up pass recovers **logo-only endorsements whose name is readable in the campaign-published image filename** (no vision model — mechanical slug filter + Jev). Oversized sites that overflowed model context now split into text+image passes with malformed-JSON salvage, recovering 20 silently-dropped sites including Connie Chan's CD-11 wall and Ben Allen's 414-endorser page. A page-context rule additionally recovers entries Jev classified as endorsements at lower confidence when both the endorser name and its quote appear verbatim on the campaign's own endorsements/support page (+5,759). Total from the scan: **12,743 campaign claims**, bringing coverage to **13,133 records under 387 of 869 printed candidacies**. All new records carry `verification: campaign_claim`, an explanatory per-site note and (where published as a mark) display-only `logo_url`; ~5,500 lower-confidence proposals stay in the local ledger for human review. No vision model was used anywhere; logo-only endorsements without any readable name remain review leads, never guesses. See [the scan review](reviews/2026-10-11-campaign-site-scan.md) for pipeline commands, calibration findings (Jev entries must ride in each question's instructions) and limits. Schema 1.17 also adds `election.publication_version`, shown in both page footers as the dated release marker.

## Previous proposed update — October 10, 2026: priority PAC review

This review branch adds historical Hindu American PAC endorsements for Murali Srinivasan (source biography identifies 2022 Sunnyvale District 3) and Yang Shao (source office is Fremont City Council, with the same verified campaign URL). It also adds AIPAC-reported United Democracy Project support for Kevin Mullin in 2022. There are **389 recommendation records under 199 candidacies**, including three explicitly historical records. Gaza evidence remains 245 items under 82 candidacies. Ballot/finance dates and official rosters are unchanged.

The owner's policy accepts older endorsements without renewal research. Schema **1.16** preserves them with `historical: true`, verification and explanatory notes; both readers display the context. The immutable [review](../research/reviews/priority-pac-endorsements-2026-10-10.json) records all 25 Hindu American PAC cards and AIPAC retrieval limits. Apply through `reviewed_updates.py`, rebuild, and run `check_release.py`. See [the review report](reviews/2026-10-10-priority-pac-review.md) for Hermes review and local preview instructions.

AIPAC PAC's accessible portal text still provides no individual endorsements. Its official report's UDP assistance is explicitly classified as historical reported support, not a PAC endorsement. All 22 printed congressional candidates remain unknown for AIPAC PAC. SEIU 1021/Santa Clara Democrats and other inherited pages were outside this pass. This work is proposed in a PR; a local preview is not a GitHub Pages deployment.

## Earlier update — October 9, 2026: reusable county workflow

The research tooling now accepts single/multiple counties, Bay Area and California presets. A shared 58-county registry supplies names/FIPS to the planner and address decoder; actual ballot scope still comes from the dataset. `research_scope.py` reports missing inventories and unresolved rosters. County-scoped collector ledgers cache/resume without silently switching scopes; a statewide ledger can explicitly report partial coverage and grow as official rosters are added.

`reviewed_updates.py` drafts held observations from any normalized publisher capture (or the existing CAIR parser), previews exact before/after changes, and registers applied reviews in an immutable ordered history. The publication guards honor explicitly reviewed supersessions while preserving the dated baseline and quarantine. `check_release.py` provides one offline release command. See [REPEATABLE_RESEARCH.md](REPEATABLE_RESEARCH.md) for the runnable workflow, source adapter contract and limits.

No election facts or coverage were added in this tooling pass: the dataset remains schema 1.15 with 386 recommendation records and 245 Gaza evidence items. No statewide collection or scheduled job was launched. Roster expansion remains official-source research; source parsing and political fact review are not replaced by automatic matching.

## Earlier update — October 9, 2026: Vote for Peace and AROC Action

Schema **1.15** publishes **386 recommendation records on 197 candidacies** and **245 Gaza evidence items under 82 candidacies**. This pass adds 27 Vote for Peace Ally classifications, 8 oppositions, 29 AROC endorsements, 6 explicit endorsements discovered through linked sources, and 14 attributed guide observations. See [the review](reviews/2026-10-09-peace-guides.md) and [complete source-card manifest](../research/endorsements/peace-guides-2026-10-09.json).

All 152 Vote for Peace cards and 44 AROC cards have dispositions. Five matched Neutral entries produce no recommendation. Panetta remains primary. Five AROC candidate endorsements outside the current roster and ten measures remain in the manifest, without creating ballot contests. CAIR's official labels remain intact; Peter Ortiz is Preferred in both sources. Track AIPAC's three existing endorsements were reverified, not duplicated; a generic badge or funding claim cannot establish its opposition.

Guide assessments use `date_method: source_observed`, the actual inspection date, and a required date note. Both readers label the unknown original date. They are attributed secondary claims, not independently checked funding totals, roll calls or historical statement dates. The importer and publication guard preserve reviewed records and reject unintended changes. Run `check_peace_guides.py` with the full release suite. Candidate rosters, parties, FEC, election-wide dates and prior Gaza evidence are unchanged. Historical sections below retain their original counts.

## Proposed update — October 23, 2026: current CAIR Action general-election guide

The [new reusable adapter](CAIR_ACTION.md) reads the official 34-page California PDF (the landing page embeds the same source), captures all 242 candidate cards, and routes source/office matches through Jev and registered updates. Adds 14 records including Kevin Park Preferred; refreshes 93, including Endorsed → Preferred for Scott Sakakihara and Mer Curry Nuñez. CAIR now has 109 records: 81 endorsed, 27 preferred, 1 opposed. Twenty identity holds and 115 names without plausible roster leads remain explicit; no absent recommendation is deleted. Publication version 2026-10-23.2, schema unchanged; readers rebuilt. See [audit](reviews/2026-10-23-cair-action-refresh.md). Playground PR #14 separately adds CAIR to its compact input registry.

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
| FEC research snapshot | Checked October 24, 2026 (daily refresh through November 3); individual financial coverage dates differ |
| Schema | Inventory version 1.11, Draft 2020-12 (`x_url`, `secondary_x_url`, `campaign_url`, `gaza_evidence`; evidence `date` is required and calendar-valid, with optional `date_method`/`date_note`) |
| Endorsements (new) | **741 of 869 printed candidacies** carry cited current-cycle `endorsements` records (884 total; schema 1.12 `$defs.endorsementRecord`) from verified endorser pages, collected October 9 via `scripts/research_endorsements.py`; snapshot at `research/endorsements/endorsements-export-2026-10-09.json`. Ongoing: bot-walled platforms and ~128 candidacies still uncovered |
| X accounts / sites | 135 printed entries (135 distinct names) with X URLs; 27 are explicitly probable matches. 10 secondary X URLs; 383 candidate-specific campaign/official URLs retained after five generic homepage claims were removed. |
| Gaza stance research | This review branch retains 231 items for 81 candidates after 44 manual rewrites and 69 documented quarantines (the 69th, Chan GE-0019, failed the deterministic relevance gate on post-merge reconciliation). All 300 input summaries have dispositions. Jev assessment is pending; see the post-enrichment review. |
| Inventory | 416 researched contests; 340 confirmed, 0 unresolved, 76 records excluded (confirmed not on ballot): 51 Contra Costa + 21 Alameda + 4 Santa Clara + 2 San Mateo |
| Confirmed seats | 443 |
| Printed candidate entries | 875; these are entries, not necessarily unique people |
| Confirmed races with missing roster | 0 (Ward 7 resolved October 12 against the county proof list) |
| OCD electorate IDs | 188, all currently convention-based; not live API validated |
| Federal finance | 22 printed candidates with FEC IDs; 20 totals, 2 unknown amounts |
| Live address checks | Census and Photon requests were blocked in the original execution environment; fixture checks passed |

The site already includes a downloadable JSON/schema, hierarchical explorer, candidate and FEC details, address-to-ballot estimates, inclusive warnings for unresolved districts and accessible autocomplete. Do not recreate these features before inspecting the existing implementation.

## Suggested next work

These are priorities for the next maintainer, not permission gates or claims that the work has already been done.

1. ~~**Resolve final ballot inclusion and missing rosters.**~~ **Complete October 14, 2026:** Contra Costa (Oct 12), Alameda (Oct 13) and the final six Santa Clara/San Mateo contests (Oct 14) are all resolved; `unresolved_scheduled_contests` is 0. Remaining related work is item 4's OCD-ID validation, not ballot status.
2. **Verify address services in a real browser.** Test autocomplete and Census lookups using public civic-building addresses across all five counties. Check actual responses, CORS/JSONP behavior, map vintage, mobile/keyboard interaction and failure fallback. Keep `api_validated: false` until evidence justifies a clearly scoped change; a single successful request does not validate every OCD ID or every race.
3. **Refresh time-sensitive evidence.** Check official final candidate/retention materials, FEC filings and unresolved incumbent/link assertions. Preserve printed names when campaign withdrawal does not remove them from the ballot. Revisit the two missing FEC totals and the Scott Wiener coverage-period exception. Both federal money layers now refresh through a scheduled run of `scripts/refresh_fec_money.py` (receipts via committee cycle totals with a coverage-start guard, IE layer refetched and re-attached, full gate before push) — keep that job running until November 3 and pause it after. **Write-ins are deprioritized by user decision (October 12, 2026): they rarely appear on the printed ballot and do not affect reader decisions; existing write-in records stay as-is with their evidence, but no future sweep or refresh work targets them.**
4. **Audit local geographic coverage.** Validate convention-based OCD IDs, investigate official GIS/precinct-to-ballot sources for council, supervisor, school, college and special districts, and compare with official county ballots. Only narrow alternatives when the evidence is reliable; missing API fields must not suppress plausible races.
5. **Expand coverage to the remaining four counties.** Marin, Napa, Solano and Sonoma are the longer-term goal. Follow the code/data expansion checklist in [MAINTENANCE.md](MAINTENANCE.md); shared districts, countywide flags, FIPS mappings and hardcoded five-county text all need attention.
6. **Gaza evidence and campaign platforms.** Two bounded website/packet rounds are now published (Oct 16 pass 1, Oct 17 round 2 — see the latest update section; docs/CAMPAIGN_PLATFORMS.md is the workflow reference). Known follow-up queue for a round 3: **(a)** ~90 JS-only/bot-walled sites need headless-render exception captures (`scripts/render_failed_sites.py`; playwright launch args and media-block retry per CAMPAIGN_PLATFORMS.md) before their packets can flip from `unavailable` to reviewed — this includes the JS-shell sites whose captured text is nav boilerplate only (e.g. votekanani.com); **(b)** sources with failed captures that bar silence findings need browser/Wayback re-capture of exactly the URLs named in each held scope_note, then packet regen + re-review; **(c)** Cheris Crocker-Root's scoped silence is barred by the HTTPS provenance guard (HTTP-only capture) — a maintainer must verify a suitable secure source capture; **(d)** Tom Ramsey's wrong-person `campaign_url` inventory correction remains open. Reviewer passes that worked at scale: direct `qwen/qwen3.8-27b` chat/completions review with gate-mirror validation for normal packets, and deterministic keyword-scan + Jev System One classification (`.research/round2_jev.py` pattern) for oversized sites — prefer the Jev path wherever a scripted decision on long text is needed. A failed or limited source must remain unavailable or explicitly scoped; silence is never neutrality. Follow the ledger's acceptance/quarantine rules for any separate prose-evidence collector work.
7. **Improve maintainability where it helps research.** Candidate opportunities include a reproducible coverage-summary updater, per-record provenance dates, a standard JSON Schema validation gate, a schema for the estimate export, browser smoke checks and CI. These are not implemented promises. Add them in small reviewable changes and avoid making fixture success stand in for factual accuracy.

## Known research exceptions to preserve

- The Contra Costa August 27 final on-ballot proof PDF was retrieved October 12, 2026 (with the certified August 14 candidate list) and archived in `research/contra_costa/`, cited as S1087/S1088. All local Contra Costa ballot-inclusion questions are closed against it; unopposed filers elected at certification sit on excluded records with their names retained under provisional filing. Do not re-open these contests without new county evidence.
- EBRPD Ward 7 (CA2026-381) roster conflict is resolved by the same proof: two qualified candidates (Coffey incumbent, Sekhon); Mushda Faiez stays recorded as filed-but-not-certified and must not be promoted to the printed roster.
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
- **Gaza evidence dates are now mandatory** (schema 1.9 → 1.10): `date` required in `$defs.stanceEvidence`; two new schema negative cases; merge refuses dateless items; pipeline resolves dates deterministically and quarantines undated findings (`research/gaza-stance/`: `date_resolvers.py`, `backfill_dates.py`, `date_first_capture.py`, `date_content_first_seen.py`, `tests/test_date_resolvers.py`). All 22 previously undated SF items resolved or removed: ledger is **97 items / 26 people, zero undated**; removals and dating methods are recorded in `ledger/date_backfill_report.json`.
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
- **New acceptance layer** `research/gaza-stance/validate_evidence.py`: hard rules quarantine at add time; soft rules write to `ledger/review_flags.json` for human review without dropping the item. `revalidate_ledger.py` applies the same rules over existing output (idempotent). Regression cases in `tests/test_validate_evidence.py` encode every confirmed failure class plus known-valid examples — passing repository tests alone was explicitly insufficient because they accepted these errors.
- **Extraction prompt strengthened:** identity-first rule requiring a source link between the person and this candidate's office/jurisdiction/biography; explicit rejection of attendance, vandalism, ads-about-them, absence claims and roster-inferred co-signatures. `--enrich` is now resumable per person (`stages.enriched`).
- **Net effect:** dataset Gaza evidence coverage 125 → **114 people / 301 printed items** (ledger 316); quarantine registry 93 entries, each with a written reason. Full check suite green; enrichment resumes under the new rules.

## Working agreement

Read the agent handoff section of [README.md](../README.md) and the guides it links, then maintain evidence and implementation together. Keep stable IDs, compact shared metadata, official party labels, `incumbent` only when true, and the user's Senate → Assembly → other-state-offices display preference. Both generated HTML files must reflect any data or source-code change.

For each research batch, record the contest IDs checked, evidence/document dates, resulting status changes and unresolved questions. Refresh this handoff after material progress so a future agent can distinguish completed work from the original backlog. Do not merely move a date forward to make stale research appear fresh.


## Post-enrichment manual review — October 8, 2026 (America/Los_Angeles)

After upstream `d0ee70b`, all 300 evidence summaries were screened manually. This branch rewrites 44, quarantines 69 with original records/reasons (68 from the review plus one relevance-gate removal during external-ledger reconciliation), and retains 231 items under 81 candidates. It also repairs filtered-download coverage, displays archive-date bounds, closes the year-zero validator gap, and removes three remaining generic campaign homepage links. Core contests, candidates, and structured FEC records remain unchanged. See [the detailed review](reviews/2026-10-08-post-enrichment-review.md) and its per-item log for scope and unresolved issues.

The requested Jev pass is not complete. Serper was blocked by the execution environment and Jev's endpoint/protocol was unavailable. The packet-preparation script does not call an API. Future work must obtain source text for held title-only entries, establish ambiguous identities, reconcile the external ledger with the repository quarantine, and complete the documented model assessment. Earlier counts and “verified” wording in historical session entries below/above are snapshots, not current certification.
