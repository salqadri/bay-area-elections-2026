# Jev grading and the local playground

[Start and use the local playground](../../docs/JEV_PLAYGROUND.md) to edit question
JSON, run Jev on tracked House candidates nationwide plus every active contest
serving Alameda, Contra Costa, San Francisco, San Mateo and Santa Clara counties,
and inspect exact inputs and confidences. The catalog includes **1,042
candidacies / 401 races**; **Run Bay Area** targets **877 / 340**. It opens
**Latest per candidate** across saved local history. Its immutable baseline
remains **187 House candidacies / 72 races**; candidates without saved evaluations
remain input previews.

The playground uses `candidate-evidence-v7-local-federal-community` with
office/jurisdiction/county context, separate CAL-ACCESS spenders and optional
owner-confirmed community values. CLI scope flags and historical request states
are unchanged; the original `house-nationwide` scope omitted the Bay Area races.

## Confidence-only results

The owner explicitly removed acceptance criteria on October 23. New CLI and
playground runs retain **every valid answer and its confidence**, with no 75%
cutoff, acceptance flag or hidden low-confidence rows. Choice probabilities and
confidence remain separate returned values. A yes/no `noul` answer returns the
probability of true, not a separate confidence.

The separate derived `pro_palestine_score_grade` uses tunable 0–5 score bands.
When the saved two-criterion `evidence_score` is below 0.10 / 1, it shows
**Insufficient Info** instead of a letter. This does not change Jev's original
answers, model confidence or archived requests. See the playground workflow for
boundary and historical-prompt behavior.

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

No grader/playground command edits the election dataset or publishes grades.
