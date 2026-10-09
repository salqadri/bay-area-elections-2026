# CAIR Action source correction — October 9, 2026

The public dataset replaces **15 secondary CAIR reports** with **95 recommendations from a supplied capture of [CAIR Action's official Explore page](https://cairactionguide.org/explore)**. Both the explorer and address page preserve **Endorsed by**, **Preferred by** and **Opposed by**. The recommendation stays on the corresponding candidate, including negative recommendations.

| Public CAIR relationship | Matched candidacies |
| --- | ---: |
| Endorsed | 76 |
| Preferred | 18 |
| Opposed | 1 |
| Total | 95 |

Examples: John Garamendi (CD-8) is **Preferred**, Rudy J. Rodriguez (Franklin-McKinley School District) is **Preferred**, and Marc Cooper (the same district) is **Opposed**. Cooper's separate campaign-claimed BAJC Action endorsement remains distinct. Endorsements do not change official party preference or establish a candidate's stance on an issue.

## Source and completeness

The supplied HTML contains **200 recommendation cards**: 156 Endorsed, 40 Preferred, 3 Joint Endorsement and 1 Oppose. All are preserved in the [review manifest](../../research/endorsements/cair-action-2026-10-09.json), including office, source card ID, original spelling, level, annotations and review disposition. Source capture SHA-256: `654899eec980485db160179cca128b9634abd6f3b7e64dda10edc8c6f48e47cf` (517,776 bytes). Raw HTML is not committed.

| Card disposition | Count | Meaning |
| --- | ---: | --- |
| Published | 95 | Matched candidate and office in the current printed roster |
| Duplicate | 2 | Repeated Peter Ortiz and Gordon Chester cards, same recommendation and district despite leading-zero formatting |
| Held: office mismatch | 1 | Tomara Hall, described below |
| Not in current roster | 102 | No matched printed candidacy; includes outside-scope candidates and unresolved local roster leads |

The 102 unmatched cards remain available for future roster research. They are not evidence that the candidates are off ballot, and endorsement material alone cannot establish or create a November contest. No captured joint endorsement matched the current roster; schema and readers nevertheless preserve that distinction for future verified matches.

Name variants were reviewed against office and jurisdiction, including Shirley Weber/Shirley N. Weber, Malia Cohen/Malia M. Cohen, Majdi Gaith/Majdi "Gaith" Abuhamdieh, Johnny Reyna/Johnny Ray Reyna and Rudy Rodriquez/Rudy J. Rodriguez. Every applied match is explicit in the manifest; the importer performs no fuzzy matching.

**Held discrepancy:** source card 4165 says Tomara Hall, San Jose Unified School Board, District 1. The current `CA2026-170` roster and [her campaign](https://www.votetomarahall.com/) identify Area 2; her [endorsements page](https://www.votetomarahall.com/endorsements) did not establish a CAIR recommendation. Preserve the original card and resolve the district discrepancy before adding a public record.

**Retrieval and phase limits:** the Explore page could not be independently re-fetched. The [linked NorCal PDF](https://cairaction.org/wp-content/uploads/2026/05/NorCal-Voter-Guide.pdf) exceeded the browser reader's size limit (48.9 MB); direct download returned HTTP 403. The PDF was not read. All new labels come from the supplied official-page capture. Its selected-election header is absent; “Also in Primary” and special-election annotations are preserved without guessing which phase was selected. Public records therefore use `phase: unspecified`, with visible provenance note `N295`. October 9 is the review date, not an endorsement announcement date. The PDF upload path supplies neither a phase nor an announcement date.

## Publication and maintenance

Schema **1.14** adds `preferred` and `opposed`, requiring provenance and an explanatory note, and supports `shared: true` only for an endorsement. Both readers use the same display module. Candidate lists explicitly identify opposition in their expandable summary as well as the individual record. Coverage counts indicate record presence, including opposition, not positive endorsements.

Total published coverage is now **316 records on 190 of 869 printed candidacies**: 266 endorsed, 18 preferred, 6 recommended, 25 supported and 1 opposed. Of these candidacies, 176 have at least one `endorsed` observation. County presence counts overlap: Alameda 72, Contra Costa 38, San Francisco 32, San Mateo 28 and Santa Clara 86. Missing records for the other 679 candidacies mean unknown. The 159 retained older records have not all been independently audited.

`scripts/import_cair_guide.py` parses a capture without network/model calls, then applies only explicitly reviewed matches. The combined dated migration skips superseded secondary CAIR findings, preserves the earlier quarantine, replaces the CAIR layer idempotently and updates coverage. The publication guard verifies every reviewed recommendation's presence, source, relationship and qualification; accidental omissions or polarity changes fail validation. See [the workflow](../ENDORSEMENTS.md) before refreshing the source.

The election-wide research date, candidate rosters, party labels, FEC records, Gaza evidence and every other publisher's records are unchanged. The [earlier publication audit](2026-10-09-targeted-endorsements.md) remains the history for other sources and quarantines.

## Verification

The release checks cover generated-page freshness; dataset, evidence and endorsement guards; collector and capture regressions; schema valid/invalid examples; explorer and address-page DOM behavior; and all address transport, autocomplete and matching checks. The CAIR cases exercise level preservation, duplicate handling, unresolved phase, the district hold, secondary-source rejection, omission detection, polarity protection and idempotent imports. A semantic comparison confirms no changes to non-CAIR candidate records or election facts. These checks establish internal consistency, not completeness of the election inventory or independent authentication of the supplied capture.
