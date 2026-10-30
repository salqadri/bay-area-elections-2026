# Voter prose and Samir Laymoun source policy

Publication **2026-10-29.3** applies the owner's editorial instruction to candidate
and race explanations. Samir's opinion is omitted when other relevant directional
evidence exists. Exceptions are the **Kamal Yassin race** and a candidate for whom
his opinion is the only relevant directional evidence. False community membership,
unrelated local-platform points, neutral ratings, not-elected records and absence
of tracked PAC money do not count as other directional evidence.

When an exception applies, state the relevant support/opposition or comment plainly.
Do not describe him as an individual rather than an institution, an owner-requested
opinion source, or separate from official organizational positions. Preserve honest
attribution and meaningful factual qualifications: his view must never become a
BAMC Action position or a candidate's own pledge. Raw source records and archived
Jev requests remain available; this policy governs voter-facing prose only.

## Current publication

- **19 candidate blurbs edited**, with exact before/after text in
  `research/gaza-grading/summary-editorial-review-2026-10-29-samir.json`.
- **Kamal Yassin's paragraph is unchanged**. It is the only remaining named Samir
  reference in the 1,296 published candidate explanations.
- Tandon's old opinion-only paragraph is replaced by direct evidence already
  present in publication 2026-10-29.2: **GE-1538 / GE-1539**, his genocide-language
  response and criticism of an unconditional ceasefire. This does not rerun or
  retroactively change the saved scoring request.
- No currently published race rationale names Samir. Historical cache lines and
  prior immutable explanation archives are preserved, not rewritten.
- All scores, grades, source evidence, endorsement records and race picks are
  unchanged. The recommendation plan is rebound to the updated dataset hash;
  its actual recommendations and rationale text remain exact.

The new immutable explanation archive is
`research/gaza-grading/explanations-2026-10-29-samir-editorial.json`. Its editorial
manifest binds every replacement to the prior archive and the unchanged candidate
and score-request identities. Edited entries are labeled `guide-editorial` rather
than claiming a new model-generated paragraph.

## Future Hermes generation

Use the hash-bound **summary-prompt-v4.txt / summary-policy-v4.json**. The historical
v3 prompt remains unchanged. Hermes's Qwen model, reasoning and concurrency defaults
are unchanged. `scripts/summary_source_policy.py` is shared by candidate generation,
attachment validation and race-reason generation. The generator supplies a per-candidate
exception decision. It also supplies newly collected current research separately
from the archived scoring state, and inventories those additions for the private
evidence audit. The audit must cover all archived and supplemental inventory IDs.

Candidate responses use `responses-summary-v4/`; prior response caches are preserved.
A response is reusable only when its full generation hash matches the prompt,
archived request and current research, and it passes the editorial prose guard.
The race prompt uses the same rules and changes its request hash; the existing
race-cache checks therefore reject stale prompt output on a future generation run.
No generation batch or Jev scoring call was made for this editorial publication.

`scripts/check_summary_source_policy.py` covers both exceptions, other evidence,
neutral/non-evidence cases, supplemental evidence, publication-wide prose and the
race prompt/validator. It is included in the **51-check release gate**.

## Standalone guide

After committing and publishing the research repository, refresh the local-only
TALL guide from the canonical JSON and its matching recommendation plan, then
publish the guide's dedicated Firebase target. The separate guide code remains
outside this repository. Do not edit its generated candidate blurbs independently
of the canonical publication.
