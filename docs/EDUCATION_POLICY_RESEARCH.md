# Antisemitism definitions and Israel/Palestine education policy

Publication **2026-10-26.5**, schema **1.26**, adds **129 source-reviewed Gaza
evidence records across 104 active candidacies**. The review covers support,
opposition, authorship, sponsorship, votes, amendments, enforcement and explicitly
labeled nonvotes. It does not equate ordinary opposition to antisemitism or
Holocaust education with a position on Israel/Palestine.

## What the Wiener omission exposed

The current gap collector retained divestment, ceasefire and general Israel
queries but lacked dedicated IHRA/antisemitism-definition/education searches.
Its missing-evidence default could skip candidates who already had some evidence.
The shared Jev state builder also selected only the first twelve Gaza records.
Wiener already had twelve records, so simply appending another record would have
left it outside the model input.

The new topic sweep plans **every active tracked candidacy**, independently of
collector done flags and existing evidence. The generic collector now also uses
`gaza-discovery-v3-education-policy`, retaining the divestment searches and adding
IHRA, AB 715/AB 1468, the Antisemitism Awareness Act and education terms. Topic
changes invalidate its source fingerprint. Search results remain discovery leads.

The schema adds the evidence dimension `antisemitism_education`. The shared
grader places **all** records in that dimension into
`antisemitism_education_policy_evidence`, with dates, qualifications, summaries,
quotes and source URLs. The generic twelve-item budget applies separately.
The CLI state version is `candidate-evidence-v8-education-policy`; the local
playground uses `candidate-evidence-v8-local-federal-education-policy`.

## Bill versions and attributed claims

Wiener's published records now include his principal-coauthor role in AB 715's
September 16 enrolled version, its recorded September 12 Senate action, CAIR
California's June 17 objections, and authorship of the separate introduced
AB 1468 proposal. These dates and roles are not interchangeable.

The chaptered AB 715 text retrieved through CalMatters Digital Democracy does
**not explicitly name IHRA**. Section 1(i) references the U.S. National Strategy
to Counter Antisemitism. The governor's signing announcement describes an
antisemitism coordinator, training and classroom-material enforcement. CAIR's
June article argues that the then-current bill could censor Palestine teaching;
the ACLU separately objects on speech grounds. These objections remain
attributed, rather than becoming a claim that the statute literally adopts IHRA.

AB 1468's February 21, 2025 introduced version specifies a domestic focus for
ethnic studies. LegiScan records that proposal as failed in February 2026. A
coauthor record is not evidence of enactment or a final passage vote.

Federal H.R. 6090 (2024) and H.R. 1007/S. 558 (2025) are separate actions and
versions. H.R. 6090's House Clerk roll call supplies actual Yea/Nay/Not Voting
labels; its GPO bill text supplies the IHRA/Title VI provision. Neither a No vote
nor a nonvote establishes support for Palestine. First-party explanations, where
verified, preserve constitutional or religious-liberty rationales. Sponsorship
is not represented as a roll-call vote or proof of enactment.

## Scope and audit

[The sweep archive](../research/education-policy/sweep-2026-10-26.json) accounts for
all **1,296 candidacies**, **1,288 distinct name queries**, **5,851 search hits**
and **271 selected candidate/source pairs**. All searches used Serper.dev;
there were no failed search requests. Of 195 selected URLs, 160 were captured
and 35 remain unavailable, including inaccessible social posts and documents
requiring separate review. Missing or inaccessible evidence never establishes
neutrality. A bounded search is not a complete career audit.

The five registered `education-policy-*-2026-10-26` reviews retain every proposed
claim, actual Jev response, source packet/hash, exact context and hold. Later
identity bridges can resolve a new claim without erasing the earlier held one.
The source audit additionally preserves
[exact requests and responses](../research/education-policy/source-decisions-2026-10-26.json).
Its `novel`/`uncertain` dispositions are follow-up leads, not published claims.

