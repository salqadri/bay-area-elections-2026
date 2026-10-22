# Ballotpedia endorsement supplement — October 22, 2026

Prepared against `8b484e3` (publication `2026-10-22.2`). Proposed publication
`2026-10-22.3`; schema stays **1.23**. This branch supplements the campaign
collector with explicitly current-cycle candidate-profile endorsement sections.
It does not claim exhaustive coverage or infer endorsement absence from a failed
request. Hermes reviewed and merged the PR; this report describes the branch's
proposed changes as published.

## Published-data changes

**200 secondary-source records on 54 printed candidacies**: 103 endorsements and
97 voter-guide recommendations. All additions retain `phase: unspecified`
because their own source categories did not establish a phase with sufficient
probability. Each has the exact named source entry, a Ballotpedia section link,
`verification: reported`, the actual observation date, and provenance note N1542.
Existing campaign/official observations remain intact.

There are **167 accepted corroborations** retained in the review audit without a
second displayed row. **857 parsed rows remain held** (411 candidate/relationship
threshold holds, 40 possible duplicates, 406 unresolved entity overlaps), plus
**47 source-layout fragments** in publication-eligible sources. A hold is not a
finding that an endorsement is false.

Total printed endorsement coverage becomes **544 of 1,294 candidacies**, with
**24,484 relationship records** (previously 516 candidacies / 24,284 records).
The changes are additive. A structural comparison removed exactly these 200
additions and their new note, restored only the publication/coverage metadata,
and recovered the complete baseline dataset. Ballot rosters, provisional filers,
finance snapshots, platforms and Gaza records are preserved.

## Mike Rogers example

[Mike Rogers's Michigan profile](https://ballotpedia.org/Mike_Rogers_(Michigan)#Endorsements)
has 12 entries in its 2026 section. Its 2024 and older notable-endorsement
sections are excluded. The original readable HTML was observed on October 22
at `17:40:59+00:00`; a later empty/challenge retrieval is not substituted for it.
The collector imported that saved page with its actual timestamp and canonical
URL. The regression fixture records the original hash and exact section excerpt.

His displayed total changes **1 → 8**:

- Donald Trump: existing campaign claim retained once, Ballotpedia corroboration
  recorded without a duplicate.
- Seven added endorsements: John Barrasso, Tim Scott, John Thune, Jack Bergman,
  Tim Walberg, Karen Whitsett, Michigan Farm Bureau AgriPAC.
- Four guide entries held: Dinner and a Ballot Review, FlintTown, Misfits M.A.G.A.
  P.A.C.K., Questionable Bipartisanism. Three fail the relationship threshold;
  Misfits passes that threshold as a recommendation but fails the distinct-entity
  threshold. These are not silently converted into formal endorsements.

## Collection scope and limits

The inventory covers **1,389 tracked candidacies**, including 95 provisional
local filers outside the common publication scope. There are 940 recorded
profile bindings representing **934 unique URLs**; every unique URL was
attempted. No profile discovery or search service was called.

- **236 readable captures**: 142 have current-cycle sections; 94 have none.
- **698 unavailable URLs**: empty/challenge responses, including HTTP 200
  responses without readable article content. These remain retry/import queues.
- Of the 142 section packets, **140 are publication-eligible** and reviewed;
  two stay outside publication scope.
- Those 140 packets contain **1,224 parsed entries**. Their dispositions sum to
  200 additions + 167 corroborations + 857 holds.
- 449 tracked candidacies have no recorded profile, including 87 outside the
  publication scope; the eligible missing-profile queue therefore contains 362.

Neither an unavailable page nor a missing current section proves no endorsements.
The collector preserves unsupported tables/prose and ambiguous linked rows as
layout holds. It does not execute challenge scripts. Previously saved readable
HTML can be imported with the actual observation timestamp and canonical URL.
The workflow is resumable and uses Python's standard library.

## Systematic safeguards

The parser follows the heading hierarchy and explicit election year. It handles
year subsections, nested categories and citation links, and distinguishes the
polling-chart presentation heading "Change over time" from a new election cycle.
The named source anchor supplies the endorser spelling; source rows, category
context, intro, links and hashes remain in the evidence packet.

**Jev `jev-1.13.0` is the sole judgment model.** Candidate/office/year identity
needs a selected probability of at least 0.85; endorsed/recommended relationships
need 0.80; explicit primary/general phase needs 0.90. Otherwise phase stays
unspecified. A general-ballot introduction or neighboring primary-results table
cannot phase an endorsement. Explicit distinctions and opposition/withdrawal
categories are held independently of model confidence.

A shared exact identity/relationship guard deduplicates across source URLs in
both the new collector and future campaign attachments. Explicit primary/general
and historical/current contexts remain separate. Fuzzy spelling only creates a
Jev identity question; it never authorizes a merger. Every otherwise-new entity
also receives an all-name Jev screen against compatible preexisting observations
and curated publisher names, catching acronym/legal-name variants without shared
tokens. Exact/fuzzy duplicate checks include earlier accepted additions in the
same draft. Unresolved overlap is held. This is not a retroactive cleanup of
unrelated legacy records.

Official CAIR/peace-guide/support-rating controls remain protected. The campaign
collector's existing CAIR-control comment is now backed by an explicit CAIR
Action exclusion, alongside the existing curated exclusions.

Drafting reconstructs source-bound model requests, checks captured bytes and
current candidacy bindings, and requires exactly one disposition per parsed
entry. Missing/stale/tampered evidence fails. The common `reviewed_updates`
workflow registers exact changes; applying the identical review again is a no-op.
No existing record is removed because it disappeared from a secondary page.

## Evidence and reproduction

- [Reusable workflow](../BALLOTPEDIA_ENDORSEMENTS.md).
- [Immutable review](../../research/reviews/ballotpedia-endorsements-2026-10-22.json)
  and [candidate/coverage audit](../../research/reviews/ballotpedia-endorsements-2026-10-22.audit.json).
- [Portable archive](../../research/endorsements/ballotpedia-2026-10-22/archive.json):
  236 normalized source packets, 140 reviewed result packets, 1,001 actual Jev
  request/response objects, collection manifest/status, and design decisions.
  The archive binds the review SHA-256
  `12b594c9d797a75086458251b36d8267f89ddcae67a0508e2e0724b31356fbfa`.
- [Mike source fixture](../../research/endorsements/ballotpedia-fixtures/mike-rogers.json).

From a clean clone, run `plan`, bounded `fetch` or `import-capture`, `extract`,
`review`, `draft`, `archive`, then common review preview/apply as documented.
Use a fresh review ID/output path for a new pass. Raw HTML and resumable caches
stay under ignored `.research/`; credentials stay outside the repo. The committed
normalized archive supports inspection of this review without credentials or live
pages. Re-fetching may produce different source content or availability and must
create a new observation, not overwrite this review's evidence.

## Validation

- All **30 release checks pass**, including **28 new offline regressions** for
  cycle/phase parsing, actual Mike section extraction, provenance/binding,
  duplicate controls, curated/relationship holds, failure preservation and
  immutable portable archives.
- Reapplying the registered review returns `already_applied: true`.
- The baseline structural comparison confirms exactly 200 additive records on
  54 candidacies and preservation of all other dataset records.
- Real Chrome checks at **1440px and 390px** pass on both readers: Mike shows
  eight entries, Trump once, seven secondary-report Ballotpedia links; Alex Lee's
  address-reader disclosure shows its seven new source-linked records. No page
  errors or horizontal overflow. Screenshots were visually inspected.
- The browser pass uses manual county selection and blocks external requests;
  it does not certify live geocoding, Ballotpedia availability or source truth.
