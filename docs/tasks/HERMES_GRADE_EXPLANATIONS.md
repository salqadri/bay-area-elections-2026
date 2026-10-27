# Hermes follow-up: concise explanations of all published grades

Requested by the owner on October 26, 2026. Prepare one brief evidence summary
for each of the **1,296 active candidacies** in the current public score snapshot.
Use Jev for model judgments, as required by the owner's research policy.

## Portable inputs

- `research/gaza-grading/explanation-queue-2026-10-26.json`: exact candidacy IDs,
  contest/name/roster identity and request hashes for every summary.
- `research/gaza-grading/published-2026-10-26.json`: frozen full Jev requests,
  actual input states, question JSON and provider answers, including evidence
  scores and confidence. No private local run directory is needed.
- `research/gaza-grading/criteria-pro-palestine-v3.json`: the owner's exact preferred
  question JSON, used unchanged on all 1,296 evaluations.
- `2026-11-03_Bay_Area_Elections.json`: published numeric scores, derived letters,
  provenance, mapping and archive hash. [Methodology](../PUBLISHED_GRADES.md).

## Required behavior

Resolve each queued item by candidacy ID and verify its request SHA-256 before
calling the model. Pass the exact archived state, questions and recorded answers,
plus the deterministic grade/mapping and 0.10 evidence threshold. Do not substitute
new research or the current candidate state for what was actually evaluated.
Generate a short, factual explanation grounded in observations present in that
input. This is an evidence summary supporting the saved score, not a transcript
of the scoring model's internal reasoning. Keep missing evidence explicit.

For **N/A**, explain that the saved evidence score is below 0.10 / 1; do not
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

## Status — completed October 27, 2026

All 1,296 summaries were generated with LM Studio `qwen/qwen3.8-27b` (temperature
0.1) from each candidate's exact archived state, the v3 rubric and the recorded
answers, cached per request hash under the ignored `.research/grade-explanations/`
work directory. The frozen archive is
`research/gaza-grading/explanations-2026-10-26.json`; publication ran
`scripts/attach_grade_explanations.py` into schema 1.25 / publication 2026-10-26.2, with `scripts/check_grade_explanations.py` in the release gate and a
collapsed **Why this grade?** panel in both readers.
