# Hermes follow-up: concise explanations of all published grades

Requested by the owner on October 26, 2026. Prepare one brief evidence summary
for each of the **1,296 active candidacies** in the current public score snapshot.
Use Jev for model judgments, as required by the owner's research policy.

## Portable inputs

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

## Status — refresh pending after October 27 grade publication

The prior 1,296 summaries were completed for the October 26/v3 score archive.
They are retained in `explanations-2026-10-26.json` but removed from current public
cards because the owner reran all candidates with v5, refreshed Vote for Peace observations and changed the score bands and
evidence minimum. Generate fresh summaries for **jev-2026-10-27-vfp** from the new queue above.
Use the archive’s own mapping, evidence threshold and exact recorded states;
do not substitute current research or the old equal-width C/B boundary.

Attach through:

```sh
python3 scripts/attach_grade_explanations.py --responses <new-responses-dir> \
  --queue research/gaza-grading/explanation-queue-2026-10-27-vfp.json \
  --output-archive research/gaza-grading/explanations-2026-10-27-vfp.json \
  --publication-version 2026-10-27.3 --schema-version 1.27
```

Then update relevant docs, rebuild both readers, and run the full release gate.
