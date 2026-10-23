# Jev grading and the local playground

[Start and use the local playground](../../docs/JEV_PLAYGROUND.md) to edit question
JSON, run Jev on tracked House candidates nationwide plus every active Alameda/
Santa Clara county ballot contest, and inspect exact inputs and confidences.
The playground now includes **685 candidacies / 268 races**; its immutable
default archive remains the original **187 House candidacies / 72 races**.
Added local/state/judicial candidates start unevaluated. The playground uses
`candidate-evidence-v4-local-federal` with office/jurisdiction/county context and
separate CAL-ACCESS spenders. CLI scope flags and historical request states are
unchanged; the original `house-nationwide` scope omitted the Bay Area races.

## Confidence-only results

The owner explicitly removed acceptance criteria on October 23. New CLI and
playground runs retain **every valid answer and its confidence**, with no 75%
cutoff, acceptance flag or hidden low-confidence rows. Choice probabilities and
confidence remain separate returned values. A yes/no `noul` answer returns the
probability of true, not a separate confidence.

The owner's exact updated questions are versioned in
`criteria-pro-palestine-v2.json`. Both default output names are retained, but
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
Full endorsement lists are not passed: current focus reduces 3,690 observations
to 41, with at most three for any candidate.

## Archives

- **Current playground default:** `house-all-focused-2026-10-23/results.json` —
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

No grader/playground command edits the election dataset or publishes grades.
