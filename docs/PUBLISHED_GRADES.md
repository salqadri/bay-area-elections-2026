# Published pro-Palestine model scores

Publication **2026-10-26.1**, schema **1.24**, shows project-owned Jev model scores
next to candidates on both public readers. A higher score follows the owner's
published pro-Palestine/anti-Israel rubric. These badges are distinct from CAIR
Action recommendations and the USCPR publisher's grades, which retain their own
source labels.

## Exact prompt and completed batch

The owner's exact final question JSON is stored under `questions` in
[criteria-pro-palestine-v3.json](../research/gaza-grading/criteria-pro-palestine-v3.json).
All **1,296 active tracked candidacies / 471 races** were freshly evaluated with
that exact JSON in run `20261026T071836Z-15420e33`, with zero errors, using
`jev-latest` resolving to `jev-1.14.0`. This includes the 254 active candidacies
outside the former House/five-county playground scope. Excluded contests are
outside the evaluation batch. Candidate identity includes contest and roster;
a person running in two contests retains two evaluations.

[The frozen archive](../research/gaza-grading/published-2026-10-26.json) contains
each exact request/state/questions, request SHA-256, full provider response,
confidence, evaluation time and source-run/dataset metadata. All requests use the
same preferred question JSON. No search or inferred explanation was added during
publication. The older mixed-prompt proposal was superseded before publication.

## Badges and colors

A badge such as **E (1.36 / 5)** displays `pro_palestine_score_grade` and the saved
`pro_palestine_score`, rounded to two decimal places only for display. The grade
uses the unrounded score. A is green, B teal, C yellow, D orange, E rose and F red;
the letter is always present. **N/A** is gray.

| Grade | Unrounded score interval |
|---|---|
| F | 0 ≤ score ≤ 5/6 |
| E | 5/6 < score ≤ 10/6 |
| D | 10/6 < score ≤ 2.5 |
| C | 2.5 < score ≤ 20/6 |
| B | 20/6 < score ≤ 25/6 |
| A | 25/6 < score ≤ 5 |

When the saved 0–1 `evidence_score` is **strictly below 0.10**, the derived grade
is **N/A**. Exactly 0.10 still receives a letter. The badge shows only N/A for
insufficient evidence; the raw model score and confidence remain in its tooltip,
accessible label, canonical JSON and archive. A candidate without a saved
evaluation also shows N/A, with a distinct explanation. No confidence cutoff is
applied. The model's separate `gaza_grade` is archived but not displayed as a
public badge.

Hover text and the badge’s accessible label include the model score confidence,
evidence score and Pacific evaluation time. Click it to read this methodology. All 1,296 active
candidacies have a saved evaluation in this publication: **A 128, B 21, C 16,
D 33, E 36, F 176, N/A 886**.

## Reproducible publication

`pro_palestine_score`, `pro_palestine_score_grade` and
`pro_palestine_evaluation` are stored together on each evaluated candidate.
Top-level `pro_palestine_grading` binds the immutable archive hash, mapping,
evidence threshold, preferred criteria and methodology. No public grade is
recomputed from a candidate name or an endorsement at render time.

```sh
python3 scripts/publish_jev_grades.py --snapshot /path/to/api-bootstrap.json --archive research/gaza-grading/NEW-PUBLICATION.json --published-on YYYY-MM-DD
python3 scripts/publish_jev_grades.py --archive research/gaza-grading/NEW-PUBLICATION.json --explanation-queue research/gaza-grading/NEW-EXPLANATION-QUEUE.json
python3 scripts/build_site.py
python3 scripts/check_release.py
```

Capture `/api/bootstrap` only after the final batch completes. The publisher
rejects incomplete rows, mixed prompts, missing active candidates, mismatched
identities/rosters, changed request hashes and unsupported score scales. An
existing archive cannot be overwritten; replaying the same archive is an
idempotent attachment. New publication prompts need their own versioned criteria
file and matching publisher preference. Bump the publication version, rebuild,
verify and publish under the owner's authorization. Local mapping changes and
new playground runs do not automatically change the public snapshot.

Published scores are excluded from future generated input states to avoid
feeding an earlier model result back into the next evaluation. Public input and
model snapshot dates remain separate from ballot and finance research dates.

## Follow-up for Hermes

[The explanation task](tasks/HERMES_GRADE_EXPLANATIONS.md) and
[1,296-item queue](../research/gaza-grading/explanation-queue-2026-10-26.json) bind
each summary to its exact saved request. Summaries should explain the recorded
evidence and score-to-letter mapping without changing the score or inventing an
unrecorded candidate position. No explanation generation is part of this release.
