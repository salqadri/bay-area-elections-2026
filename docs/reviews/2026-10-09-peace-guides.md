# Vote for Peace and AROC Action review — October 9, 2026

This source-specific pass adds **70 recommendation records** and **14 Gaza evidence observations** to the existing five-county elected-office inventory. The published totals are **386 recommendation records on 197 printed candidacies** and **245 Gaza evidence items under 82 candidacies**. All 316 prior recommendation records and 231 prior Gaza items are preserved exactly. Ballot rosters, parties, FEC fields and election-wide research dates are unchanged.

The [review manifest](../../research/endorsements/peace-guides-2026-10-09.json) preserves source identity, retrieved-text hashes, all card dispositions, candidate/office matches, reference checks, note decisions and the exact accepted records. It is a manual review, not an independent audit of every claim made by the guides. Raw retrieval caches remain outside Git.

## Recommendations

| Source | Inspected cards | Published in current roster | Other dispositions |
| --- | ---: | --- | --- |
| [Vote for Peace California](https://voteforpeace.info/california) | 152 | 27 Ally; 8 Opposed | 5 matched Neutral; 112 not matched to current roster |
| [AROC Action](https://arocaction.org/endorsements/) | 44 | 29 candidate endorsements | 5 candidate endorsements outside current roster; 10 ballot measures |

Vote for Peace's methodology distinguishes guide inclusion from formal endorsement. Ally is stored as `relation: supported, rating: Ally` and displayed **Listed as Ally by Vote for Peace**. Opposed is an explicit negative recommendation. Neutral yields no recommendation; substantive Gaza notes can still be retained independently. Jimmy Panetta's source card says primary, so its recommendation remains primary. The other 34 matched recommendations identify the general election.

AROC identifies November 3, 2026. Every candidate endorsement matching an existing printed candidacy is included. The five other candidates are Mai Vang (CD-7), Randy Villegas (CD-22), Angela Gonzales-Torres (CD-34), Isaac Bryan (AD-55) and Sade Elhawary (AD-57). All ten measures are preserved in the manifest, outside the public elected-office inventory. An unmatched endorsement does not create a ballot contest or establish whether someone is on the ballot.

Name variants were checked against office and jurisdiction, including Michael Nguyen / Michael T. Nguyen, Dion-Jay “DJ” Brookter / Dionjay (DJ) Brookter, JR Eppler / J.R. Eppler, and Majdi Gaith / Majdi “Gaith” Abuhamdieh. Multiple endorsements in San Francisco Districts 8 and 10 carry no invented ranks or joint designation.

## Endorsements discovered through the aggregator

Six explicit additional endorsements are published with their provenance:

- Malia Cohen: California Building and Construction Trades Council, California Environmental Voters, GrowSF and California Council for Affordable Housing. Vote for Peace explicitly reports these in her candidate notes. They remain secondary reports associated with its general-election entry, not first-party confirmation.
- Jane Kim: Working Families Party, confirmed in its [January 21 announcement](https://workingfamilies.org/2026/01/wfp-endorses-jane-kim-for-california-insurance-commissioner/). Election phase is unspecified in that announcement.
- Jane Kim: For the People Action, explicitly listed under Organizations on her [campaign endorsement page](https://www.janekim.org/endorsements). This is a campaign claim with unspecified phase.

The [official Track AIPAC list](https://www.trackaipac.com/endorsements) confirms existing general-election endorsements of Connie Chan, Lateefah Simon and Ro Khanna. They are preserved without duplicates. A Track AIPAC badge, generic link, funding claim or omission from an endorsement list cannot establish opposition. Vote for Peace's own Opposed labels remain separate.

CAIR's reviewed official capture still controls its precise labels and phase. Both CAIR and Vote for Peace say Preferred for Peter Ortiz; an erroneous draft review note claiming a conflict was corrected before release. AROC's current list does not confirm the aggregator's Rob Bonta reference. Generic DSA, Working Families Party and For the People source badges without a candidate-specific assertion remain discovery leads rather than invented endorsements.

## Gaza evidence and date meaning

All 40 matched Vote for Peace candidate pages were reviewed. Thirteen substantive issue-specific notes were retained for Xavier Becerra, Steve Hilton, Jane Kim, John Garamendi, Josh Harder, Mark DeSaulnier, Lateefah Simon, Kevin Mullin, Sam Liccardo, Ro Khanna, Zoe Lofgren, Jimmy Panetta and Mia Bonta. AROC's candidate-specific arms-embargo and speech/protest rationale supplies one additional item for Connie Chan.

These sources do not date the underlying statements, contributions or votes. Schema 1.15 introduces `date_method: source_observed` for explicitly attributed voter-guide assessments, with a complete observation date equal to `checked_on`, `source_kind: voter_guide`, and a required explanatory `date_note`. Both readers display **Observed on 2026-10-09 (guide snapshot; original date unknown)**. This does not establish historical chronology or convert an undated candidate statement into a dated event.

Funding and legislative claims remain attributed to the guide. Missing periods, transaction evidence, cosponsorship dates or independently checked roll calls are stated where relevant. These observations are not financial audits. General party platforms, generic corporate-PAC refusals, publisher principles and silence were not converted into candidate-specific Gaza positions. The manifest records each note disposition.

## Verification

The complete README release suite passed: generated-page freshness, data/reference/coverage checks, evidence quarantine, published endorsements, 33 endorsement regressions, 8 CAIR regressions, 5 new peace-guide regressions, schema checks (50 rejected invalid examples and 18 accepted valid examples), and both reader/address-service integration suites. New checks cover exact Ally/opposition wording, observation-date display, phase preservation, missing/unreviewed recommendations, completeness and importer idempotence.

Both generated pages embed the current canonical JSON and schema. All previous records and unrelated contest fields were compared with the published baseline and preserved. UI checks use a minimal DOM, not browser rendering; passing checks establish internal consistency, not source truth or exhaustive coverage.
