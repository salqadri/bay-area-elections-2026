# Direction-aware recommendation eligibility

PR #22 adds `direction-aware-selection-v1` on November 2, 2026. This is an
eligibility/data-direction correction, not a new scorecard evaluation or a
protest-vote policy. The score questions, thresholds, exact saved requests and
responses, and candidate letter grades are unchanged. Production is unchanged.

## Failure and guard

The old selector removed N/A candidates, kept graded candidates through D, and
automatically selected a sole remaining graded candidate. Consequently a D
based only on a source opposing someone could become a recommendation for that
same person. It also omitted the unassessed opponent's recorded support.

`scripts/recommendation_evidence.py` projects current generated evidence into
the selection input. Relationships, source names, tiers, phases and qualifiers
remain explicit. The narrow gate excludes a candidate from automatic selection
when their only relevant directional observations are opposition from the
existing owner-designated recommendation sources and there is no other issue
record. Historical records and neutral ratings do not become current opposition;
unrelated campaign priorities and zero/unmapped spending are not issue evidence.
Opposition by an unrelated organization is not assigned the same meaning.

Every candidate, including N/A candidates, appears in future Jev race-selection
context. Only eligible graded candidates are choice options. N/A continues to
mean unassessed; neither source opposition nor a source's support upgrades that
candidate's recorded grade. This guard does not choose an opponent or create a
new protest recommendation. Existing separately maintained TALL editorial rules
remain separate from score-based selection.

## Cache and publication contract

The new request hashes bind the policy, full roster and signed observations.
Changing only an endorsement direction invalidates an old cache entry. A stored
choice must be both eligible and among the highest remaining letter grades.

`scripts/revalidate_recommendations.py` provides an offline migration. It keeps
exact old provider requests/responses and adds a separate revalidation receipt
for an unchanged valid choice. The receipt is not a new Jev answer and cannot be
used as a cache hit for a future request. Invalid choices are withheld; their
old rationale and selection are archived in the audit and removed from the
rendered recommendation. A replacement choice requires a separate selection
review or call, rather than a migration inventing an opponent endorsement.

The November 2 audit is
[`research/reviews/opposition-selection-2026-11-02.json`](../research/reviews/opposition-selection-2026-11-02.json).
For the PR's frozen-score plan, **Rob Stump (CA2026-112) is withdrawn** and **160
archived choices are retained**. Rommy Kushner is already N/A/unrecommended in
that frozen-score plan. Under the latest held scores used by the local review,
both **Rommy Kushner (CA2026-176)** and **Rob Stump** had been automatic picks;
both are now withheld. Their recorded D grades remain. No replacement candidate
is automatically selected. No model calls or live deployment occurred.

To revalidate a plan against its exact bound dataset without overwriting it:

```sh
python3 scripts/revalidate_recommendations.py \
  --dataset 2026-11-03_Bay_Area_Elections.json \
  --plan research/candidate-recommendations/recommendations-2026-10-28-latest.json \
  --output .research/selection-review/plan.json \
  --audit .research/selection-review/audit.json
python3 scripts/check_recommendations.py
```

Review the proposed plan and audit together. Rebuild the readers only after
adopting a plan; do not mix a plan and a different dataset or rewrite archived
answers to match a changed prompt. `check_recommendations.py` covers signed
observations, N/A context, opposition-only exclusion, mixed evidence, historical
records, cache invalidation, exact historical retention and stale-rationale
removal. The full release gate includes these regressions.
