# Fresno local candidate research — November 3, 2026

PR #23 is **unmerged and not deployed**. The owner requested this research after
finding that the county import had added ballot rosters and empty-state grades,
without candidate enrichment. Roster completeness was not research completeness.
This source pass supersedes the earlier review's “enrichment remains future
work” and “all 222 new candidates are N/A” descriptions for the candidates below.

## Coverage and results

The bounded pass covers **all 80 named county/city candidates**, plus **four
contested Superior Court candidates**, in **37 local contests**. The Huron
write-in-only contest has no printed candidate to research. School/college and
special-district candidates are outside this follow-up's scope.

- **353 Serper discovery queries**, plus one government-identity follow-up;
  **384 source URLs requested**, **315 readable** and 69 unavailable after retries.
- **70 Ballotpedia profiles, 24 campaign URLs and three X profiles**, verified
  against actual captured pages: 97 added links on 73 candidacies.
- **105 quoted general policy points for 20 candidates** and **64 endorsement
  observations for 10 candidates**. General policies and ordinary endorsements
  do not by themselves establish a Palestine stance.
- **Four CAIR Action endorsements** from its current general-election guide:
  Maria Pacheco, Naindeep Singh, Joaquin Arambula and Ariana Martinez Lott.
- **Four issue observations for three candidates**: Pacheco's ceasefire action,
  Karbassi's Iran-war comments, and two distinct Arambula AB 715 vote stages.
- **79 of these 84 candidates remain N/A**. No religion is inferred from names,
  and missing evidence is not a neutral, positive or negative position.

Search snippets were leads only. Qwen (`qwen/qwen3.8-27b`, LM Studio, medium
reasoning, temperature .2, concurrency 2) proposed facts from 66 captured campaign
pages. Literal quotation/context checks and separate Jev source decisions gated
publication. Campaign claims remain `campaign_claim`; Ballotpedia relationships
remain `reported`; CAIR's own guide is `endorser_statement`. Duplicate or unclear
entities, reverse endorsements and unsupported quotes are held in the audits.

## Findings and source cautions