Name overlap only makes a lead. House votes use the source's state and an
official Clerk full-name/bioguide bridge. California floor actions use the
latest recorded floor action rather than an earlier bill version. Digital
Democracy's `Abstain` category stays a source label; it does not establish a
deliberate abstention or a No vote. Structured-field quotations are labeled
transcriptions, not spoken quotations or independently verified municipal votes.
Official and advocacy accounts retain their source roles.

Jev `jev-1.14.0` is the only judgment model used in this refresh. Identity must
reach 0.90, faithful attribution 0.85 and date provenance 0.90. These are source
verification gates, not candidate score/confidence acceptance criteria. No model
response is rewritten to force acceptance. Date checks receive the explicit
publication/inspection provenance; unrelated page-navigation dates are excluded.

## Repeatable workflow

Use new output directories to preserve observations. Raw captures, credentials
and request caches stay in ignored `.research/`; never commit API keys.

```sh
python3 scripts/research_education_policy.py plan --output-dir .research/education/NEW
python3 scripts/research_education_policy.py discover --output-dir .research/education/NEW/search --serper-key-file /secure/serper-key
python3 scripts/research_education_policy.py triage --discovery .research/education/NEW/search/discovery.json --output-dir .research/education/NEW/triage --jev-key-file /secure/jev-key
python3 scripts/research_education_policy.py capture-leads --triage-file .research/education/NEW/triage/triage.json --output-dir .research/education/NEW/captures --serper-key-file /secure/serper-key
```

Use `research_gaza_gaps.py capture` for shared sources. The replayable capture
kinds `house-rollcall-xml`, `house-members-xml` and
`california-legislation-jsonld` validate source URLs and retain structured
associations. `policy-html` reads explicit publication metadata without changing
older capture formats. `shared_vote_leads()` and `coauthor-leads --packet …`
generate candidate leads; Jev still verifies identity and attributed meaning.

Prepare source-local proposed claims as described in
[the gap workflow](RESEARCH_GAP_RECOVERY.md), retaining actual bill-version,
publication and inspection dates. Supporting captures can establish bill content
or bridge a historical office to the current candidacy. Every supporting excerpt
is checked against replayed raw bytes before a model decision can publish.

```sh
python3 scripts/research_gaza_gaps.py draft --claims /path/to/claims.json --model jev-1.14.0 --jev-key-file /secure/jev-key --work-dir .research/education/NEW/review --id education-policy-YYYY-MM-DD --checked-on YYYY-MM-DD --output research/reviews/education-policy-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py preview research/reviews/education-policy-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py apply research/reviews/education-policy-YYYY-MM-DD.json
python3 research/gaza-stance/merge_gaza_evidence.py --sync-published
python3 scripts/research_education_policy.py audit-sources --discovery .research/education/NEW/search/discovery.json --triage-file .research/education/NEW/triage/triage.json --captures .research/education/NEW/captures/captures.json --output-dir .research/education/NEW/source-review --jev-key-file /secure/jev-key
python3 scripts/build_site.py
python3 scripts/check_release.py
```

## Scores and local review

**No scorecards were rerun.** All 1,296 saved numeric scores, derived grades,
confidence/provenance fields, exact v3 questions, provider responses and frozen
grade explanations remain unchanged. New research does not rewrite a historical
request or automatically publish a new grade.

In the local playground, **Current input** previews the regenerated state for
the next evaluation. **State JSON**, **Full request** and **Answers JSON** retain
the exact saved evaluation. Current input does not submit a request. A future
owner-authorized rerun should use current evidence, then publish the new archive
and refresh explanations from that same archive.

## Verification of this publication

All **44 offline release checks pass**, including source/registry reconciliation,
schema validation, unchanged grade/explanation bindings and the new policy
regressions. Desktop/mobile Chromium checks verify the evidence on both readers
and Current input versus the saved input in the playground, with no page errors
or scoring requests. All 106 preexisting local run files remain byte-identical.
The retained numeric scores, grades, prompts and explanations also match the
pre-refresh dataset exactly. Other candidate, finance and endorsement data is
unchanged. A macOS test-fixture root now resolves `/var` symlinks consistently
with the existing publication path guard; that guard remains unchanged.
