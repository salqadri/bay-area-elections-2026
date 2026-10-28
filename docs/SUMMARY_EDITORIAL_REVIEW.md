# Summary editorial review — October 27, 2026

Publication **2026-10-27.12**, schema **1.28**, manually edits **336 letter-grade
explanations**. This is an editorial pass, not bulk model regeneration. The
complete before/after review is [archived](../research/gaza-grading/summary-editorial-review-2026-10-27.json)
and bound by hash to the previous and current explanation archives and exact
candidate scoring requests. Generator labels preserve original draft provenance;
the archive explicitly records manual editing. Every untouched paragraph,
including the approved 78-word Khanna explanation, remains exact.

Removed: missing-record disclaimers, thin/sparse-record padding, inventories of
absent statements/votes, and speculative claims that a candidate's broader stance
is unestablished. Brief known facts can yield a short paragraph rather than
padding to a minimum word count. Source attribution, explicit refusals, actual
non-sponsorship, historical dates, recommendation tiers and material uncertainty
about a specific factual claim are retained. JStreetPAC endorsements are not an
automatic reason for praise or condemnation; substantive conduct takes priority.
Underlying endorsements and evidence are not deleted or reclassified.

## Issue-observation eligibility

Four D results contained only unrelated local-platform points: **Shruti Kumar,
Arielle Fleisher, Boris Lipkin and Rebecca Lewington**. They now show N/A with no
political explanation panel. Raw model answers remain unchanged. A conservative,
versioned `require_issue_observation: true` mapping flag supplements the unchanged
0.22 evidence threshold: identity fields, false community membership and local
platform points without issue terms cannot establish a stance. Affirmative
owner-defined community alignment and supplied issue observations remain eligible.
Unknown nonempty evidence fields are retained conservatively, rather than silently
classified as irrelevant. This gate detects empty issue inputs, not the strength
or polarity of actual evidence. Historic mappings without the flag reproduce
the old result. Python, browser and local-server presentation use the same rule.

The new snapshot is `published-2026-10-27-editorial.json`, publication ID
`jev-2026-10-27-editorial`, with matching explanation archive and queue. All 1,296
requests, raw responses, numerical scores and evaluation provenance match the
previous snapshot. Bounds remain **0.7 / 1.4 / 2.3 / 3.3 / 4.4**, minimum evidence
**0.22**, no confidence cutoff. Counts: **A 121 · B 44 · C 13 · D 30 · E 67 ·
F 125 · N/A 896**. N/A notes remain archived but hidden in both readers.

## Future generation and Liccardo comparison

[Summary prompt v3](../research/gaza-grading/summary-prompt-v3.txt) and its
[hash-bound policy](../research/gaza-grading/summary-policy-v3.json) retain complete
evidence assessment, normally 45–80 words, allow shorter fact-only explanations,
forbid missing-record padding, and give JStreetPAC little weight. Hermes's Qwen
model defaults are unchanged. The numerical scoring rubric is unchanged.

At the owner's request, a separate Sam Liccardo comparison used GPT-6.1 Sol Low
with current generated state, saved questions and recorded answers. Its 71-word
draft is held for review, not published. The published Liccardo text was manually
edited to remove JStreetPAC as a positive opening rationale; his saved
**C (2.67 / 5)** remains unchanged. No Jev scoring calls were made.

## Verification

All **47/47 offline release checks pass**, including schema, both readers,
source-bound editorial manifests, short factual paragraphs, rejection of
missing-record boilerplate, the four real unrelated-platform cases, recommendation
and community eligibility, historical mapping replay, and browser/Python grade
behavior. All 1,296 frozen input/output/evaluation rows are identical to the previous
snapshot. Candidate/source/evidence/endorsement research is unchanged outside the
grade projection. The restarted local playground reports the same distribution
and retains the saved prompt and thresholds.
