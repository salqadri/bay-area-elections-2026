# Missing X profiles — October 22, 2026

Baseline: `87bbe2c` (merged/published PR #11, publication `2026-10-22.3`).
Proposed publication **2026-10-22.4**, schema **1.23** unchanged.

## Becerra finding and cause

The tracked candidacy is **Xavier Becerra, California Governor**, position
`CA2026-014`. Its recorded [campaign website](https://www.xavierbecerra2026.com)
links directly to [XavierBecerra](https://x.com/XavierBecerra), including header
and footer social links labelled "Follow on twitter". The capture contains three
occurrences of the same profile. Optional retrieved profile metadata names
Xavier Becerra and describes him as a candidate for Governor, former HHS
Secretary and California Attorney General, with location Sacramento, CA.

The recorded campaign-page capture was observed at
`2026-10-22T23:34:30+00:00`; metadata at `2026-10-22T23:35:25+00:00`.
Jev's selected probabilities were **0.95 candidate identity** and **0.98 account
ownership**. This is an account-identity check, not a verified-badge claim.

The missing link is a collection coverage gap:

1. The old local helper's `find_x` in
   `research/gaza-stance/xhunt2.py` searches X results and tries at most three
   profile leads. It does not extract social self-links from the campaign page
   found by the separate `find_site` step. It also accepts only exact profile
   result URLs, so indexed post URLs do not become profile leads.
2. The later `research/federal_2026/discover_links.py` does inspect campaign-page
   X links, but reads the nationwide `draft_positions.json` scaffold, limits its
   scope to Senate/governor additions, and skips every already-present ledger
   key even when its X value is null. It is not a current all-office repair pass
   and does not revisit California's existing gubernatorial record. Its
   profile-service dependency can also suppress otherwise useful linked evidence.
3. Becerra's existing source S691 records the October 7 campaign-site discovery;
   it does not establish that his missing X field was ever checked against those
   campaign self-links. Historical per-candidate X search results are not
   retained here, so the precise result/service failure in that original search
   cannot be reconstructed. The code and scope gaps above are directly visible;
   no account absence should have been inferred.

## Systematic recovery and actual scope

The new [workflow](../X_PROFILES.md) inventories current missing fields at all
office levels and follows recorded campaign URLs. It uses no search service and
no guessed handles. Jev is the sole judgment model; a recorded Jev policy decision
selected this source-backed, additive approach over a manual-only or blind fix.

Before the pass: **1,294 eligible printed candidacies, 435 with X links, 859
missing X links**. Of the missing entries, **301 have recorded campaign URLs**
representing **299 distinct sites**. Every one of those 299 sites was attempted.

| Outcome | Count | Interpretation |
| --- | ---: | --- |
| Readable campaign pages | 258 unique sites | Source capture, not ownership approval |
| Unavailable pages | 41 unique sites / candidacies | Explicit retry queue |
| Pages with direct profile links | 25 | 26 unique linked handles including a vendor lead |
| Readable optional profile metadata | 24 of 26 handles | Third-party corroboration only |
| Added profile links | 11 candidacies | Jev identity/ownership gates passed |
| Identity holds | 8 candidacies | Page/campaign/office identity insufficient |
| Ownership holds | 6 candidacies | Own-account evidence insufficient |
| No profile link in captured page | 235 candidacies | Not evidence of no account |
| No recorded campaign site | 558 candidacies | Outside this first-party retrieval pass; not searched |

The candidate dispositions sum to **859**. Printed X coverage becomes
**446 of 1,294**. Secondary accounts remain **10**, campaign URLs remain **653**.
The pass checks homepages as recorded; it does not exhaust linked subpages,
JavaScript-rendered content, search engines, or candidates without recorded sites.

Added accounts:

| Candidate | Office | X handle |
| --- | --- | --- |
| Todd Achilles | U.S. Senate | Achilles4Idaho |
| Xavier Becerra | California Governor | XavierBecerra |
| Jonathan Kreiss-Tomkins | Alaska Governor | jktforak |
| Sonja Shaw | Superintendent of Public Instruction | realSonjaShaw |
| Elizabeth Bracco | City Council | Bracco4council |
| Mindy Ruth Pechenuk | Mayor | MindyForOakland |
| Matthew "Matt" Avery | City Council | matt4pinole |
| Reena Gupta | City Council | reena4ptown |
| James Maes | Mayor | maes4mayor2026 |
| Armando "Gary" Ferraris | Mayor | GaryMayor2026 |
| Laurance Lee | Board of Education | lauranceleesf |

The holds include generic/vendor/organization leads such as `wix`, `candidate`
and `midpenopenspace`; the script does not treat every linked handle as the
candidate's own account. Existing primary/secondary accounts are preserved.

## Audit and validation

The self-contained [immutable review](../../research/x-profiles/2026-10-22/review.json)
contains all 299 page outcomes, normalized captured page/anchor evidence,
optional metadata and hashes, the 25 actual Jev classification requests/responses,
all 859 candidate dispositions, the design decision, and exact baseline/post-state
hashes. The review file SHA-256 is
`39c692d12e8120f4088578f1fa50a095edaded6dfba44201c8d43d9f84c64e39`.
It excludes raw HTML/API captures and credentials. Source IDs S1494–S1504
are attached to the 11 additions with dates, capture hashes and review ID.

The link adapter has a dedicated scalar-field review path because common
`reviewed_updates.py` handles structured research records. Applying the review
reconstructs source-bound questions and dispositions without network access,
requires its exact baseline, validates schema, and appends only missing links and
source provenance. Reapplying its exact post-state is a no-op.

All **31 release checks pass**. The **21 new offline regressions pass**, including
source/model binding and failed-service cases. Real Chrome at **1440px and 390px**
passes for Becerra's link in both readers, with no page errors or horizontal
overflow; screenshots were visually inspected. Exact review reapplication makes
no dataset change. The structural
comparison removes exactly the 11 new links/source references and new sources,
restores coverage/publication metadata, and recovers the entire baseline dataset.
No existing campaign/X link, endorsement, finance amount/date, roster, platform
or Gaza record changes. Browser checks use manual county selection and block
external requests; they do not certify live geocoding or account availability.
