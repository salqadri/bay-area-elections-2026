# Jev Gaza grading batches

`scripts/grade_gaza.py` grades candidacies on the Israel/Gaza dimension with **Jev System One**
(`jev-latest`; score questions need the current flagship). It is a research batch tool: results
are **held pending publication review**, never written into the dataset directly.

## Reusable shape

- `--criteria research/gaza-grading/criteria-<id>.json` — versioned rubric file. Each run records
  its criteria id; grading refuses a plan built against a different rubric. The owner's v1 rubric
  (`gaza-grade-v1`, provided 2026-10-22) always yields `pro_palestine_score` (score question,
  level 0 = shields Israel → level 5 = openly against the genocide/military assistance) and
  `gaza_grade` (choice A–F). Future rubrics keep those two output names.
- `--scope` — race/region selector (`house-nationwide`, `senate-nationwide`, `governor-nationwide`;
  extend the `SCOPES` map for new offices or regions).

## Run

```sh
python3 scripts/grade_gaza.py plan --scope house-nationwide --batch <name>
python3 scripts/grade_gaza.py grade --batch <name> --jev-key-file /secure/typesafe_key --workers 4
python3 scripts/grade_gaza.py report --batch <name>
```

Working files (plan, per-request decision cache, results) live under gitignored
`.research/gaza-grading/<batch>/`. Decisions are cached against the exact request contract — a
rerun only pays for candidates whose evidence changed. One failed candidate is recorded as an
`error` row and retried on rerun; it never stops the batch.

## What goes into the Jev `state` (kept succinct by design)

Identity line (name, office+district, state code, party), then only substantive evidence:
outside-money spenders **supporting** and **opposing** with amounts (top 12 each), official USCPR
scorecard grades when published, up to eight campaign platform point summaries, any reviewed Gaza
platform statement, up to twelve dated Gaza evidence items, and tracked congressional Gaza actions.
No boilerplate scope/method notes — they burn context without informing the grade.

## Acceptance semantics

`gaza_grade_accepted` marks choice confidence ≥ 0.75 (the repo-wide Jev bar). `has_gaza_evidence`
marks whether direct attributable statements existed: rows without it are inferred only from
outside-money and platform context and must never be presented as documented positions. Silence
is not neutrality — an evidence-free candidate graded D/E is a weak inference, not a finding.

## Batches

- `house-2026-10-22` (criteria `gaza-grade-v1`, run 2026-10-23): all **165** printed nationwide
  House candidates — A 16 · B 2 · C 1 · D 48 · E 1 · F 97; 83 grades accepted at ≥0.75; zero call
  errors. Portable archive (answers omitted, decision cache stays local):
  `research/gaza-grading/house-2026-10-22/results.json`. **Not published** — publication needs the
  normal reviewed-updates workflow plus an owner decision on how grades display.
