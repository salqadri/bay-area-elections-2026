# Candidate endorsement research

`scripts/research_endorsements.py` collects current-cycle endorsement evidence for **every printed candidacy in the election JSON**, including nonpartisan races. It keeps a separate SQLite research ledger and exports normalized JSON with [its own schema](../research/endorsements/endorsements.schema.json). It does not modify the main dataset, candidate party preferences, or the website. Unknown candidate rosters cannot be researched until names are available.

The collector uses Python's standard library. Optional `pdftotext` supports text PDFs. It makes no LLM, Jev or Research-agent calls. Serper supplies search results; direct HTTP retrieves pages. A provider-neutral import path also accepts browser or other search-service lookups.

## Minimize agent work

1. Fetch shared endorser lists first. Each page is matched against the entire roster, so one union or party list can resolve many candidates.
2. Search each candidacy once with name, office and cycle, plus county-wide discovery queries across Democratic and Republican parties, labor, business, educators, environmental groups and media. Party affiliation never limits candidate coverage. The registered URLs are seeds, not a representative or complete inventory of endorsers.
3. Cache searches and content snapshots. Follow real endorsement links on campaign sites. Repeated URLs are fetched once per refresh and repeated extraction skips unchanged inputs.
4. Read the grouped review packets in Hermes's main context. Register verified source publishers and reviewed name aliases, then rerun extraction to resolve whole pages at once. Handle clear rejects from the supplied excerpts without new research.
5. Use a Research sub-agent only when a packet needs a missing page, OCR, identity verification or additional evidence. Combine issues from the same source into one lookup task, import its result, then rerun extraction. Do not dispatch one research task per candidate.

On the October 9 baseline, a fresh plan contains **869 candidacies, 904 search queries and 386 initial source URLs**. `--deep` adds one targeted query per candidacy. These are request counts, not a promise of complete results, cost or duration; discovered pages add fetches. A modest first batch lets Hermes inspect coverage before committing a larger budget.

## Current publication and correction — October 9, 2026

The initial run completed 904 searches and parsed 3,671 pages, but completion was not a factual audit. Its 741-candidacy/884-record publication claim was inflated: 723 records came from a neutral Chronicle candidate directory, and two more named a cookie notice and a section heading as endorsers. These 725 public records and their 1,167 collector observations are now quarantined with stable IDs and original snapshot hashes. The old export has been filtered; its original contents remain in Git history.

The corrected publication now contains **316 records under 190 candidacies**. The [earlier audit](reviews/2026-10-09-targeted-endorsements.md) added 77 reviewed records. The [CAIR correction](reviews/2026-10-09-cair-action-correction.md) replaces 15 of those secondary reports with 95 official-page recommendations. The remaining 159 older records are retained, not certified as independently audited. Missing evidence for 679 candidacies remains unknown.

The collector export and curated layers are deliberately separate: the collector schema does not express every public support relationship. Public schema **1.14** supports `endorsed`, `preferred`, `opposed`, `recommended` and `supported`, with source ratings, provenance and shared notes. `shared: true` applies only to a joint endorsement. Both readers display the relationship explicitly; an opposition stays in the corresponding candidate's list as **Opposed by**, never as an endorsement or as support for an opponent. The legacy `printed_candidates_with_endorsements` coverage key counts presence of any recommendation, including opposition. DMFI primary announcements remain primary. Japra's documented presentation of organizational checks is not a claim of a personal donation.

### CAIR Action: preserve the official recommendation levels

