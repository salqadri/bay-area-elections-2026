# Finance fixes and Gaza/ceasefire evidence audit

Reviewed October 14, 2026 against baseline `6fdd99e95adfd11fc5c8a7551d3055161223f476`. Proposed publication `2026-10-14.2`, schema 1.18. This review does not refresh the election-wide October 4 research date or October 12 finance snapshot.

## Requested code corrections

The finance publisher now passes the Git remote and `HEAD:main` as separate arguments. Optional token authentication uses a child-process configuration header, with raw/encoded tokens and URL credentials redacted from failures. Configured Git credentials also work. Publication requires a clean `main` checkout; `--skip-push` permits local review. No live authenticated push or FEC refresh was performed as part of this audit.

Schedule E aggregation now groups by spender **and direction**. A committee spending both for and against one candidate retains both amounts, row counts and date ranges. The existing amendment, cycle and memo filters remain. Published amounts have not been recomputed: the original raw Schedule E ledger was unavailable, and a new live finance retrieval would be a separate dated refresh.

First reported receipts, including a reported zero, require a valid coverage period and authorized committee IDs. Missing metadata preserves the unknown amount; existing coverage exceptions and newer snapshots are protected. The obsolete unavailable-total note is removed only after a previously unknown amount becomes a complete numeric record.

Both readers now use the same collapsed campaign-money disclosure, including receipts, independent spending, coverage/retrieval dates, qualifications and FEC links. The address page previously omitted it. Fixed synthetic tests cover zero, unknown, both spending directions and safe publication. Page integration checks derive current amounts from the snapshot and format dates consistently in America/Los_Angeles. The full release command has 19 checks.

The owner accepted findings #2 (ballot exclusion evidence) and #3 (logo filename names); those records and rules remain unchanged.

## A real example for endorsement finding #4

