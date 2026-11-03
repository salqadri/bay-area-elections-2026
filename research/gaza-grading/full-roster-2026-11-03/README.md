# Owner-run full-roster scores — November 3, 2026

Held in PR #22 for local review; no production deployment and no new API calls.

`run.json` is the byte-for-byte saved playground run
`20261103T075603Z-68c505d6`: 1,296 complete candidates, zero errors, v26 input
format. Every request uses exactly the archived v10 questions. Prior runs and
prompts are retained. The default questions and portable manifest now prefer v10.
The previous v9 targeted-run tests still bind their exact historical v9 prompt.

Thresholds are unchanged: F <= .74, E <= 1.4, D <= 2.3, C <= 3.3, B <= 4.4,
A through 5; evidence minimum .22 with the issue-observation guard. No confidence
acceptance cutoff. New distribution: A 119, B 46, C 20, D 35, E 84, F 121, N/A 871.
The prompt adds strong MAA opposition to the lowest criterion and removes the
October 2023 statement exception. The prior roster results used mixed prompts;
input differences and inference variation also affect changes.

`comparison.json` and CSVs compare against the prior eight-run PR snapshot:
31 letter changes (19 Bay Area), 1,179 numeric changes across the full roster,
and 372 numeric changes among candidates with a visible old or new grade.
`prompt.diff` compares preferred v9 with the exact new questions. It does not
claim the older 1,249 roster evaluations used v9. All request hashes and questions
were validated; no saved answer is retroactively relabeled.

## Current factual correction versus saved input

Tracy Jensen's anti-war-letter wording was corrected after this run. Her saved
C 2.32 remains a result of the original input; the live Current input now has the
correction and source-bound context. The source review preserves the independent
January 2024 ceasefire-support record. No additional evaluation was requested.
Harris is B 3.98 and his publisher-withheld race setting stays in place.

## Local previews and narrative status

The owner explicitly requested the latest full-roster scores in both local
previews. Older explanations retain their original request hashes and are
visibly labeled, rather than presented as newly generated summaries. A local
staging-only TALL adapter permits this labeled older text; production's strict
summary binding remains untouched. New N/A candidates have no grade explanation.
Missing explanations use a refresh placeholder, not invented text. The corrected
Tracy candidate/race paragraphs take precedence over their archived originals.

Existing selected candidates are retained only while eligible and among the
highest grades. No replacement race decisions or model calls are made; an invalid
previous choice is withheld for review. Publisher holds and the separately
maintained TALL editorial exceptions remain scoped to their original conditions.
The preview remains 340 races, 876 candidacies and 14 propositions. Its current
comparison has 123 picks versus production's 122, six changed picks, 11 same-pick
letter changes and 44 candidate letter changes. Score publication in the root
canonical dataset remains the frozen public version; this is a held overlay.

Local URLs: http://127.0.0.1:4173/ and /changes.html; research preview at
http://127.0.0.1:8791/; Jev playground at http://127.0.0.1:8787/.
The `.research/research-site-preview/build_preview.py` and separate TALL
`verification/pr22-preview/build_preview.py` are local preview builders, not
production deployment commands. Preserve current/older narrative provenance.

The local all-roster refresh queue contains 425 graded candidates: 424 older
explanations retained with their original source hashes and one missing narrative.
No new summaries were generated. The research preview exposes `refresh-plan.json`
and candidate/race CSV queues. TALL adds visible older-summary labels on screen;
these preview labels are excluded from printing.

Full offline release gate: **53/53 PASS**. Local desktop/phone and exact-score preview checks pass.
