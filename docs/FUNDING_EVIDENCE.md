# Funding evidence: periods and organization donors

Publication **2026-10-26.8** corrects seven Track-JPAC observations and changes
new Jev inputs to v11. Schema remains **1.26**. No candidate scores, questions,
saved request states or archived explanations were changed or rerun.

## What went wrong

Haney’s source table lists **California Jewish PAC: $25,700, 2021–2023** and
**Robert J. Fisher: $7,500, 2021–2025**. The old extraction combined donors into
$47,700, assigned the combined 2021–2025 period to the whole summary and used
2025 as the evidence date. This incorrectly made the PAC money look recent.
The source’s own analysis date is May 7, 2026; that also is not a donation date.

The generic state builder passed every funding summary as `date: summary`.
It had no donor-type or contribution-period gate. Other sources use analysis
dates or lifetime totals, so a simple `evidence.date >= 2024` filter would repeat
the error. WhoFundsMyRep’s 2026 ballot page also explicitly defines “received”
as **direct and earmarked** contributions. That combined amount is not a proven
organization-only donation total, even with a valid recent cycle.

## Public corrections

All seven Track-JPAC pages were retrieved directly and their individual donor
table cells parsed. Jev reviewed proposed corrections against the captured text;
the immutable review records exact before/after values and content hashes.

| Candidate | Corrected interpretation |
|---|---|
| Matt Haney | $25,700 from California Jewish PAC during 2021–2023; historical, excluded from new financial scoring input. |
| Marc Berman | $29,050 from that PAC during 2019–2025; no 2024-onward portion isolated. |
| Gail Pellerin | $11,400 from that PAC during 2023–2025; no 2024-onward portion isolated. |
| Ben Allen | $24,200 from that PAC during 2021–2025; no 2024-onward portion isolated. |
| Buffy Wicks | $54,850 combines individual donors across 2017–2025, not organization-only recent money. |
| Diane Papan | $2,000 from individuals in 2021 and 2023, not organization donations. |
| Robert Rivas | $63,577 combines individual donors and a $5,500 law-firm contribution in 2023 across 2017–2025; not a recent organization total. |

Haney/Papan dates now identify the final year of the stated historical donor
period, explicitly explained in `date_note`. Other rows retain the source’s
analysis date with an explicit warning that it is not a donation date. The
collector ledger mirrors all seven replacements. Original observations survive
in immutable publication reviews and historical evaluation archives.

Both readers explain that reporting dates need not be transaction dates. Saved
explanations made under pre-v11 funding rules are flagged when funding evidence
is present; their text and scores stay bound to the original request. Haney’s
saved explanation can therefore still quote the old total, visibly identified
as an earlier evaluation. No new A/B/etc. grade is implied by this repair.

## Systematic input contract

[funding_evidence.py](../scripts/funding_evidence.py) projects financial evidence
using a [reviewed hash-bound index](../research/funding/jev-funding-policy-v1.json).
It handles the `aipac_funding` dimension and detects mixed monetary sentences
filed in other dimensions (one additional Ayotte observation in this audit).

- Financial amounts require a named organization classification and an explicit
  period wholly on/after **2024-01-01**. The gate never uses the observation’s
  publication/check date as a transaction date.
- Cross-cutoff aggregates, lifetime/unknown periods, individual/mixed-donor
  totals and unseparated earmarked receipts are held. A 2024 election cycle can
  include 2023. No aggregate is prorated or assumed recent from a current race.
- Outside spending remains distinct from campaign receipts. Structured
  current-cycle FEC/CAL-ACCESS independent expenditures are unchanged.
- Reviewed nonfinancial policy statements, refusals, endorsements and historical
  travel context remain; mixed sentences can have narrow projections that omit
  old money claims. Financial facts are never silently re-dated.
- A missing index entry or changed evidence hash is held out automatically.
  Filtering precedes the generic evidence budget. Omission means unresolved
  for this input, **not proof of zero donations**; a short state scope line says so.

The audit covers **221 observations across 151 candidacies**: 220 originally
classified as funding and one mixed sentence in another dimension. **185 are
held**, **34 retain nonfinancial projections**, and **2 retain explicitly dated
organization outside-spending projections**. Many held observations describe
potentially real money; they need donor/period separation before reuse. This
repair is not a fresh transaction-level audit of every candidate or a guarantee
that all recent organizational donations have been found.

## Research and future refreshes

[research_funding_periods.py](../scripts/research_funding_periods.py) batches
existing observations through Jev choice questions about period and donor type;
it does not grade candidates or automatically publish first-pass choices:

```sh
python3 scripts/research_funding_periods.py \
  --work .research/funding-refresh --jev-key-file /secure/path/jev-key
```

Review the actual source donor rows/transactions and the model classifications.
Save approved projections with exact `evidence_sha256`, period, donor type,
contribution/outside-spending kind and narrow `model_text`. Renew the review when
source observations change. For public corrections use `reviewed_updates.py`,
then `merge_gaza_evidence.py --sync-published`; do not edit a frozen score archive.
The Track-JPAC parser reads each donor’s **own Years cell**, never a neighboring
row or the page analysis date. Changed table shapes stop for review.

The legacy collector now filters FEC organization receipts dated 2024 onward,
excludes memo/conduit receipts and individual-employer matching, and instructs
extraction to preserve donor-specific periods. New financial output still needs
source review and an approved projection. No new web searches were needed here;
the named pages were fetched directly. Future web searches must use Serper.

Artifacts:

- [Seven public corrections](../research/reviews/funding-periods-2026-10-26.json)
- [Captured donor-row audit](../research/funding/track-jpac-donor-rows-2026-10-26.json)
- [Tracker receipt/spending definitions](../research/funding/tracker-semantics-2026-10-26.json)
- [Initial Jev classifications](../research/funding/classification-2026-10-26.json)
- [Exact Jev choice requests/responses](../research/funding/source-decisions-2026-10-26.json)
- [Approved projection index](../research/funding/jev-funding-policy-v1.json)

Jev was used for **evidence review only**, with no candidate score questions.
Classifier output was reviewed: mistaken financial-as-nonfinancial decisions
were held, and mixed statements narrowed. Unsupported original funding amounts
were not admitted merely because a classifier assigned a recent category.

Validation: **45/45 release checks pass**, including new donor-year/cutoff/earmark
regressions. Browser checks cover both readers and the local playground at
desktop/mobile sizes. All 146 prior local run files retain their hashes.
