# FEC independent-expenditure reconciliation — October 20, 2026

Prepared against `4053f984abd76d4546b3802bdb67169ae8fe79f2` (publication `2026-10-19.3`). Proposed publication `2026-10-20.1`, schema 1.22 unchanged. This is a PR for review, not a claim that GitHub Pages has deployed it.

## Exact answer: UDP against Abdul El-Sayed

The website's **$40,564,674.03 is a collector bug**, reproduced exactly from the live FEC Schedule E response for `S6MI00418`, committee `C00799031`:

| Reporting stream | Rows | Amount |
| --- | ---: | ---: |
| Regular reports, primary election | 25 | $20,140,908.74 |
| 24-/48-hour notices, primary election | 24 | $20,139,904.21 |
| 24-/48-hour notices, general election | 3 | $283,861.08 |
| Old collector's sum | 52 | $40,564,674.03 |

**All 24 primary notices match a regular-report transaction ID and amount.** Thus $20,139,904.21 was demonstrably counted twice. The extra regular-report transaction is $1,004.53 to The Phone Consultants, dated August 3. The three general-election notices have no matching regular-report transaction in this capture. They are outside the FEC candidate page's regular-report scope; excluding them does not mean that the spending did not occur.

For example, transaction `E615209634B23404484F`, $9,797.37 to United Media Partners LLC on July 30, occurs both in [the July 30 notice](https://docquery.fec.gov/cgi-bin/fecimg/?202607309899241594) and [the August monthly report](https://docquery.fec.gov/cgi-bin/fecimg/?202608209899671265). Both have `most_recent=true`, but different `sub_id` values (`4073020261539935176`, `4090820261595915656`). Neither deduplication by sub-ID nor amendment filtering removes cross-report overlap.

The official by-candidate API returns **$20,140,908.74, count 25**, exactly the user's [FEC candidate-page figure](https://www.fec.gov/data/candidate/S6MI00418/?cycle=2026&election_full=false&tab=other-spending). The captured [UDP reconciliation](../../research/finance/2026-10-20/udp-reconciliation.json) retains all 52 relevant row projections, source filing links, the full candidate-response hash (895 rows fetched), and the official aggregate. It contains no credentials.

## Root causes and source contract

The old shared collector called `/schedules/schedule_e/` without `is_notice=false`, retained both report streams, and discarded `is_notice` when saving its SQLite cache. Its `most_recent` filter only addressed amended versions, not repeated reporting of the same expenditure. Its memo rule also retained `memo_code=X` whenever the selected candidate's filing had no non-memo row. A shared `link_id` is not proof of a parent/subtotal relationship.

The FEC's own implementation establishes the intended comparison:

- [Candidate-page JavaScript](https://github.com/fecgov/fec-cms/blob/e9439435549f90f8db13ee42452072f70e9d6fea/fec/fec/static/js/pages/candidate-single.js) loads `/schedules/schedule_e/by_candidate/`.
- [Candidate-page template](https://github.com/fecgov/fec-cms/blob/e9439435549f90f8db13ee42452072f70e9d6fea/fec/data/templates/partials/candidate/other-spending-tab.jinja) distinguishes regularly scheduled reports from notices and warns of summary-processing latency.
- [API documentation source](https://github.com/fecgov/openFEC/blob/1d3bffc50e84226dea733fd0986dedf3e989688c/webservices/docs.py) explains that candidate aggregates exclude notices and memo entries to prevent double counting.
- [Aggregate SQL](https://github.com/fecgov/openFEC/blob/1d3bffc50e84226dea733fd0986dedf3e989688c/data/migrations/V0327__update_ofec_schede_aggregate_candidate_mv.sql) excludes memo-code X, groups by candidate/committee/direction/election cycle, and includes Form 5 data. The FEC owns those processing rules; custom election-type whitelists can diverge, including special elections.

The repair uses that official aggregate endpoint with **`cycle=2026&election_full=false`**, rather than reconstructing it from raw transactions. The explicit two-year selection matters for Senate candidates, whose full election period can span multiple cycles. FEC figures remain dated source totals, not an independent audit of every committee filing.

## Inventory-wide impact

All **136 unique FEC IDs / candidacies** were fetched successfully: 22 printed House and 114 provisional Senate. Governors and state/local candidacies have no federal IE layer. The nine unmatched Senate names still have no FEC ID and are outside this collector; this repair makes no new identity assignments.

| Cohort | Candidates refreshed | Candidates with changed amounts | Previous for / against | Corrected for / against |
| --- | ---: | ---: | --- | --- |
| Printed House | 22 | 12 | $12,939,400.21 / $2,587,950.82 | $7,529,062.91 / $2,347,250.60 |
| Provisional Senate | 114 | 57 | $545,438,599.49 / $1,215,252,749.28 | $117,540,580.34 / $127,562,823.54 |
| All federal | 136 | 69 | $558,377,999.70 / $1,217,840,700.10 | $125,069,643.25 / $129,910,074.14 |

These are **candidate-attributed sums, not unique national spending**. The before/after differences are **not a measurement of duplicate dollars alone**: they also exclude notice-only spending, adopt FEC memo/cycle processing, and can include intervening filings. The exact transaction-level duplicate proof above is for UDP/El-Sayed; no claim is made that every changed candidate was independently reconciled transaction by transaction.

Of 74 previously nonzero candidacies, 69 change and five remain monetarily identical. The corrected snapshot has 69 with positive regular-report amounts; Todd Achilles, John Deaton, Justin Murphy, Greg Levy and Brian Bengs now have no regular-report aggregate. Their prior nonzero totals must not be interpreted as proof of no spending after correction. Both readers explicitly qualify the zero-results message and explain the exclusion of recent notice-only spending.

El-Sayed's entire card changes from **$23,066,634.41 for / $131,757,078.14 against** to **$2,422,492.19 for / $20,829,487.24 against**. UDP is one component of that opposition total. The [complete impact report](../../research/finance/2026-10-20/impact.json) contains every candidate and changed spender/direction, including unchanged candidacies and actual retrieval timestamps. The [normalized official snapshot](../../research/finance/2026-10-20/official-aggregates.json) preserves every returned total and count. Campaign receipts, ballot decisions, identities, endorsements, platform statements and Gaza evidence are unchanged. El-Sayed’s receipts were separately checked against the live candidate-totals API: **$45,175,566.89**, January 1, 2025–September 30, 2026, exactly matches the published record; see the [receipts check](../../research/finance/2026-10-20/el-sayed-receipts-check.json). Other candidates’ receipts were not re-fetched in this audit.

## Systematic repair and reproduction

The existing plan/run/export/attach CLI and scheduled refresher now share one aggregate adapter. Normal page-number pagination replaces the raw endpoint's keyset pagination. It rejects missing results/counts, inexact or changing counts, repeated pages, wrong candidate/cycle, duplicate spender/direction rows, invalid counts/amounts and unsupported directions. Only a fully fetched, validated candidate response is committed. Genuine successful empty results become checked zeros; failures preserve prior snapshots.

A separate `aggregate_snapshots` table is keyed by candidate, cycle and method version. Legacy raw rows remain intact but cannot qualify as corrected data, even when their timestamps are recent. Attach requires coverage for every current FEC-linked candidate. Shared `checked_on` is the oldest actual candidate retrieval day in America/Los_Angeles; an explicitly overstated date is rejected. The scheduled publisher uses the same day convention. This prevents partial refreshes from overstating nationwide freshness.

The aggregate API supplies counts, but no transaction date ranges or committee types. Unavailable optional date ranges are omitted; known registry committee types are retained. No dates or types are invented. Support and opposition remain separate; totals use decimal arithmetic. Both built pages include corrected numbers, regular-report browse links, scope wording and dated provenance.

To reproduce the comparison from a clean checkout after setting `FEC_API_KEY`:

```sh
git show 4053f984abd76d4546b3802bdb67169ae8fe79f2:2026-11-03_Bay_Area_Elections.json > .research/ie-baseline.json
python3 scripts/fec_independent_expenditures.py run --force
python3 scripts/fec_independent_expenditures.py export --output .research/ie-current.json
python3 scripts/audit_fec_independent_expenditures.py --baseline .research/ie-baseline.json --snapshot .research/ie-current.json --output .research/ie-impact.json
```

Create `.research/` first if absent. For the exact historical comparison, pass the committed October 20 export instead of fetching again. The report hashes both inputs. Follow the [maintenance workflow](../MAINTENANCE.md#independent-expenditure-refresh) to attach a reviewed refresh, rebuild, validate and publish. Amounts are never halved or adjusted by a candidate-specific exception.

## Jev and validation

The owner requested TypeSafe Jev for decisions. The [actual requests/responses](../../research/finance/2026-10-20/jev-decisions.json), using the documented endpoint and pinned `jev-1.13.0`, are archived. Jev selected official aggregates (p=.78), a separate versioned cache (p=.99), and a full federal refresh (p=1.00). Its first broad diagnosis was low-confidence (p=.41); it was not treated as proof. After the deterministic transaction-ID comparison, a focused overlap question returned yes (p=.91). Financial amounts come entirely from FEC data and deterministic arithmetic, not the model.

**All 29 release checks passed**, with **22 finance regressions** passing on the final collector. Chrome checks passed in both readers at 1440px and 390px: corrected El-Sayed totals, source links, regular-report wording, initially collapsed disclosures, no horizontal overflow and no JavaScript errors. Address-page checks used San Francisco county browsing, not a new live geocoder test. A structural comparison proves every non-IE record is preserved exactly. The macOS test run used a real workspace `TMPDIR` because an existing review-history fixture does not resolve the system `/var` → `/private/var` symlink; no production review guard was weakened. The finance regressions include the source-bound UDP reproduction, both directions for one committee, multiple pages, malformed/partial responses, legacy/wrong-cycle cache rejection, snapshot preservation after failure, complete-scope/date guards, timezone boundaries and credential redaction. The full offline release gate covers schema, evidence-history preservation, generated pages and both readers. It does not certify all political research, live address services or unique economic spending behind every FEC record.
