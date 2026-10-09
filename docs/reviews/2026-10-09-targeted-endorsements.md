# Targeted endorsement review — October 9, 2026

The public dataset now contains **236 endorsement/support observations for 156 of 869 printed candidacies**. This update adds 77 reviewed records and removes 725 unsupported prior imports. It covers the existing five-county November roster, not all US candidates or every endorsement organization. The election-wide research date, printed rosters, official party preferences and FEC receipts are unchanged.

## Findings added

| Source / endorser | Records | Meaning and limits |
| --- | ---: | --- |
| [Track AIPAC / Citizens Against AIPAC Corruption](https://www.trackaipac.com/endorsements) | 3 | Explicit November endorsements for Connie Chan (CD-11), Lateefah Simon (CD-12) and Ro Khanna (CD-17). All matches to the current printed roster from this list are captured. The separately linked local guide is a different publisher. |
| [CAIR Action, reported by Blue Voter Guide](https://bluevoterguide.org/endorser-org/CAIR_Action/CA/7054) | 15 | November listings matched to the roster, labeled **reported support**. The [official interactive guide](https://cairactionguide.org/explore) was unreadable. CAIR's [methodology](https://cairaction.org/how-we-developed-our-endorsements/) distinguishes endorsed from preferred; the original tiers remain unknown. |
| [Hindu American PAC](https://www.hinduamericanpac.com/endorsements) | 1 | Melissa Hernandez, CD-14, in Current Endorsements with a 2026 campaign link. Stage is unspecified. Murali Srinivasan's biography still says 2022; Yang Shao's entry concerns Fremont Council rather than his current water-district candidacy. Both are held. |
| [Americans4Hindus / Dr. Romesh Japra, reported by IndiaPost](https://indiapost.com/americans4hindus-extends-support-to-fremont-city-council-candidates-vipin-sharma-and-manisha-pathak/) | 4 | Two organizational endorsements, for Vipin Sharma (Fremont D3) and Manisha Pathak (D4), plus two Japra **support** observations. The September 11 report describes his presentation of the organization's certificates and checks; it does not establish personal donations or separate personal endorsements. |
| [JStreetPAC](https://jstreetpac.org/candidates/) | 10 | Individual profiles explicitly mark Endorsed and identify the House district. The [2026 program](https://jstreetpac.org/jstreetpac-in-2026/) supplies cycle context; primary/general stage remains unspecified. |
| [Jewish Democratic Council of America](https://jewishdems.org/endorsements/) | 2 | Josh Harder and Kevin Mullin. A June 16, 2026 [announcement](https://jewishdems.org/press_release/jewish-dems-endorse-house-senate-and-gubernatorial-candidates/) identifies this as the full 2026 list. |
| [DMFI PAC](https://dmfipac.org/news-updates/press-release/dmfi-pac-announces-major-2026-house-endorsement-slate-backing-pro-israel-democrats-in-must-win-districts-nationwide/) | 3 | Harder, Mullin and Jimmy Panetta in the December 16, 2025 announcement for the **2026 primary**. Current November status is unverified; the present endorsement page could not be fully retrieved. |
| [California Jewish Democrats](https://www.dfi-ca.org/ELECTIONS) | 23 | Positive Support/Strong Support ratings, expressly **not exclusive endorsements**. Ratings belong to the source. Neutral, No Position, In Process and an ambiguous BOE district line are excluded from positive-support records. |
| Regional organizations, named on campaign pages | 6 | BAJC Action claims on [Mer Curry Nuñez](https://www.merforschoolboard.com/endorsements), [Marc Cooper](https://www.marccooperforschoolboard.com/endorsements) and [Boris Lipkin](https://www.borislipkin.com/) pages; JDCBA claims on Mer/Lipkin pages; [Kerry Hillis](https://www.kerryhillis.com/endorsements) names Bay Area Jewish Coalition. Exact labels and campaign-claim provenance are preserved. |
| [Chronicle Editorial Board — actual endorsements page](https://www.sfchronicle.com/projects/2026/california-sf-election-endorsements/) | 10 | Named November candidate recommendations from the editorial list. Coming Soon, ambiguous BOE statements and ballot measures are not candidate endorsements. |

The exact candidacy IDs, names, records, source URLs, check date and qualifications are in [`targeted-2026-10-09.json`](../../research/endorsements/targeted-2026-10-09.json). No inferred political affiliation or candidate stance was added from an endorsement.

## Correction to the prior import

The Chronicle's neutral voter guide describes candidates and opponents across the ballot. The previous import incorrectly treated **723 candidate mentions** as endorsements by its editorial board. Its actual editorial recommendations are on a separate URL. Two additional records named “This website uses cookies.” and “5 LEADERS OF THE COMMUNITY” as endorsers; neither identifies a person or organization.

Those **725 public records** are removed. The corresponding **1,167 observations** in the collector export are quarantined with original IDs, source hashes and a Git-history reference in [`quarantine-2026-10-09.json`](../../research/endorsements/quarantine-2026-10-09.json). The filtered export retains 161 historical observations; the curated additions remain in a separate layer because support ratings exceed the collector's schema. The 159 older public records retained from that export have **not** all received an independent factual audit.

Current totals: 190 formal endorsement observations, 6 recommendations, 40 other support observations. There are 144 candidacies with at least one formal endorsement observation; the broader 156 count includes recommendations and support. County presence counts overlap: Alameda 60, Contra Costa 35, San Francisco 24, San Mateo 22, Santa Clara 81. No published record for the other 713 candidacies means unknown, not no endorsements.

## Research still needed

- Retrieve the official CAIR November tiers and AIPAC PAC's dynamic candidate list. PAC contributions and Track AIPAC funding totals cannot substitute for an endorsement.
- Recheck DMFI's November list and any explicit withdrawal. A historical primary observation is not evidence of continued general-election support.
- Confirm regional campaign claims against official organizational lists. BAJC Action's retrieved guide offered no extractable November choices; JDCBA's retrieved page concerned primary applications. Bay Area Jewish Action is a distinct organization and yielded no readable candidate list.
- Resolve Hindu American PAC's mixed-cycle and wrong-office entries. Previously endorsed officials, candidates outside the five counties and people absent from the November roster remain outside publication.
- Japra searches also found a primary fundraiser for Ethan Agarwal and a Gopal Krishan endorsement-page lead. Neither is on the current November roster. Hosting a meeting or attending a summit alone was not counted as an endorsement. These are source-level follow-ups, not proof of exhaustive personal-support coverage.

## Implementation and validation

Schema 1.13 adds `supported`, source `rating`, `verification` and shared qualification `note_id`. Both pages use one display module and label campaign claims and secondary reports. The collector registry has **14 shared publisher queries** and 42 source URLs; the query cache prevents one search per candidate for these publishers. Discovery guides cannot assert endorsements, aggregators require review, sibling sections lose stale endorsement context, and cookie/category text is rejected.

`apply_endorsement_review.py` reproduces the dated publication idempotently. `check_published_endorsements.py`, also called by `check_data.py`, blocks the quarantined guide even with tracking parameters or a renamed publisher and rejects support ratings mislabeled as formal endorsements. The schema cleanup also removed a pre-existing duplicate coverage property.

Validation passed: both generated pages are current; data/evidence/quarantine guards; 33 endorsement regressions; schema examples including invalid provenance and rating misuse; explorer and ballot DOM integration; and all address transport, autocomplete and matching checks. The DOM checks cover qualifications, source ratings, source links, filtered-download counts and the distinction between Japra support and organizational endorsement. These are deterministic checks, not live browser rendering or proof that all endorsement facts have been audited.
