# Repeatable county research and updates

Use the same pipeline for a county rerun, the nine-county Bay Area or California. Selecting a scope does not add ballot coverage. Official contests and printed rosters must be researched first; every later enrichment uses those stable contest/candidacy identities.

## 1. Plan the scope and identify gaps

```sh
python3 scripts/research_scope.py --county "Contra Costa" --output .research/contra-costa-plan.json
python3 scripts/research_scope.py --county Alameda --county "Contra Costa" --output .research/east-bay-plan.json
python3 scripts/research_scope.py --scope bay-area --output .research/bay-area-plan.json
python3 scripts/research_scope.py --scope california --output .research/california-plan.json
```

The report separates requested counties, counties represented in the inventory and missing counties. It lists unresolved rosters, ballot statuses, endorsement/evidence gaps and unique totals. Shared contests appear once; county totals overlap. An evidence gap is unknown, not a negative finding. County presence is not a completeness certification.

The shared [California registry](../research/california-counties.json) contains county names/FIPS from the [Census Bureau's 2026 table](https://tigerweb.geo.census.gov/tigerwebmain/Files/acs26/tigerweb_acs26_county_ca.html), the [MTC nine-county definition](https://data.bayareametro.gov/dataset/Bay-Area-County-Boundaries/t75i-n3yr) and the [Secretary of State county elections directory](https://www.sos.ca.gov/elections/voting-resources/county-elections-offices). Geography recognition does not enable ballot coverage: the address matcher still requires the county in the election dataset.

For a new county, follow [RESEARCH.md](RESEARCH.md): audit county, municipal, school/college and special-district inventories against official resident-ballot materials; determine June-resolved and canceled contests; reconcile shared offices; verify party/incumbency and candidate identity; record uncertainty explicitly. Refresh federal receipts with their actual coverage dates. The separate external Gaza collector still has its own documented validation/ledger requirements. This workflow does not replace official roster research or imply that external collector is now part of this repository.

## 2. Collect once, cache and resume

```sh
python3 scripts/research_endorsements.py --db .research/contra-costa/ledger.sqlite3 plan --county "Contra Costa"
python3 scripts/research_endorsements.py --db .research/contra-costa/ledger.sqlite3 run --max-queries 50 --max-pages 100
python3 scripts/research_endorsements.py --db .research/contra-costa/ledger.sqlite3 extract
python3 scripts/research_endorsements.py --db .research/contra-costa/ledger.sqlite3 review-packets --output-dir .research/contra-costa/review
python3 scripts/research_endorsements.py --db .research/contra-costa/ledger.sqlite3 status
```

Search requires the collector's existing Serper configuration. `run --no-search` only fetches pages. Browser/search-service results can instead enter through the existing provider-neutral `import` command. Raw responses, keys and caches remain outside Git. Search snippets stay leads. Fetch shared publishers first; the ledger deduplicates each source URL and matches one source against all selected candidacies.

A ledger has one election and one explicit county scope. Replanning that scope preserves completed work and cached pages, and refreshes the current roster. Reusing it for a different scope fails before collecting unrelated work. Use a separate ledger for a different scope. Source caches are shared within a ledger, not automatically across separate county ledgers.

For a long-lived statewide ledger that grows as official rosters are added:

```sh
python3 scripts/research_endorsements.py --db .research/california/ledger.sqlite3 plan --scope california --allow-partial-scope
```

The requested scope remains all 58 counties; missing inventories are explicitly reported. Without `--allow-partial-scope`, a requested but unresearched county is an error. Run `plan` before using an older ledger to record its scope metadata. County discovery queries use the selected counties, even when a selected statewide candidate also appears in other counties.

To refresh an existing county, rerun its identical `plan`, then use the collector's existing age/budget controls:

```sh
python3 scripts/research_endorsements.py --db .research/contra-costa/ledger.sqlite3 run --refresh-days 7 --retry-failed --max-queries 50 --max-pages 100
```

A failed fetch or omitted name never deletes a published observation. Source content hashes and review decisions remain available for comparison. No scheduled automation is installed by these commands.

## 3. Normalize source observations and draft a review

`reviewed_updates.py` is the common publication path for endorsements, Ally/Preferred/Opposed classifications and candidate-specific Gaza evidence from any publisher. Collection/export alone never publishes.

Give a source adapter this small contract:

```json
{
  "sources": {
    "guide": {
      "url": "https://example.org/guide",
      "publisher": "Example Organization",
      "role": "endorser",
      "checked_on": "2026-10-09",
      "retrieval": "rendered_text",
      "content_sha256": "replace with the SHA-256 of the actual captured content"
    }
  },
  "cards": [
    {
      "id": "stable-source-card-id",
      "source_key": "guide",
      "name": "Name as published",
      "office_context": "Exact office, jurisdiction and district from the source",
      "label": "Original source label",
      "phase": "unspecified",
      "notes": "Relevant source notes; do not invent missing text"
    }
  ]
}
```

The example is a format illustration, not a real source or importable endorsement. Preserve every source card, including unmatched candidates, Neutral labels and measures. A candidate-specific URL should have its own source entry. Use each source's actual capture date; a later review date or roster match does not refresh it. Publisher roles are `endorser`, `aggregator`, `campaign` or a descriptive secondary-source role. A campaign source also names its `candidate`.

The existing CAIR parser output is accepted directly, including its captured source hash, labels and annotations:

```sh
python3 scripts/import_cair_guide.py parse /path/to/capture.html --checked-on 2026-10-09 --output .research/cair-capture.json
python3 scripts/reviewed_updates.py draft --capture .research/cair-capture.json --id cair-county-refresh-2026-10-09 --reviewed-on 2026-10-09 --county "Contra Costa" --output research/reviews/cair-county-refresh-2026-10-09.json
```

For other publishers, pass their normalized capture to the same `draft` command. `--aliases` accepts the collector's reviewed full-name aliases keyed by stable candidacy ID. Name and office matching supplies suggestions only. **Every draft decision remains `hold`**, including exact matches. A CAIR “Also in Primary” annotation does not set the recommendation's election phase.

## 4. Review exact changes and preview the delta

For each accepted decision, retain its source-card ID, source observation and concrete reason. Set `action: change`, the matched `position_id`/`candidate`, and the suggested `identity` object (office, jurisdiction, district/seat, term, election type). Choose `field: endorsements` or `gaza_evidence`. Set:

- `before: null` for a new observation, or the entire exact current record for a replacement/removal.
- `after` to the complete new record, or `null` for an explicitly justified removal. Missing/inaccessible source text is not a removal reason.
- `evidence.identity_basis`, `evidence.date_basis` and `evidence.relationship_basis` (endorsements) or `evidence.issue_basis` (Gaza) to concrete source-supported explanations.
- `notes` to new shared provenance notes keyed by unused stable IDs. Existing note meanings cannot be overwritten.

Preserve the public schema's relation, rating, phase, verification and note rules. A publisher's own statement must match the verified source publisher. A campaign claim must match its campaign. Aggregator source badges alone do not establish third-party relationships; explicit reported endorsements remain `reported`. Oppositions belong to that candidate and never imply support for another. Undated guide assessments retain `source_observed` with the actual observation date and explanatory note; they do not date historical votes, contributions or statements. Historical quarantine remains enforced.

```sh
python3 scripts/reviewed_updates.py preview research/reviews/cair-county-refresh-2026-10-09.json --output .research/proposed-elections.json
```

The preview leaves maintained inputs unchanged and reports added/replaced/removed/unchanged/held counts and shared contests affected. It rejects stale before values, office mismatches, out-of-scope changes, ID/source conflicts, unsupported provenance, invalid dates and known quarantined sources. It validates the proposed full dataset and recomputes the two enrichment coverage metrics. Ballot rosters, parties, FEC and global freshness dates are outside this importer's write scope.

## 5. Apply, validate and publish

```sh
python3 scripts/reviewed_updates.py apply research/reviews/cair-county-refresh-2026-10-09.json
python3 scripts/build_site.py
python3 scripts/check_release.py
git diff --check
git diff --stat
```

Apply validates before writing, preserves unrelated records, and registers the manifest's content hash in [publication-reviews.json](../research/publication-reviews.json). An identical rerun makes no further changes. After registration, a review is immutable: add a new dated review to supersede it. Each replacement/removal requires the exact previous record and a new reason. Publication guards project the original CAIR/peace-guide baselines through this ordered history, so new evidence can revise a dated assertion without weakening the guard. Dated legacy importers become validation-only once updates are registered, preventing old captures from overwriting newer research.

Keep the canonical dataset, review manifest, registry, updated coverage documentation and rebuilt pages together in the commit. Review the diff and follow existing publishing authorization. The full offline gate writes `.checks/release-checks.json` and `.checks/release-checks.log`; it neither researches nor deploys. Verify the Pages deployment for the exact commit separately. Passing checks establishes internal consistency, not official ballot accuracy or exhaustive source coverage.

## Extending the process

Add source adapters that emit the common capture contract; reuse county selection, identity matching, review decisions, provenance/date validation and publication guards. Keep source-specific parsing outside the common application logic. Preserve all dispositions and raw-source hashes. Prefer reusable fixture regressions for a newly discovered failure class over a new dated import script. Test a county rerun, a shared contest, a new Bay Area county and a non-Bay-Area California county before claiming broader portability.