- [KVPR](https://www.kvpr.org/local-news/2024-03-29/kerman-becomes-second-valley-city-to-call-for-gaza-ceasefire-mayor-says-matter-goes-beyond-politics)
  reports that **Maria Pacheco introduced Kerman's proclamation in February 2024
  and voted for it in March**. It calls for an immediate, permanent ceasefire,
  hostage release and civilian aid. The publication date is not the meeting date.
- [ABC30](https://abc30.com/post/fresno-council-member-karbassi-speaks-iran-attacks-isnt-war-is-rescue-mission/18670160/)
  reports **Mike Karbassi's personal support for U.S.-Israeli military action in
  Iran**, calling it a rescue mission. This is not labeled a Gaza ceasefire vote
  or a city-council resolution.
- [CalMatters Digital Democracy](https://calmatters.digitaldemocracy.org/bills/ca_202520260ab715)
  records **Joaquin Arambula's May 2025 Aye** at Assembly third reading and
  **September 2025 Abstain** on Senate-amendment concurrence. Both are preserved,
  with month precision because the structured timestamps do not state timezone.
  These are his prior Assembly votes, not Fresno City Council votes. Different
  bill stages/versions are not collapsed into a single position.
- **Gary Yep's reported abstention remains held**: the source identity gate
  stayed below .90, including after an official Kerman council-page identity
  bridge. Its exact questions/answers are preserved in `held-gary-review.json`.
  It is not published as a No vote or used to grade him. A news report listing
  public demands at Clovis council, without a named response/vote, likewise
  does not establish the candidates' positions.

The CAIR endpoint currently returns a PDF. Page 28 has a candidate card above
the ballot-measure section; the prior parser rejected the mixed page. The
systematic fix parses only candidate cards above the geometry-bounded measures
heading, rejects ambiguous/crossing layouts and never imports measures as
candidate endorsements. The complete source has 246 candidate cards. A scoped
refresh added only the four relevant Fresno observations; other candidates'
CAIR records were not changed. PDF bytes remain in the ignored collector cache.

## Evaluations and recommendations

Five affected candidates were re-evaluated using the **unchanged preferred
owner prompt v11**, bounds **.74 / 1.4 / 2.3 / 3.3 / 4.4**, minimum evidence
**.22**, and the issue-observation guard. Confidence is retained; there is no
confidence acceptance cutoff for published grades. Source-review identity and
assertion gates are separate data-quality controls, not grade acceptance rules.

| Candidate | New grade | Score / 5 | Evidence / 1 |
|---|---:|---:|---:|
| Maria Pacheco | A | 4.95 | .99 |
| Naindeep Singh | A | 4.90 | .90 |
| Joaquin Arambula | B | 4.40 | .93 |
| Ariana Martinez Lott | A | 4.87 | .86 |
| Mike Karbassi | F | .21 | .38 |

Current prepared archive: `research/gaza-grading/published-2026-11-03-fresno-local-research.json`,
ID `jev-2026-11-03-fresno-local-research`. All **1,513 other evaluation rows**
remain exact, including all 1,296 pre-Fresno rows. Prior archives are immutable.
Distribution: **A 122 · B 47 · C 21 · D 34 · E 84 · F 122 · N/A 1088**.
Five actual single-candidate run envelopes are registered in portable history.
The saved local editor/history is not overwritten.

Four previously uninformed Fresno races now recommend **Pacheco (CA2026-466),
Singh (476), Arambula (477) and Martinez Lott (478)**. Their Qwen paragraphs were
reviewed: Pacheco's introduction/vote dates were corrected and process boilerplate
removed, with original outputs and exact editorial changes retained in
`narrative-review.json`. Campaign redirects resolving to the same final URL are represented once in the
platform page list; no policy point or scoring input changed. Registered issue
evidence is also mirrored into the collector ledger, so later merges preserve it.

The prior **539 maintained race rows**, including the
owner's 179 approved selections/paragraphs and Aisha correction, stay exact.
Total selected races: **183**.

The five new candidate-grade explanations are queued separately for Hermes at
`research/gaza-grading/explanation-queue-2026-11-03-fresno-local-research.json`.
No old candidate explanation was regenerated or relabeled. The research-site
and TALL **local previews** consume the updated data and plan together; neither
production site is changed by this work.

## Artifacts and repeatable process

- `research-manifest.json`: every candidate's queries, source availability and
  explicit disposition. Search result URLs are leads, not evidence assertions.
- `links-review.json`: exact Jev link decisions, literal Person-profile markers,
  actual source hashes, before/after values and chosen source IDs.
- `qwen-proposals.json`: exact research proposal requests/responses and timings.
- `current-jev-states.json`: current inputs for all 84 candidates, explicitly
  separate from saved evaluations; preserves the playground's identity wrapper.
- `score-refresh.json`: five exact changed request bindings and four race IDs.
- Five registered `fresno-local-*` reviews (including the mechanical redirect-page correction) under `research/reviews/`, plus
  `research/endorsements/fresno-ballotpedia-2026-11-03/` for the existing
  Ballotpedia collector's portable source/decision archive.

Start future county enrichment with an explicit local inventory, then collect
shared guides and source pages before grading:

```sh
python3 scripts/local_candidate_research.py --county Fresno --output .research/fresno-local-plan.json
python3 research/gaza-stance/merge_gaza_evidence.py --sync-published
python3 scripts/check_local_candidate_research.py
python3 scripts/check_fresno.py
python3 scripts/check_release.py
```

`review_local_campaigns.py --help` documents the resumable campaign-proposal
review adapter. It requires literal captured source text, exact source hashes,
explicit scope and actual model answers; it drafts only. Inspect the review and
use `reviewed_updates.py preview/apply` separately. Existing Ballotpedia and CAIR
collectors are reused. All searches must use Serper.dev. Keep credentials, raw
HTML and working histories outside Git. [County workflow](../../../docs/REPEATABLE_RESEARCH.md).

## Verification

**55/55 offline release checks PASS** on the final dataset. The schema suite
still validates all 754 real records and rejects the same 55 malformed examples,
with 21 positive cases; representative mutation fixtures avoid repeating the
entire inventory traversal for every example. Both research readers rebuild
exactly. Desktop/mobile Chrome checks pass for the TALL county filter, accepted
existing picks, new Pacheco grade/tag/links, evidence and endorsement drawers,
and responsive layout, with no page errors. The normal preview suite emits no
analytics requests. `validation.json` binds the checks to the final dataset hash.
The standalone TALL checkout remains clean; only ignored staging files changed.
