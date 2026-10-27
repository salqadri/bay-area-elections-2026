# Evidence chronology and source reconciliation

Prepared publication **2026-10-27.4** (schema 1.27) adds eight Jev-reviewed
observations and retires one obsolete guide observation. New grader/playground
inputs are **v15**. Candidate scores and explanations were not rerun.

Validation: **47/47 offline release checks pass**, including eight context
regressions. The restarted local playground serves all 1,296 candidacies with
11 receiving linked context. Frozen score and explanation archives remain
byte-identical; both generated readers match the prepared dataset.

## Reviewed cases

- **Wiener:** JTA's January 12 report records the debate refusal while both
  opponents answered yes, audience jeers, continued criticism and the subsequent
  Sunday video calling Israel's actions genocide. The model gets the sequence
  together and the guide's concern about political pressure. A private
  opportunistic motive is not presented as an independently established fact.
- **Khanna:** the Clerk records Yea on H.R.7006 on January 14 and Nay on H.R.7148
  on February 3. His January 16 post says Republicans “snuck” provisions into the
  bill and says he had voted to fund UNRWA. It does not literally say “I did not
  know”; the explanation is attributed. Official data also establishes March 27,
  2025 cosponsorship of the UNRWA Funding Emergency Restoration Act. That is not
  a roll-call vote; this refresh does not independently identify the exact prior
  UNRWA vote he claims. Keep the initial Yes, explanation, later No and separate
  restoration support together; neither erase the Yes nor omit the follow-up.
- **Liccardo:** official XML lists Block the Bombs cosponsorship from July 14,
  2026. The undated Vote for Peace no-support/funding prose item GE-0423 is retired
  through a registered review, with its original text preserved there. His current
  Ally endorsement is retained. The guide's undated funding claim cannot establish
  organization-only funding since 2024.
- **Wahab:** the same official source establishes her October 5 cosponsorship.
  Earlier Not elected entries can precede later House actions.
- **Community:** true means owner-confirmed membership in the **pro-Palestine
  Muslim community**, affirmative general-alignment evidence under this guide.
  It is not generic religious identification or proof of every specific policy.
  False/unknown is not adverse. New v15 publications reject N/A when this explicit
  signal was supplied. Historical evaluations remain exact; Jamal Khan's old 0.16
  evidence result requires a new evaluation, not a retroactive grade edit.

## Systematic maintenance

Discovery v4 adds debate/backlash/reversal, UNRWA explanation/follow-up and Block
the Bombs cosponsorship queries. Fingerprints invalidate older discovery caches.
Both explicitly verified X accounts are accepted, including `secondary_x_url`;
lookalike accounts still fail source review.

`congress-billstatus-xml` capture parses official GovInfo BILLSTATUS XML, binds
Congress/type/number to its URL, and preserves bioguide identities, cosponsorship
dates and withdrawals. Malformed dates or identities fail. Search snippets and
blocked HTML are not treated as proof. Example:
[H.R.3565 official XML](https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr3565.xml).

```sh
python3 scripts/research_gaza_gaps.py capture \
  --url https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr3565.xml \
  --raw /path/to/actual.xml --kind congress-billstatus-xml \
  --checked-on YYYY-MM-DD --output .research/NEW/bill-packet.json
python3 scripts/evidence_context.py --output .research/NEW/context-leads.json
```

The all-candidate audit flags possible obsolete guide claims, differing UNRWA
responses and position-change wording lacking trigger context. Its October 27
queue contains 11 leads across 11 candidacies, including the reviewed Khanna and
Wiener episodes. These are research leads, not findings of error; other cases
remain pending source review.

`evidence-context-v1.json` binds short interpretation notes to exact reviewed
evidence/action hashes and the immutable publication review. Changed anchors
stop reuse. A shared, hash-bound action family also groups the January/February
appropriations responses and UNRWA-restoration sponsorship for every covered
member; no personal explanation is transferred between candidates. All eligible reviewed Gaza observations now reach the model: the old
twelve-item cap cannot hide follow-ups. Existing funding-period and focused
endorsement filters still apply.

Collector synchronization accepts an exact candidate/record retirement from a
registered review. An edited claim or unreviewed draft still fails; a shared
publisher URL does not authorize deleting other observations.

## Hermes handoff

Hermes continues using `qwen/qwen3.8-27b` for narrative work, with its existing
runtime settings. The model-independent `summary-policy-v2.json` pins the hash of
`summary-prompt-v2.txt` and the evidence-coverage requirements. The prompt requires an assessment for every supplied item,
chronology/reconciliation and the defined community meaning, with no fixed
two-or-three-fact cap. Validate every ID once; coverage does not prove correct
polarity or interpretation, so keep review flags.

Frozen requests, questions, provider responses, scores and prior explanations
are untouched. Do not substitute v15 and claim new context computed an old grade.
Updated-record drafts remain held until the appropriate publication is prepared.

The registered review and portable source audit are
`research/reviews/context-followups-2026-10-27{,.audit}.json`. Full raw captures,
exact Jev requests and retry history stay in ignored
`.research/context-followups-2026-10-27/`. The portable audit preserves URLs,
hashes and actual source-review answers without redistributing full articles.
