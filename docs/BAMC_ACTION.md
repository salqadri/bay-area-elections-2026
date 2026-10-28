# BAMC Action and activist recommendations

Publication **2026-10-27.13**, schema **1.29**, adds **96 source-specific candidate
entries across 92 candidacies / 63 races**. BAMC Action is the owner-designated
trusted Bay Area Muslim Council source. Its organization guide determines its
positions; a separately identified activist retains his own opinions. No
propositions or ballot-measure entries are imported.

| Source | Support | Oppose | Comments only | Candidate comments |
|---|---:|---:|---:|---:|
| BAMC Action | 16 | 2 | 2 | 18 |
| Samir Laymoun | 38 | 38 | 0 | 3 |

The [official organization guide](https://bamcaction.org/myvote/bamc-action)
provides BAMC Action's support/opposition. Candidate comments from the
[board-member guide](https://bamcaction.org/myvote/razim) are included as BAMC
commentary at the owner's explicit direction. Its personal selections do not
create organization positions. In particular, tactical comments concerning
Heidi Owens and Steve Raspe are **comments only**, not official opposition.

[Samir Laymoun's guide](https://bamcaction.org/myvote/samir) is a separately
attributed personal opinion source. The owner supplied his full author identity.
His selections and all three candidate comments are retained, including opinions
that differ from BAMC Action. Opponents not explicitly listed as avoided are not
automatically assigned opposition.

## Candidate comments and differences

`endorsements[].comments` stores each complete, verbatim comment with its source
URL. Both readers render comments as text beneath the matching recommendation;
HTML in comments is never executed. The new `comment` relationship asserts no
support, opposition or neutrality rating. Explicit ranked choices preserve their
preference rank. Other publishers' records remain unchanged.

BAMC Action supports **Sam Liccardo**; Samir supports **Peter Sundin Soulé**.
Samir's tactical comment about reducing an incumbent's winning margin is kept
under the source candidate where it was posted. The current Jev state includes
both sources' differing race selections and their comments, with an explicit
warning against treating ambiguous pronouns as a candidate policy fact. No
explicit Samir opposition rating for Liccardo is invented. Samir's opposition to
Zoe Lofgren and Jimmy Panetta is separately recorded with its comments.

## Repeatable import and review

`scripts/sync_bamc_action.py` reads the public organization, shared-guide and
catalog APIs used by these pages. Captures exclude non-candidate contests and
retain source hashes, API URLs, source update timestamps, exact option IDs,
complete candidate comments and normalized official labels.

```sh
python3 scripts/sync_bamc_action.py capture --checked-on YYYY-MM-DD \
  --output research/endorsements/bamc-action-YYYY-MM-DD.json
python3 scripts/sync_bamc_action.py review \
  --capture research/endorsements/bamc-action-YYYY-MM-DD.json \
  --id bamc-action-candidates-YYYY-MM-DD \
  --output research/reviews/bamc-action-candidates-YYYY-MM-DD.json \
  --dispositions research/endorsements/bamc-action-dispositions-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py preview research/reviews/bamc-action-candidates-YYYY-MM-DD.json
```

Review identities and source distinctions before applying with `reviewed_updates`.
Names are matched exactly after normalization, together with county, office,
jurisdiction and seat. Unknown options, conflicting explicit positions and source
layout/cycle changes fail closed. Ambiguous identities are held. Refreshes replace
the same publisher/candidacy record; exact repeats produce no new decisions.
Source absence never deletes a recommendation. Existing immutable captures and
registered reviews must not be overwritten.

The October 27 publication review and its hash-bound Jev audit cover all 96
entries. One initially held statewide identity was resolved using the complete
source contest, matching opponent pair and explicit avoids list; the initial
answer and follow-up remain archived. These were source/identity decisions, not
candidate scoring calls.

## Jev inputs

`endorsement-focus-v4.json` explicitly includes BAMC Action and Samir Laymoun
alongside CAIR Action and Vote for Peace. New state version is
**candidate-evidence-v17-bamc-action-comments**; playground metadata derives from
that shared version with a `-local-federal` suffix to prevent version drift.
Compact observations preserve
source names, support/opposition/comment-only relations, phase, complete comments
and explicit preference ranks. Short context identifies source trust and separates
organization recommendations, personal activist opinions and tactical voting
advice from specific Palestine policy claims.

`community_guide_race_context` exposes different selections only when both sources
have nonempty, different support lists in that race. A rival's selection is not
an invented opposition rating. Current affected states are archived in
`research/gaza-grading/community-guide-states-2026-10-27.json` for review.

Existing saved scoring requests, numerical responses, grade bands, evidence
minimum, explanations and historical score archives are unchanged. They do not
pretend the new source material was present in the old scoring run. New runs use
the updated generated inputs; no candidate scores were rerun for this import.

## Verification

All **48 release checks pass**. Seven source-specific regressions cover official
versus personal polarity, comment-only handling, excluded measures, source changes,
exact office/seat identity, repeated-import deduplication, complete comment delivery
to new states, differing race choices and the bound Jev identity audit. Both reader
integration checks verify independent CAIR Action/Samir opposition records and the
new comments. The synchronized core/playground version is separately checked.
All prior published score/evaluation/explanation fields remain identical. The local
playground exposes all 96 new source observations across its 1,296-candidate catalog.
