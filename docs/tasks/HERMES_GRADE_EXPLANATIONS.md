# Hermes follow-up: concise explanations of all published grades

## Current Khanna paragraph

The owner approved the strict 45–80-word Sol Low comparison draft for Khanna.
Publication **2026-10-27.10** publishes its 78-word final paragraph, with one
recorded clarification of U.S. aid to Israel. The shared current context and
summary rules are saved in `ro-khanna-summary-input-2026-10-27-concise.json`;
raw output, final text and the edit are saved in the matching output file.
The current explanation archive is `explanations-2026-10-27-v6-concise-khanna.json`.
Other summaries and all scores are unchanged. Continue using the existing Qwen
runtime for Hermes; this one-off Sol draft does not change model defaults.


## Historical-timeline correction

Only Khanna's paragraph was refreshed using the owner's explicit Sol Low request.
Hermes's Qwen defaults are unchanged. Its new archive contains separate generation
input/output hashes rather than pretending November evidence was in the old scoring
request. Preserve the other 1,295 summaries. Apply this additional rule to future
Qwen summaries: an earliest collected report does not establish first/earliest
support; distinguish statement, broadcast, report and repost dates. Use “by [date]”
when the source establishes support by then, without proving the onset.
[Current correction and exact inputs](../HISTORICAL_GAZA_EVIDENCE.md).


## Current task — summaries for v6 evaluations

Prepared publication **2026-10-27.7** replaces the scoring snapshot with the
owner's full-roster run `20261027T224704Z-cc6d4be3`: exact **v6** questions,
all 1,296 current v15 states, grade bounds **0.7 / 1.4 / 2.3 / 3.3 / 4.4**,
minimum evidence **0.20**, no confidence filter. Use:

- `research/gaza-grading/explanation-queue-2026-10-27-v6.json`
- `research/gaza-grading/published-2026-10-27-v6.json`
- `research/gaza-grading/criteria-pro-palestine-v6.json`

Keep the owner's latest Qwen summarizer prompt and runtime. Each replacement
summary must bind the new `candidate_id`, `request_sha256` and publication ID
**jev-2026-10-27-v6**. Do not attach prior paragraphs by name or replace their
request hashes: the scoring questions and results changed. The previous prompt3
summary archive remains immutable. Its paragraphs are no longer shown beside
the new scores. New N/A notes can use the existing editorial template; no
political stance should be inferred from insufficient evidence.

The batch contains **408 letter-grade paragraphs** for Qwen and **888 N/A
editorial notes**. The existing attachment tool creates the latter without model
calls when response files are absent. Keep final paragraphs/source audits bound
to the new queue, and publish to a new immutable explanations archive.

The earlier five-candidate rerun recommendation is complete because the owner
ran the full roster. The sections below describe historical v5 work and useful
full-evidence/source-binding requirements; use the v6 queue above for new work.


Requested by the owner on October 26, 2026. Prepare one brief evidence summary
for each of the **1,296 active candidacies** in the current public score snapshot.
Use Jev for source/scoring decisions. Hermes uses `qwen/qwen3.8-27b` for
narrative summaries; retain the existing runtime settings.

## October 27 follow-up policy

Keep the latest owner-approved final summarizer prompt and Qwen runtime from
publication 2026-10-27.5. PR #19 does not replace that prompt or require regenerating
the full summary batch. [Targeted rerun review](../JEV_RERUN_REVIEW.md) identifies
the five-candidate small batch; generate newly bound explanations after scoring
those candidates and preserve the rest.

The supplementary `research/gaza-grading/summary-prompt-v2.txt`, with the hash and coverage
requirements in `summary-policy-v2.json`, specifies an assessment for every supplied
evidence ID before the paragraph; no two-or-three-fact cap. Source chronology,
corrective actions and the owner-defined pro-Palestine community meaning must be
considered. [Evidence context](../EVIDENCE_CONTEXT.md) documents the source-reviewed
Wiener/Khanna/Liccardo fixes. Full coverage still needs semantic review.

These fixes change new v15 inputs. Do not silently replace frozen v5 request
states or say the old score considered the new material. Candidate scores and
existing published explanations have not been regenerated for this update.

## Portable inputs

**October 27 context update:** new states use the source-backed v14
[organization context](../ORGANIZATION_CONTEXT.md). No scorecards were rerun.
Do not replace frozen inputs with these new states when explaining old grades.
Organization funding links carry the owner's negative-signal criterion, while
actual spender support/opposition and source qualifications remain explicit.

