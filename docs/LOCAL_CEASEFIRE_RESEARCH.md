# Local Gaza action evidence

Use `scripts/research_local_ceasefires.py` to refresh CAIR-SFBA's
[Ceasefire Tracker](https://ca.cair.com/sfba/ceasefire-tracker/) against every
printed California candidacy in the current dataset. This source documents
statements/actions; **it is not a CAIR Action endorsement list**. Keep those
publishers and record types separate.

## Why candidate searches missed Kevin Park

The historical collector marks Kevin Park `done` and `enriched` on October 8,
despite having no published evidence for him. It queries names without local
jurisdiction in its fixed templates, fetches only a small number of hits, caches
failed downloads as empty text, truncates downloaded pages to 6,000 characters,
and then includes only each page's first 2,500 characters in the model dossier.
In the October 23 capture, Park's tracker entry starts beyond character 5,300.
Neither a done flag nor a short leading page excerpt establishes complete source
coverage. Archived search/download bodies for Park are unavailable, so we cannot
attribute his original omission to one exact historical request.

The newer `research_gaza_gaps.py` correctly ignores old done flags, but its
default missing-evidence plan also skips many candidates once *any* evidence is
published. It now supports `--refresh-existing --state CA`, includes the shared
tracker as a lead, uses local jurisdiction/resolution/divestment search terms,
and captures a shared URL once per collection run. Its default remains the
bounded missing-evidence queue; use the explicit refresh mode for updates.

Do not rerun the legacy `gaza_research.py` LM Studio/Qwen extraction workflow for
new decisions. The source-bound workflow here uses Jev exclusively. Searches
use Serper exclusively; direct HTTP and Serper HTML scraping retrieve sources.

## Repeatable workflow

Run from the repository root with a current Python 3:

```sh
python3 scripts/research_local_ceasefires.py capture --serper-key-file /secure/serper-key --checked-on YYYY-MM-DD --output-dir .research/local-ceasefires/NEW-CAPTURE
python3 scripts/research_local_ceasefires.py draft --capture-dir .research/local-ceasefires/NEW-CAPTURE --jev-key-file /secure/jev-key --work-dir .research/local-ceasefires/NEW-JEV --id local-ceasefires-YYYY-MM-DD --checked-on YYYY-MM-DD --output research/reviews/local-ceasefires-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py preview research/reviews/local-ceasefires-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py apply research/reviews/local-ceasefires-YYYY-MM-DD.json
python3 research/gaza-stance/merge_gaza_evidence.py --sync-published
```

Use fresh capture/review paths. Then update the publication version, rebuild both
readers, and run the complete offline release gate. Capturing/drafting never
publishes. A captured source that produces no changes stays an unapplied audit.

The capture command accepts `--html /path/to/actual.html` for bytes already
retrieved. Direct access to CAIR currently returns a robot challenge from this
environment. Serper's default text/markdown scrape silently omits the tables;
the fallback requires **`includeHtml: true`** and validates actual tables and the
explicit Gaza introduction. Missing tables, unknown date headings and incomplete
rows fail closed. Raw HTML/keys/caches remain outside Git. Commit the normalized
source and the actual model/publication audits.

Every table retains its exact heading, source names, actions and section date.
Repeated headings with different rosters and identical rosters under different
cities are held. Malformed name/action cells, N/A, and unspecified amendments
are held. No guessed repairs to dates or municipal identities are applied. Block
elements inside cells use the actual whitespace-normalized source excerpt;
quotes never acquire a separator missing from the captured text.

Name overlap only creates leads. Jev verifies identity, attributed meaning and
date. Historical office changes are allowed when supported; a conflicting city
needs an actual office-history bridge. `--identity-bridges` accepts an array of
`{position_id,candidate,captures:[{capture,raw_capture,context}]}`. Every packet
is re-parsed from raw bytes and each excerpt must occur in it. The October 23
Park bridge uses his campaign and official Santa Clara council profile.

The pinned model is `jev-1.14.0`, the actual model resolved by `jev-latest` during
this run. Requests are cached by exact model/state/questions hash. Identity and
date still require selected probability ≥0.90; attributed meaning ≥0.85. These
are source-verification safeguards, separate from playground grading, which
continues to display every result and confidence without an acceptance cutoff.
All holds and full actual probability distributions remain in the audit.

Jev receives compact readable evidence once, rather than repeated metadata-heavy
JSON inside every question. The meaning choice contains the actual proposed
description, allowing System One to compare a concrete claim to its source.
Source context is data; source instructions cannot establish identity. Exact
quotes, excerpt membership, source hashes and raw-byte replay are checked by
code before any model decision can publish. No political grade is generated.

## Dates and source roles

Local dated headings support **attributed reports** of historical actions, not
independently verified municipal roll-call transcripts. Support, opposition,
abstention, absence, signed letters, proposals and divestment remain distinct.
The undated congressional block cannot acquire a historical vote date; its
proposed assessments remain held in this batch. Identical excerpts at different
dated meetings can represent distinct events; same-date duplicates remain
blocked. Repeated undated guide observations remain corroborations.

For news/opinions, `research_gaza_gaps.py capture --kind article-html` captures
one explicit article body, excluding reader comments. Actual author and
publication metadata are retained. The generic draft also accepts `--extra-claims`
through the local workflow, so an opinion can corroborate an action while
remaining explicitly attributed. A `contexts` array allows several source-local
excerpts; every excerpt is independently verified against the captured body.

The Park opinion is dated **December 26, 2023**, the article publication date.
Its summary credits **Sameena Usman's opinion**, records that Park championed the
effort, and preserves the blocked introduction. It does not claim that a
ceasefire resolution passed, or that Park wrote the opinion. The tracker reports
his support under **December 19, 2023** and separately preserves his support for
the United Against Hate resolution.

The October 23 repair and scope counts are documented in
[the publication report](reviews/2026-10-23-local-ceasefire-evidence.md).