Use [the official Explore page](https://cairactionguide.org/explore). Its reviewed [capture manifest](../research/endorsements/cair-action-2026-10-09.json) records all 200 supplied cards, their exact level and office, cross-election annotations, source hash, retrieval limits and explicit match decisions. This produces **76 Endorsed, 18 Preferred and 1 Opposed** records. Two duplicate cards are collapsed, one district mismatch is held, and 102 cards have no match in the current printed roster. Unmatched cards are research leads, not proof that the candidate is off ballot. Do not create or alter ballot races from endorsements alone.

The official page could not be independently re-fetched. The [linked PDF](https://cairaction.org/wp-content/uploads/2026/05/NorCal-Voter-Guide.pdf) could not be read and contributes no inferred labels. The supplied HTML fragment omits the selected-election header. Its “Also in Primary” annotations do not establish the selected phase, so public records say `unspecified`; the shared note explains the provenance. A retrieval date or a PDF upload path is not an endorsement announcement date.

For a new complete capture, first extract its cards without model calls:

```sh
python3 scripts/import_cair_guide.py parse /path/to/capture.html --checked-on YYYY-MM-DD --output .research/cair-cards.json
```

Then review the new capture against the current roster, one source pass for all candidates. Give every card a disposition and concrete reason; explicitly record name variants, exact office/district, duplicates and holds. Update the dated manifest, provenance note and publication expectations intentionally before applying. The reviewed manifest is the reproducible evidence layer; raw HTML stays outside Git.

```sh
python3 scripts/import_cair_guide.py apply
python3 scripts/check_cair_guide.py
python3 scripts/check_published_endorsements.py
python3 scripts/build_site.py
```

The apply command composes the existing publication correction with the CAIR replacement and recomputes coverage. The guard verifies all reviewed recommendations are present with the correct relationship and official URL; it rejects reverting to Blue Voter Guide or changing an opposition into an endorsement. Older CAIR secondary findings remain marked superseded in the historical manifest and cannot be reimported by the dated migration. To refresh this source later, update the manifest and its tests with the new evidence rather than disabling the guard.

### Refresh the requested publishers without per-candidate agent calls

The seed registry now includes Track AIPAC, CAIR Action, Hindu American PAC, JStreetPAC, JDCA, DMFI PAC, California Jewish Democrats, regional groups and Japra/Americans4Hindus leads. Fourteen shared publisher queries are planned once across the roster; they reuse the existing search cache. Each fetched page is matched against all candidates. Read the `followups` in the curated layer before spending requests on blocked or historically ambiguous sources.

```sh
python3 scripts/research_endorsements.py plan
python3 scripts/research_endorsements.py run --max-queries 14 --max-pages 60 --workers 4
python3 scripts/research_endorsements.py extract
python3 scripts/research_endorsements.py review-packets
```

Those budgets prioritize new shared queries in an existing completed ledger; in a fresh ledger other discovery work also exists. Re-fetch a source only when its age or a concrete unresolved question justifies it. Resolve all candidates on that source in one pass. Dynamic CAIR/AIPAC pages may need one browser lookup each; Hindu American PAC's older biographies need office/cycle clarification. Do not schedule a broad enrichment run or one Research-agent invocation per candidate.

Extractor version 2 invalidates the old extraction cache when `extract` runs. Neutral guides (`role: discovery`) cannot generate endorsements. Aggregators (`role: aggregator`) require review of the actual endorsing organization. Support tiers and mixed-cycle lists use `assertion: mixed`. Sibling sections no longer inherit an endorsement heading, and cookie/category labels are rejected. Registered metadata is not a substitute for reviewing accepted observations.

To reproduce this dated publication layer after inspecting the current roster:

```sh
python3 scripts/apply_endorsement_review.py
python3 scripts/check_published_endorsements.py
python3 scripts/build_site.py
```

The apply command removes quarantined imports, applies the curated findings and reviewed CAIR capture idempotently, and updates coverage. It refuses newer conflicting review records or changed note meanings. Do not use this dated migration to override future research; update its manifest intentionally. `check_data.py` also runs the publication guard, including query/tracking variants of the rejected guide. Raw local SQLite observations are not automatically deleted: reconcile them using the quarantine IDs before exporting again. Future integrations must preserve campaign/report provenance, rank, shared endorsements and personal-capacity notices; if the public schema cannot express a qualification, hold the record until it can.

## Run and resume

From the repository root:

```sh
python3 scripts/check_endorsements.py
python3 scripts/research_endorsements.py plan
# Supply SERPER_API_KEY through the environment or a local secret manager.
python3 scripts/research_endorsements.py run --max-queries 100 --max-pages 200 --workers 4
python3 scripts/research_endorsements.py extract
python3 scripts/research_endorsements.py review-packets
python3 scripts/research_endorsements.py export
python3 scripts/research_endorsements.py status
```

Alternatively, `run --serper-key-file /secure/path/serper-key` reads a key without putting it in a command argument. Never commit keys. `run --no-search --max-pages 200` retrieves already planned pages without Serper. A fresh all-query pass can use `--max-queries 904`; page budgets are independent. Re-run `run` for pending work, then `extract` and `export`. `--retry-failed` retries failures explicitly; `--refresh-days 7` refreshes older searches/pages within the same budgets. An access block checkpoints progress and stops the batch.

The default ledger, snapshots, packets and export are under ignored `.research/endorsements/`. Preserve that directory on Hermes's machine for resumability. `--db /path/to/ledger.sqlite3` goes **before** the subcommand. Do not run two commands against the same ledger simultaneously. A process lock prevents this; after a crash, confirm that no collector process is running before removing its `.lock` file. Use a separate ledger for another election.

Re-run `plan` after roster/source changes. Candidacy IDs combine contest ID and normalized candidate name; two contests involving the same person remain separate. Removed candidacies are excluded from exports, while evidence history is retained. Old cached queries remain in the ledger, so a long-lived ledger's planned query count can exceed a fresh plan.

## Publisher verification and aliases

[sources.json](../research/endorsements/sources.json) contains reviewed starter sources. Add verified pages there, or use a separate file with `plan --seeds path.json`. Every source has a URL and metadata:

```json
{"sources":[{"url":"https://example.org/2026-endorsements","publisher":"Example Organization","role":"endorser","kind":"organization","assertion":"endorsements"}]}
```

`role` distinguishes `endorser`, `campaign`, `aggregator`, `discovery` and `unverified`; only a verified endorser or campaign can produce automatic claims. `assertion` can be `endorsements`, `recommendations` or `mixed`. Use `mixed` for pages combining positive endorsements, negative recommendations, or unclear categories. An endorser page asserts the publisher's position; it does not establish that every organization it mentions endorsed every candidate. Search discoveries start unverified. Do not promote a page based on its search snippet alone. Campaign URLs already in the candidate data receive `campaign` provenance; verify that they remain the candidate's site before publication.

For confirmed name variants, create a JSON object keyed by exported candidacy ID, with arrays of full-name aliases, then run `plan --aliases path.json` and `extract`. This explicitly replaces the alias map; ordinary replans preserve it. First/last-name approximations only create review leads. Never resolve a common-name collision without office and jurisdiction evidence.

## Browser and alternative-provider imports

Use newline-delimited JSON, one lookup per line. Example page lookup:

```json
{"type":"page","url":"https://example.org/2026-endorsements","observed_at":"2026-10-09T00:00:00+00:00","provider":"browser","format":"text","partial":true,"content":"The actual retrieved page text, including office and election headings."}
```

Replace the example timestamp with the actual UTC retrieval time; future or timezone-free timestamps are rejected. Use `format: "html"` for actual HTML. Mark truncated/browser excerpts `partial: true`; retain headings and nearby qualifiers. Plain text may supply `links` and `image_labels`; those are discovery/review leads. Optional `meta` follows the verified source rules above. Imported text must be fetched source content, not an agent's paraphrase or unsupported summary. Never turn search snippets into page evidence.

Search imports use:

```json
{"type":"search","query":"the exact query","candidate_ids":[],"observed_at":"2026-10-09T00:00:00+00:00","results":[{"title":"Result title","link":"https://example.org/2026-endorsements","snippet":"Search excerpt, used only as a lead."}]}
```

Use exported candidacy IDs for candidate-specific searches; shared discovery queries use an empty array. To satisfy a planned query, preserve its exact query text. Fetch its result pages separately.

```sh
python3 scripts/research_endorsements.py import .research/lookups.jsonl
python3 scripts/research_endorsements.py extract
python3 scripts/research_endorsements.py review-packets
```

Image-only flyers, dynamic pages, paywalls and complex tables require browser/OCR review. A failed fetch or incomplete excerpt does not establish absence of endorsements. Do not bypass access controls.

## Review packets and decisions

`review-packets` writes a manifest and source-grouped packets, bounded to 24,000 serialized characters by default. Read only files in the current manifest. They include candidate/office references, reasons, source excerpts, snapshot IDs and truncation flags. `lookup_needed` packets combine failed fetches by URL. Pages with clear evidence need no agent invocation, but accepted results still need a publication audit.

Apply a JSON array of decisions using `apply-review path.json`. Each decision needs `review_id`, `snapshot_id`, `action` (`accept`, `reject`, `needs_source`), `reviewed_by` and a concrete `reason`. For an acceptance, include a `record`:

```json
{
  "candidate_id":"C-<ID from packet>",
  "endorser":"Exact endorser name",
  "endorser_kind":"organization",
  "relation":"endorsed",
  "phase":"general",
  "cycle":2026,
  "verification":"endorser_statement",
  "evidence":{
    "quote":"Source excerpt explicitly establishing the endorsement",
    "context":"Source excerpt identifying the candidate and office/district",
    "cycle_quote":"Source excerpt establishing the election year and stage"
  }
}
```

This is a shape example, not an acceptable fabricated record. Quotes must match cached source text, allowing punctuation/spacing normalization. A source quote containing a year is only a mechanical gate: the reviewer must ensure it refers to this endorsement's cycle, not a footer or an unrelated election. `needs_source` records the unresolved decision; it does not automatically spawn work. Decision batches are atomic and stale snapshots are rejected. Reversing an acceptance removes that reviewed claim; history remains in SQLite.

Allowed endorser kinds: `party`, `union`, `organization`, `media`, `person`, `unspecified`. Provenance: `endorser_statement`, `campaign_claim`, `reported`. A first-party statement requires a verified publisher; a campaign list remains a campaign claim. Optional `rank` is a positive integer; `shared` and `titles_for_identification_only` appear only when true. Individual endorser names are source-scoped to avoid silently merging different people.

## Meaning of the export

- `candidates` includes every printed candidacy, with contest reference, evidence IDs, lookup counts and explicit research status. `exhaustive` is always false. Empty evidence means unresolved or nothing verified in the searches performed, never “no endorsements.”
- `endorsers` and `sources` are shared registries. `records` link the candidacy, endorser and source snapshot, with evidence, cycle, phase and provenance. Organizations use exact normalized names; the script does not attempt fuzzy organization merging.
- `endorsed`, `recommended` and `withdrawn` are separate relations. Primary endorsements remain primary; they are not silently carried forward to November. Conditional carry-forward statements need specific review.
- Ranked/shared endorsements and personal-capacity notices are preserved. Questionnaires, appearances at a forum, donations, job titles and opposition to an opponent are not endorsements.
- `observed_at` is the source check time, and `first_observed_at` is when that content version was first seen. Neither is an announcement date. A page's disappearance or removal of a name is not an explicit withdrawal.
- `current_source_version` means the record comes from the latest captured version of that URL. It does not certify the endorsement remains active. `source_refresh_failed` exposes unsuccessful rechecks; older records remain available. `conflicts` flags current endorsement/withdrawal observations for the same candidate, endorser and phase; resolve these before presenting an active endorsement list.

`export` copies the schema beside its JSON. The dataset fingerprint hashes canonical JSON, not raw file bytes. Review this separate layer before intentionally integrating it into the election schema and both generated pages. Keep raw captures and intermediate exports out of Git unless a separately reviewed publication artifact is requested.

## Verification and limits

Run `python3 scripts/check_endorsements.py` for offline regression checks. These cover identity/office matching, cycle/stage, recommendations/opposition, ranked/shared lists, campaign provenance, snippet rejection, cache/resume, history, review validation and collection failure handling.

The [live test report](reviews/2026-10-09-endorsement-collector-test.json) records a five-source browser-import test. Direct Serper/page HTTP was blocked in the development environment; the Serper request contract was fixture-tested, not live-verified. Imported pages were partial excerpts, so this is an extraction test, not exhaustive candidate research. Complex markup and name variants intentionally leave review work. The regression suite is not a complete JSON Schema validator or an independent factual audit.