- `research/gaza-grading/explanation-queue-2026-10-27-vfp.json`: exact candidacy IDs,
  contest/name/roster identity and request hashes for every summary.
- `research/gaza-grading/published-2026-10-27-vfp.json`: frozen full Jev requests,
  actual input states, question JSON and provider answers, including evidence
  scores and confidence. No private local run directory is needed.
- `research/gaza-grading/criteria-pro-palestine-v5.json`: the owner's exact preferred
  question JSON, used unchanged on all 1,296 evaluations.
- `2026-11-03_Bay_Area_Elections.json`: published numeric scores, derived letters,
  provenance, mapping and archive hash. [Methodology](../PUBLISHED_GRADES.md).

## Required behavior

Resolve each queued item by candidacy ID and verify its request SHA-256 before
calling the model. Pass the exact archived state, questions and recorded answers,
plus the deterministic grade/mapping and 0.20 evidence threshold. Do not substitute
new research or the current candidate state for what was actually evaluated.
Generate a short, factual explanation grounded in observations present in that
input. This is an evidence summary supporting the saved score, not a transcript
of the scoring model's internal reasoning. Keep missing evidence explicit.

For **N/A**, explain that the saved evidence score is below 0.20 / 1; do not
assign a political stance from a lack of evidence. Distinguish direct statements,
legislative actions, outside spending, endorsement observations and owner-confirmed
community input when relevant. Attribute each observation accurately. Do not
invent sources, facts or a justification merely to fit the saved number.

Return structured results with `candidate_id`, `request_sha256`,
`publication_id`, a short `summary`, and the input fields supporting it. Prefer
one or two sentences (about 40–70 words). Record the actual model/version,
questions, inputs and responses; cache by their request hash. A failed call stays
an explicit retry item. Summaries must never silently regrade a candidate or
replace the immutable raw scoring answers.

Review completeness, source attribution, N/A handling and a representative sample
before adding summaries to the readers through the normal publication workflow.

## Status — completed October 28, 2026 (publication 2026-10-27.8)

All summaries for **jev-2026-10-27-v6** are generated, validated and published
as publication **2026-10-27.8** in
`research/gaza-grading/explanations-2026-10-27-v6-prompt3.json` (1,296
entries). The **408 letter grades** carry voter-voice paragraphs regenerated
under the owner's final prompt — openly pro-Palestine, pro-justice,
anti-genocide standpoint, comprehensive current-stance capture,
candidate-specific openings, strict factual-accuracy and relevance rules —
from each candidate's exact frozen v6 input state, rubric and recorded result
(LM Studio `qwen/qwen3.8-27b`, temperature 1.0, thinking enabled, with a new
grade-letter leak guard in the harness; 0 generation errors). The **888 N/A
candidacies** get a uniform hand-written editorial note (no LLM): the record is
too thin to judge and no stance is inferred from silence. The 2026-10-27.5 v5
batch is superseded (its 405 paragraphs no longer bind to the v6 request
hashes) and remains archived immutable.

## Status — completed October 27, 2026 (publication 2026-10-27.5)

All summaries for **jev-2026-10-27-vfp** are generated, validated and published
as publication **2026-10-27.5** in
`research/gaza-grading/explanations-2026-10-27-vfp-prompt3.json` (1,296
entries), superseding the interim 2026-10-27.3 batch (retained immutable).
The **405 letter grades** carry voter-voice paragraphs under the owner's final
prompt — openly pro-Palestine, pro-justice, anti-genocide standpoint,
comprehensive current-stance capture, candidate-specific openings, strict
factual-accuracy and relevance rules — generated by LM Studio
`qwen/qwen3.8-27b` (temperature 1.0, thinking enabled) from each candidate's
exact frozen v5 input state, rubric and recorded result, with no scores, bands
or methodology in the prose. The **891 N/A candidacies** get a
uniform hand-written editorial note (no LLM): the record is too thin to judge
and no stance is inferred from silence. Prior batches remain archived in
`explanations-2026-10-26.json` and `explanations-2026-10-27.json`.

Attached through:

```sh
python3 scripts/attach_grade_explanations.py \
  --responses .research/grade-explanations/responses-v5 \
  --queue research/gaza-grading/explanation-queue-2026-10-27-vfp.json \
  --output-archive research/gaza-grading/explanations-2026-10-27-vfp-prompt3.json \
  --publication-version 2026-10-27.5 --schema-version 1.27
```

Docs updated, both readers rebuilt, and the full release gate passes.