Jimmy Panetta's published campaign-claim record lists **Moms Demand Action** with `relation: endorsed`, while its stored quote is “2026 Moms Demand Action Gun Sense Candidate Distinction.” Gail Pellerin has the same classification, and her [current campaign endorsements page](https://www.gailpellerinforassembly.com/endorsements-26) displays that distinction. The [program's official FAQ](https://gunsensevoter.org/faq/) explicitly distinguishes the designation from an endorsement and prohibits describing it as one.

This demonstrates the semantic gap: a quote can appear on an endorsements page while describing an award or qualification. Its presence alone cannot prove the modeled relationship. A separate Everytown endorsement would be separate evidence; it would not turn this distinction into a Moms Demand Action endorsement. The user requested an example, so this PR does not change the endorsement layer or its collector.

## Gaza research scope and findings

The [audit inventory](../../research/reviews/gaza-evidence-audit-2026-10-14.json) records 198 Serper discovery queries, including separate Gaza/Palestine and ceasefire searches for all **72 printed federal/state candidacies**. Separate ceasefire searches also covered the 39 existing local evidence dossiers, including the two now held for attribution. All 245 existing summaries and provenance were screened and their 228 distinct cited URLs retried. Raw search responses and source captures stay in ignored local caches; committed provenance includes source hashes and retrieval outcomes.

Automated excerpt checks were triage: 204 normalized excerpts were found, 14 entries had no stored quotation, 23 needed contextual review, and four yielded no usable source text. An excerpt match does not verify identity, context or a financial claim. The 23 mismatches can include shortened quotations or extraction differences; they are not a count of false statements. Four unavailable original citations (three Connie Chan, one Catherine Stefani) remain published without a claim of fresh verification.

The [registered change review](../../research/reviews/gaza-ceasefire-audit-2026-10-14.json) records exact before/after changes, identity/date grounds, held leads and source hashes:

| Candidate | Reviewed change |
| --- | --- |
| Jimmy Panetta | Restore three formerly inaccessible official statements: the [January 15, 2025 ceasefire agreement](https://panetta.house.gov/media/press-releases/rep-panettas-statement-ceasefire-agreement-between-israel-and-hamas), [July 28 humanitarian emergency](https://panetta.house.gov/media/press-releases/rep-jimmy-panettas-statement-dire-humanitarian-situation-gaza) and [October 13 hostage release](https://panetta.house.gov/media/press-releases/rep-jimmy-panettas-statement-release-israeli-hostages). Summaries preserve his Israeli-security, hostage-release and Hamas-related qualifications. |
| Scott Sakakihara | Add a [March 16, 2026 interview profile](https://eastbayinsiders.substack.com/p/scott-vs-palantir) reporting that he pushed Union City to consider a Gaza ceasefire resolution in 2024. The publication date is not presented as the date of that action or proof of a final vote. |
| Alex Lee | Add his individually attributed ceasefire statement in [CAIR's October 17, 2023 release](https://ca.cair.com/press-release/more-than-50-california-elected-officials-speak-out-in-support-of-gaza/). Collective signatory lists are not used to infer individual statements. |
| Sally J. Lieber | Add an attributed assessment from the [2024 CAIR Action Santa Clara guide](https://cairaction.org/wp-content/uploads/2024/11/SCC-Voter-Guide.pdf), page 5, whose table was visually checked. It describes ceasefire support during her earlier supervisor candidacy; the entry is labeled as a guide observed October 14, 2026, with unknown original statement dates. |
| Rebecca Eisenberg | Quarantine GE-0344: the claimed social reply is not in the retrieved parent post, no direct reply URL was established, and the account was not positively linked to the candidate. This hold does not establish that the quotation is false. |
| Seema Badar | Quarantine GE-0197: protest attendance and the organizer's language cannot establish her personal genocide/BDS position. Two stronger ceasefire-related leads remain held pending a retrieved identity bridge to the Dublin USD candidate. |
| Mike Hutchinson | Remove GE-0215 as a republication of the same November 2023 story/action; retain GE-0212. |
| Valarie Bachelor | Remove GE-0220/0221 as syndicated copies of the story retained in GE-0219; retain the distinct Oaklandside source. |
| Melissa Hernandez | Remove GE-0131 as a syndicated copy of the story retained in GE-0137. |

The result remains **245 evidence items under 82 printed candidacies**: six accepted/restored items and six quarantined/deduplicated items. Original held records are preserved in [the quarantine](evidence-quarantine.json); resolved Panetta holds are preserved in its resolution history. County presence is Alameda 38, Contra Costa 25, San Francisco 24, San Mateo 26 and Santa Clara 30, with overlapping shared contests.

## Remaining limits

Evidence coverage is stronger for federal candidates (20/22) and state candidates (25/50). It remains sparse for city/town (30/394), education (7/288), judiciary (0/18), county (0/2) and special-district (0/101) candidacies. The 803 local/judicial candidacies were not exhaustively searched in this pass. Missing evidence must never become a neutrality or no-position label.

Seema Badar's [November 9, 2023 CAIR rally statement](https://ca.cair.com/press-release/cair-sfba-joins-50-teachers-parents-workers-and-ca-14-residents-in-urgent-call-to-congressman-swalwell-to-support-a-ceasefire/) and [December 1 community ceasefire letter-writing page](https://mcceastbay.org/writing-letters-to-congress-12-01-23/) are useful follow-ups. Search snippets suggest matching community roles, but a retrieved primary identity bridge is still needed before publication.

Third-party funding trackers, donor classifications and guide roll-call assessments remain attributed source claims. Their transactions and legislative conclusions were not independently audited. This is a targeted manual review and retrieval audit, not certification of every retained political claim or exhaustive candidate research.

Upstream `cc0af8c` made the formerly external collector available at `research/gaza-stance/` during this review. Its ledger contained 231 items, including the six newly held/syndicated records, and omitted the 14 previously published guide observations and six newly accepted/restored items. It is now reconciled to all 245 published items. Missing quarantine history was copied, including one older hold; three Panetta holds retain their originals with resolution metadata (186 historical entries, three resolved).

The merger previously replaced candidate evidence wholesale without checking the repository's quarantine or review history. It now rejects missing/replaced publication records, quarantined sources and invalid dates before writing, retains full summaries and guide observation provenance, and uses the current qualified-write-in field. `--sync-published` copies reviewed manual updates back into the collector and refuses to discard unknown draft items. Its round trip must preserve the entire dataset. One additional [registered context correction](../../research/reviews/gaza-ledger-reconciliation-2026-10-14.json) makes Bachelor GE-0219 explicitly identify the Gaza ceasefire resolution: its old peace quotation alone failed the collector's relevance rule when the ignored source cache was absent.

The collector's date and acceptance regressions pass; a fresh `revalidate_ledger.py --dry-run` retains 245 items with zero hard failures and no new soft flags. Existing soft flags still need human judgment. Collection prompts and deterministic rules were inspected, but no model enrichment or Jev assessment ran. These rules remain filters, not proof of identity or political facts.

## Validation

Run `python3 scripts/build_site.py`, then `python3 scripts/check_release.py` for the complete 19-check offline gate. New finance regression tests exercise mixed spending directions, complete first totals, secret redaction, Git argument boundaries and both reader disclosures. Headless Chromium checked both modified pages at 1440px and 390px, including collapsed disclosures, support/opposition amounts, FEC links and wrapping without clipped spender names. County browsing used San Francisco; this was not a new live address-provider test. Offline checks establish consistency and behavior; they do not certify source truth, live FEC totals or provider availability.
