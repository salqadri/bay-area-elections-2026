# Published pro-Palestine model scores

Publication **2026-10-27.2**, schema **1.27**, shows project-owned Jev model scores
next to candidates on both public readers. A higher score follows the owner's
published pro-Palestine/anti-Israel rubric. These badges are distinct from CAIR
Action recommendations and the USCPR publisher's grades, which retain their own
source labels.

## Current publication — October 27 Vote for Peace refresh

Publication **2026-10-27.2**, schema **1.27**, uses the exact latest owner-saved
[criteria v5](../research/gaza-grading/criteria-pro-palestine-v5.json), from full
run `20261027T084211Z-eec4530d`. The
[current immutable archive](../research/gaza-grading/published-2026-10-27-vfp.json)
contains **1,296 fresh successful evaluations** after refreshing Vote for Peace.
The new full run `20261027T085927Z-01877b08` completed with zero errors. Two
follow-up evaluations use the same v5 questions and corrected current guide
notes for John Garamendi and Sam Liccardo. Every archived state matches its
current generated input before publication; original local runs remain exact.

132 first-party guide cards are bound to tracked candidacies: **103 additions,
29 updates** (91 Ally, 37 Opposed, 4 Neutral). Garamendi changed Opposed → Ally.
Source cards without a unique state/office/seat match remain held; absence never
deletes old records, and primary observations remain primary. Aggregated badges
for other organizations are not imported as their endorsements. See the
[refresh workflow](MAINTENANCE.md#vote-for-peace-refresh).

The publication uses the owner's saved inclusive grade bounds **0.7, 1.4, 2.5,
3.2, 4.4** and minimum evidence **0.20 / 1**. The publisher stores and checks this
minimum against its mapping, and public tooltips display it dynamically.
All CAIR Action / Vote for Peace directional-recommendation evidence guards pass;
there are no directional recommendation/N/A conflicts. Distribution:
**A 125 · B 41 · C 7 · D 40 · E 71 · F 121 · N/A 891**. No confidence cutoff.

The [new Hermes queue](../research/gaza-grading/explanation-queue-2026-10-27-vfp.json)
binds all 1,296 summaries to this archive and v5 prompt. Older explanations remain
archived and are not shown as explanations of these new scores.

## Historical October 27 first publication

Publication **2026-10-27.1**, schema **1.26**, uses the owner’s exact revised
[criteria v4](../research/gaza-grading/criteria-pro-palestine-v4.json), including
AB-715 in the E criteria and the JStreetPAC exception in the F criteria.
The [historical immutable archive](../research/gaza-grading/published-2026-10-27.json)
contains **1,296 latest successful saved evaluations**, all using those exact
questions. Source selection: 1,293 from full run `20261027T071000Z-d9860cf0`,
the owner’s later Matt Haney run, and two recommendation-evidence repairs.

Don Wagner and Kalimah Priforce initially received evidence scores below 0.10
despite Vote for Peace Opposed/Ally observations. New input v12 explicitly
identifies directional CAIR Action / Vote for Peace recommendations as concrete
stance evidence under the owner’s rubric, retaining tier, phase and source
qualifications. Only those two were re-evaluated, using the **same v4 questions**:
Wagner **1.06, E**, evidence **0.80**; Priforce **4.86, A**, evidence **0.72**.
Original runs/responses remain unchanged. There are no recommendation/N/A conflicts.

The owner set the inclusive **C upper bound to 3.2**. B begins strictly above
3.2 and ends at 25/6; all other bounds and the evidence threshold remain unchanged.
This mapping changes Shirley N. Weber and Marlon Duran from C to B, without
changing model scores. Current distribution: **A 126 · B 24 · C 13 · D 37 ·
E 64 · F 140 · N/A 892**. No confidence acceptance cutoff is applied.

Old “Why this grade?” summaries are preserved in the October 26 archive and
removed from current cards because their prompt, request hashes and bands no
longer match. The [new Hermes queue](../research/gaza-grading/explanation-queue-2026-10-27.json)
binds every candidacy to this exact new archive and v4 prompt. Explanations await
regeneration; no old narrative is presented as an explanation of a new score.

## Historical October 26 prompt and completed batch

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
| F | 0 ≤ score ≤ 0.7 |
| E | 0.7 < score ≤ 1.4 |
| D | 1.4 < score ≤ 2.5 |
| C | 2.5 < score ≤ 3.2 |
| B | 3.2 < score ≤ 4.4 |
| A | 4.4 < score ≤ 5 |

When the saved 0–1 `evidence_score` is **strictly below 0.20**, the derived grade
is **N/A**. Exactly 0.20 still receives a letter. The badge shows only N/A for
insufficient evidence; the raw model score and confidence remain in its tooltip,
accessible label, canonical JSON and archive. A candidate without a saved
evaluation also shows N/A, with a distinct explanation. No confidence cutoff is
applied. The model's separate `gaza_grade` is archived but not displayed as a
public badge.

Hover text and the badge’s accessible label include the model score confidence,
evidence score and Pacific evaluation time. Click it to read this methodology.
All 1,296 active candidacies have a saved evaluation in this publication:
**A 125, B 41, C 7, D 40, E 71, F 121, N/A 891**.

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


The publication check also requires captured nonhistorical CAIR Action and
Vote for Peace recommendations to appear in the exact saved input. A derived
N/A alongside a directional endorsement, preference, support or opposition is a
blocking evidence-review discrepancy. Primary recommendations remain explicitly
labeled observations. Vote for Peace Neutral/no-endorsement records do not imply
a directional stance. This guard never fabricates a score or rewrites a model
answer; repair the input or rerun Jev with the same preferred questions. The
fresh 1,296-candidate batch has zero CAIR Action recommendation/N/A conflicts,
and zero N/A cases with directional Vote for Peace observations. Neutral is not
a directional recommendation and can still have insufficient evidence.

## Historical evidence explanations (October 26 batch)

Publication **2026-10-26.2** (schema 1.25) adds one short evidence paragraph per
candidate, shown under a collapsed **Why this grade?** panel beside each badge in
both readers. Hermes generated all 1,296 summaries with LM Studio
`qwen/qwen3.8-27b` (temperature 0.1), giving the model exactly what Jev saw: the
frozen input state, the exact v3 rubric and the recorded score/evidence/gaza
answers, plus the deterministic band mapping and that historical archive’s 0.10
evidence threshold. Each summary is
bound to its `candidate_id`, `request_sha256` and publication id; N/A paragraphs
state only that evidence was insufficient (below 0.10 / 1 in that archive) without assigning a
stance. Summaries explain the saved score — they never regrade, and raw provider
answers remain immutable.

The frozen [explanations archive](../research/gaza-grading/explanations-2026-10-26.json)
holds every entry with its grade, generating model and timestamp; the dataset's
`pro_palestine_grading.explanations` binds its hash and the source queue.
[The explanation task](tasks/HERMES_GRADE_EXPLANATIONS.md) and
[queue](../research/gaza-grading/explanation-queue-2026-10-26.json) specify the
contract; `scripts/check_grade_explanations.py` re-validates every published
paragraph against the archive, request hashes and word/format/N/A rules.

```sh
python3 scripts/attach_grade_explanations.py --responses <dir> \
  --output-archive research/gaza-grading/explanations-2026-10-26.json \
  --publication-version YYYY-MM-DD.N --schema-version 1.25
```

Replaying the archive is idempotent; a changed archive must go to a new path.

## New research after the saved evaluation

The education-policy evidence refresh in publication 2026-10-26.5 (schema 1.26)
adds current research without rerunning Jev or replacing any score, exact request,
question JSON or frozen explanation. The local playground's **Current input** tab
previews the next evaluation; **State JSON** retains the evaluated input. A later
owner-authorized grade refresh must bind its explanations to the new archive.
See [education-policy research](EDUCATION_POLICY_RESEARCH.md).


## Funding input correction (October 26, publication 2026-10-26.8)

The v11 funding projection corrects donor periods and restricts new financial
inputs to reviewed organization amounts from calendar 2024 onward. The saved
grade batch and explanation archive are unchanged. Older funding-based saved
explanations display a notice that they may contain historical or mixed-donor
totals excluded from new evaluations. In particular, Haney’s saved explanation
still describes the old $47,700 total; his corrected public evidence instead
identifies the PAC’s $25,700 during 2021–2023. This does **not** mean his grade
has been recomputed. [Funding review and limits](FUNDING_EVIDENCE.md).

The October 27 publication supersedes those displayed explanations; its current
queue and archive are listed above. Exact replay preserves an explanation layer
only for the same archive hash/path/publication. A new score or mapping archive
clears that layer automatically, with old archives left intact. The publisher
accepts `--criteria` to bind each new publication to its own versioned prompt.
