# BAMC Action and activist recommendations

Publication **2026-10-28.2**, schema **1.30**, corrects guide polarity and comment
subjects. Current data has **97 source observations across 92 candidates / 63 races**.
See [the correction and exact attribution rules](COMMUNITY_GUIDE_CLEANUP.md).

| Source | Support | Oppose | Comments only | Candidate comments |
|---|---:|---:|---:|---:|
| BAMC Action | 16 | 4 | 0 | 18 |
| Samir Laymoun | 38 | 38 | 1 | 3 |

BAMC Action positions come from its official guide and the owner-authorized
board guide. Its explicit opposition to Steve Raspe and Heidi Owens is included.
Contradictory explicit positions require review. Samir Laymoun's activist views
remain a separately attributed source. Nonselections alone never imply opposition.
Propositions and ballot measures are excluded.

Comments are verbatim and source-linked. Every comment has a hash-bound reviewed
candidate subject. Samir supports Peter Sundin Soulé as a protest vote; his
criticism of Sam Liccardo is assigned to Sam's input, rather than Peter's. A
recommendation qualifier is not a candidate policy statement. Race-wide guide
context is not included in candidate inputs. The original October 27 snapshots
remain immutable history.

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

`endorsement-focus-v5.json` includes BAMC Action and Samir Laymoun alongside CAIR
Action and Vote for Peace. New core state version is
**candidate-evidence-v18-candidate-only-guide-comments**. The playground derives
its version from that core with a `-local-federal` suffix. Observations retain
polarity, phase, reviewed comment subjects, complete comments and recommendation
qualifiers. `community_guide_race_context` is no longer generated.

The latest current states are archived in
`research/gaza-grading/community-guide-states-2026-10-28.json`. Previous scoring
requests, answers and explanations are retained unchanged; the **Current input**
tab previews new inputs, while **State JSON** shows a saved evaluation's original
request. No scoring rerun is performed for the correction.
