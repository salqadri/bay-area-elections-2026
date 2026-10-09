# Candidate endorsement research

`scripts/research_endorsements.py` collects current-cycle endorsement evidence for **every printed candidacy in the election JSON**, including nonpartisan races. It keeps a separate SQLite research ledger and exports normalized JSON with [its own schema](../research/endorsements/endorsements.schema.json). It does not modify the main dataset, candidate party preferences, or the website. Unknown candidate rosters cannot be researched until names are available.

The collector uses Python's standard library. Optional `pdftotext` supports text PDFs. It makes no LLM, Jev or Research-agent calls. Serper supplies search results; direct HTTP retrieves pages. A provider-neutral import path also accepts browser or other search-service lookups.

## Minimize agent work

1. Fetch shared endorser lists first. Each page is matched against the entire roster, so one union or party list can resolve many candidates.
2. Search each candidacy once with name, office and cycle, plus county-wide discovery queries across Democratic and Republican parties, labor, business, educators, environmental groups and media. Party affiliation never limits candidate coverage. The five starter URLs are seeds, not a representative or complete inventory of endorsers.
3. Cache searches and content snapshots. Follow real endorsement links on campaign sites. Repeated URLs are fetched once per refresh and repeated extraction skips unchanged inputs.
4. Read the grouped review packets in Hermes's main context. Register verified source publishers and reviewed name aliases, then rerun extraction to resolve whole pages at once. Handle clear rejects from the supplied excerpts without new research.
5. Use a Research sub-agent only when a packet needs a missing page, OCR, identity verification or additional evidence. Combine issues from the same source into one lookup task, import its result, then rerun extraction. Do not dispatch one research task per candidate.

On the October 9 baseline, a fresh plan contains **869 candidacies, 904 search queries and 386 initial source URLs**. `--deep` adds one targeted query per candidacy. These are request counts, not a promise of complete results, cost or duration; discovered pages add fetches. A modest first batch lets Hermes inspect coverage before committing a larger budget.

## First live run status (October 9, 2026)

Collection through this date is **complete**: 904/904 searches, 3,671 pages parsed, ~2,780 explicit fetch failures (bot-walled platforms and junk hosts; each stays checkpointed as a limitation), 1,328 accepted observations from 9 verified endorsers / 10 registered sources. Published: endorsements on **741 of 869 printed candidacies** in the election dataset (schema 1.12) plus the snapshot `research/endorsements/endorsements-export-2026-10-09.json`. A final drain pass changed nothing — re-extract/export/re-attach is byte-identical, so do not rerun collection expecting new signal from plain HTTP.

Next-value work: (1) browser/provider **imports** for bot-walled but credible sources (Ballotpedia candidate pages, Facebook/Instagram endorsement posts) via `import`; (2) targeted follow-up on the ~128 uncovered candidacies; (3) bulk reject-by-source for the ~27.6k pending review items from low-quality hosts after confirming they are not endorsers — record decisions with reasons, never delete packets silently.

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

`assertion` can be `endorsements`, `recommendations` or `mixed`. Use `mixed` for pages combining positive endorsements, negative recommendations, or unclear categories. An endorser page asserts the publisher's position; it does not establish that every organization it mentions endorsed every candidate. Search discoveries start unverified. Do not promote a page based on its search snippet alone. Campaign URLs already in the candidate data receive `campaign` provenance; verify that they remain the candidate's site before publication.

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
