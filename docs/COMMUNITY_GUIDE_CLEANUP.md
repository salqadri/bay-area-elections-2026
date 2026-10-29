# Candidate-only guide inputs — October 28, 2026

Publication **2026-10-28.2**, schema **1.30**, corrects guide polarity and comment
subjects while preserving the latest recommendation reader and every existing
published score and explanation. No candidate scoring or summary generation is
performed for this correction.

- **Steve Raspe and Heidi Owens:** BAMC Action now **opposes** both. The previous
  importer ignored the owner-authorized board guide's explicit `avoids`, leaving
  these two as comment-only observations. Official and authorized board-guide
  positions are now both read; contradictory explicit positions fail for review.
- **Peter Sundin Soulé:** Samir Laymoun's support remains, qualified as a
  **protest-vote recommendation**. The comment criticizing the incumbent is removed
  from Peter's record and input. BAMC's recommendation for Sam is not copied into
  Peter's input.
- **Sam Liccardo:** Samir's criticism is attached here as a comment about Sam,
  following the owner's explicit subject clarification. It is not converted into
  an invented explicit opposition rating. BAMC's support for Sam remains.
- **All candidates:** `community_guide_race_context` is removed from the builder.
  A candidate receives only their own recommendation observations and comments
  assigned to that candidate's reviewed subject.

## Repeatable subject review

The importer captures source placements unchanged, then assigns comments using
`research/endorsements/comment-subjects-2026-10-28.json`. Each of its 21 entries
binds the source card, URL, exact text hash and candidate subject. The one changed
subject is explicitly owner-confirmed. New or edited comments require subject
review before publication; a pronoun is never resolved automatically. Reviewed
recommendation context is stored separately from candidate policy evidence.

A refresh compares complete semantic records, including removed comment fields,
rather than matching only fields present in a new record. Removing a source
comment therefore creates an explicit before/after review instead of retaining a
stale quote silently.

The correction is registered as
`research/reviews/community-guide-cleanup-2026-10-28.json`, with a hash-bound Jev
source/subject audit. Jev accepted all 21 reviewed subjects and four proposed
record changes; these were source-attribution checks, not political evaluations.
The October 27 captures and audit remain immutable historical records.

Current normalized data contains **97 observations across 92 candidates**:
BAMC Action **16 supports / 4 oppositions**; Samir Laymoun **38 supports /
38 oppositions / 1 comment-only record**. All 21 comments remain stored, with the
incumbent criticism now assigned to Sam rather than Peter.

## Current versus evaluated input

The core input version is
**candidate-evidence-v18-candidate-only-guide-comments**, with the playground's
`-local-federal` suffix. The current 92 affected inputs are archived in
`research/gaza-grading/community-guide-states-2026-10-28.json`.

The playground's **Current input** tab previews this corrected state; the
**State JSON** tab retains the exact input used by a saved evaluation. Historical
requests are not rewritten. A new candidate evaluation uses the corrected input.

## Verification

All **48 release checks pass**, with nine focused guide/subject regressions.
Tests verify both corrected BAMC opposition labels, Peter's protest-vote qualifier
without Sam's endorsements/comments, Sam's correctly assigned criticism, changed
comment rejection, and explicit review of removed comments. Both public readers
render the corrected records. The latest recommendation reader also passes its
existing display test and remains unchanged. All published score/evaluation/
explanation fields are identical to the latest-main baseline; no scores were rerun.
The local playground serves the v18 current inputs with the saved prompt and
thresholds preserved.
