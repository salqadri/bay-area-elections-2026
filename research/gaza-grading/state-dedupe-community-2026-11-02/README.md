# Current-state correction — November 2, 2026

No scoring or summary calls, no new prompt or threshold, no deployment.
State version: `candidate-evidence-v26-endorsement-dedupe-community-reports`.

## Duplicate organization observations

The prior normalizer only consolidated California Jewish Democrats aliases and
required identical phases. ACJDC's own general endorsement and a campaign's
unspecified-phase claim therefore both survived for Sara Lamnin.
The normalizer now compares recognized organization identities and lets an
unspecified claim yield to a matching first-party record. It preserves distinct
explicit phases, history, directions, tiers, shared status and unique comments.
Neither the canonical endorsement data nor old requests are deleted.

One redundant ACJDC campaign claim is removed for each of:
Scott Sakakihara, Sally J. Lieber, Ross Bernet, Mark Humbert, Barbara Lee,
Jamie Yee, Kathryn Camp and Sara Lamnin.

## Harris Mojadedi

His old evaluation did not receive the MAA report or article context. The last
change refreshed narratives and withheld a race pick, without changing scoring
inputs. `community_report_context.py` now reads explicitly registered reports
from `research/community-reports/state-sources-v1.json`, matching both candidacy
and position. MAA's owner-reported **strong opposition** appears alongside the
other directional observations, explicitly marked not independently verified.
The article's documented criticism of LGBTQ-related guide criteria is a separate
community-policy observation with its date, URL and scope; it is not presented
as Gaza evidence or verification of MAA opposition. No identity inference or
new scoring rule is added.

The existing A remains an old result until a new evaluation is requested. The
playground's Current input previews these additions; State JSON remains the
exact old request. No archived Jev run, request hash, answer or publication has
been relabeled. The narrative source bindings were refreshed after confirming
the same facts/text, with previous hashes retained; original model inputs and
responses remain exact in the earlier Harris context directory.

## Audit and validation

`state-changes.json` captures all nine changed current states (before/after).
`selection-audit.json` revalidates the frozen source plan against the new compact
observations: no choice changes, no provider calls and no withdrawn choices.
This refreshes source bindings without inventing or relabeling model answers.
Regression tests cover Sara's single observation, distinct-source qualifiers,
Harris-only mapping, attribution, article/Gaza separation and raw-data immutability.
The local previews and comparison are rebuilt; production stays unchanged.

`selection-plan.json` carries the same 37 held cohort choices with updated
source projections. Exact original provider requests and responses remain
unchanged. An explicit offline receipt accepts only removal of an unspecified
copy already represented by a matching dated-phase observation; the complete
resulting request must otherwise match. A direction, tier, grade, unique comment
or question change is not accepted by this receipt. This is not a current cache
hit or a new provider decision. The portable review manifest loads this overlay
after the earlier source plan.

Validation so far: 16 organization-context tests and 21 recommendation tests
pass. Live playground checks confirm Sara has one ACJDC observation, Harris's
current input has MAA opposition and separate article context, and his exact
saved evaluation still has its original request hash without these new facts.
No credentials occur in the new archive.

Full offline release gate: **53/53 PASS**. Chrome current-input checks pass for Sara and Harris.
