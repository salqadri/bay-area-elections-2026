# Jev grading and the local playground

[Start and use the local playground](../../docs/JEV_PLAYGROUND.md) to edit question
JSON, inspect exact states and evaluate every active tracked candidate. The full
catalog has **1,296 candidacies / 471 races**; **Run Bay Area** targets **877 / 340**.
It opens **Latest per candidate** across local history. House-only CLI scopes and
all historical requests remain intact. New CLI/default questions are v3; old
plans need their matching criteria file when explicitly replayed.

The playground uses `candidate-evidence-v7-local-federal-community` with
jurisdiction/county context, both independent-spending directions, focused
endorsement observations and owner-confirmed community values.

## Confidence-only results

The owner explicitly removed acceptance criteria on October 23. New CLI and
playground runs retain **every valid answer and its confidence**, with no 75%
cutoff, acceptance flag or hidden low-confidence rows. Choice probabilities and
confidence remain separate returned values. A yes/no `noul` answer returns the
probability of true, not a separate confidence.

The separate derived `pro_palestine_score_grade` uses tunable 0–5 score bands.
When the saved two-criterion `evidence_score` is below 0.10 / 1, it shows
**N/A** instead of a letter. This does not change Jev's original
answers, model confidence or archived requests. See the playground workflow for
boundary and historical-prompt behavior.

The owner's exact updated questions are versioned in
`criteria-pro-palestine-v3.json`. Both default output names are retained, but
custom questions can be added or renamed. The score and letter are separate
rubrics; neither is mechanically derived from the other. Decisions are made by
Jev `jev-latest`; the current default run returned `jev-1.14.0`.

## Reusable CLI

```sh
python3 scripts/grade_gaza.py plan --scope house-all --batch <fresh-name>
python3 scripts/grade_gaza.py grade --scope house-all --batch <fresh-name> --jev-key-file /secure/key --workers 3 --force
python3 scripts/grade_gaza.py report --batch <fresh-name>
```

Global `--criteria PATH` supports other question files. `house-all` selects all
active tracked House races, including California county-scoped contests.
`house-nationwide`, `senate-nationwide` and `governor-nationwide` retain their named
scopes. Working plans/caches stay under ignored `.research/gaza-grading/`.
CLI cache reuse is exact-request based; `--force` reruns every candidate. A flaky
candidate call becomes an explicit error without discarding other answers.

The shared state builder includes identity, both IE directions, recorded scorecard
and platform/Gaza evidence, focused endorsement observations, and congressional
actions with actual response values resolved against the action registry. See the
workflow for limits and the versioned, source-backed endorsement focus registry.
Full endorsement lists are not passed. Focused observations preserve the exact
reviewed recommendation levels and source provenance; the registry and current
candidate records determine each newly generated state.

## Archives

- **Immutable playground baseline:** `house-all-focused-2026-10-23/results.json` —
  all 187 candidates, zero call errors, updated owner JSON, focused endorsements,
  exact requests/responses and dataset hash. A 22 · B 4 · C 2 · D 47 · E 2 · F 110.
  These are experimental model outputs; none is published into candidate records.
- **Historical held batch:** `house-2026-10-22/results.json` — 165 nationwide
  House candidates, original v1 rubric, run October 23. A 16 · B 2 · C 1 · D 48 ·
  E 1 · F 97. Its 83 historical acceptance flags used selected-letter probability
  ≥0.75, despite the old confidence wording. Those immutable fields are retained
  only as history, never used to filter the new playground. Its
  `has_gaza_evidence` flag meant a dedicated Gaza-ledger input was present; it did
  not reliably identify all attributable topical platform evidence.

Grader/playground runs do not edit the election dataset. The separate
`publish_jev_grades.py` command attaches a frozen, complete uniform-prompt batch;
see [publication workflow](../../docs/PUBLISHED_GRADES.md).

## Current public snapshot

`published-2026-10-26.json` freezes the fresh 1,296-candidate run
`20261026T071836Z-15420e33`, zero errors, with the exact v3 prompt on every request.
A 128 · B 21 · C 16 · D 33 · E 36 · F 176 · N/A 886. Every raw provider response,
input state, confidence, request hash and source-run reference is preserved.
`explanation-queue-2026-10-26.json` binds all 1,296 Hermes follow-up items to these
exact requests. The separate model `gaza_grade` remains archived but is not a
public score badge. Previous House batches remain immutable historical baselines.

## Education-policy evidence (October 26, 2026)

No grading batch was run for this evidence update. All 1,296 published scores,
preferred v3 questions, exact responses and frozen explanations are unchanged.
Current state v8 includes every `antisemitism_education` record in a separate
source-linked channel, outside the generic twelve-item budget. The playground
exposes Current input separately from the exact saved State JSON. See
[the source-review workflow](../../docs/EDUCATION_POLICY_RESEARCH.md).

## Legislative tracker input v9 (October 26, 2026)

The current builder includes the sheet's assessment and explicit alignment for
each action. It keeps legislative-tracker dates from 2023-12-01 onward,
newest first, then period-only entries whose entire range meets that cutoff.
Ambiguous older ranges and unknown dates are omitted. This is an input change;
no grading batch was run, and frozen requests/answers/explanations are unchanged.
See [the source/date contract](../../docs/GAZA_VOTING_RECORDS.md).

## Compact input v10 (October 26, 2026)

The shared/local input builders now omit capture mechanics and duplicate metadata,
retain explicit alignment and substantive qualifiers, and collapse identical
linked legislative observations. No scoring requests or archived evaluation edits
occurred. The canonical dataset and provenance are unchanged. See
[the v10 input contract](../../docs/JEV_PLAYGROUND.md#compact-model-inputs-v10-october-26-2026)
and [the measured state sizes](state-compaction-2026-10-26.json).


New model input v11 uses a reviewed funding-period/donor projection rather than
raw financial prose: calendar 2024 onward, organizations only, no mixed/unknown
period totals or individual/conduit receipts. Historical scores remain exact.
[Funding workflow](../../docs/FUNDING_EVIDENCE.md),
[projection index](../funding/jev-funding-policy-v1.json).
