# Maintaining the explorer

The October 22, 2026 schema 1.23 update adds the California state campaign-finance layer (CAL-ACCESS receipts and independent expenditures; see [the refresh section](#california-campaign-finance-refresh)). The guide also includes the October 17 schema 1.22 update: neutral `endorsement_images`, a separate `distinction` relationship, external image URLs with no copied assets and the [deterministic image workflow](ENDORSEMENT_IMAGES.md). The guide also includes the October 17 schema 1.21 update (nationwide Senate/governor contests: empty-county records and any-state OCD identifiers; previous layers: 1.20 general campaign platform positions October 16, 1.19 Gaza records October 15). Inspect current code before relying on a fixed provider layer, snapshot count or version.

## Development setup

Use Git, Python 3 and Node.js. No npm packages, Python packages, framework, database, build service or API key are required for the current app. The handoff checks ran with Python **3.12.14** and Node **24.19.0**. Python 3.10+ and Node 18+ are reasonable starting environments, not a tested compatibility matrix; use the checked versions if compatibility is uncertain.

```sh
git clone https://github.com/salqadri/bay-area-elections-2026.git
cd bay-area-elections-2026
git status --short
python3 scripts/build_site.py --check
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/` and `/ballot.html`. Stop the server with Ctrl+C. On systems where Python is named `python`, substitute that executable. The explorer also opens as a standalone HTML file; use HTTP for browser debugging. Address requests need internet access and remain separate from the local server.

For an existing clone, inspect local changes and `git fetch origin` before rebasing or pulling. Do not overwrite local work or assume this handoff commit is still the branch head. Ordinary Git/SSH authentication on the maintainer's machine is sufficient for repository pushes when that identity has access.

## File ownership and data flow

| Maintained file | Responsibility |
| --- | --- |
| `2026-11-03_Bay_Area_Elections.json` | Canonical researched records, code maps, source/note registries, coverage and finance metadata |
| `elections.schema.json` | Draft 2020-12 contract for the inventory; the dataset's `schema_version` const is authoritative |
| `src/index.template.html` | Explorer markup, shared CSS, inline explorer logic and download behavior |
| `src/ballot.template.html` | Address page markup and extra CSS |
| `src/address-services.js` | Census JSONP transport, input/result checks, timeout and cancellation |
| `src/address-suggestions.js` | Photon fetch adapter, complete-address filtering and provider backoff |
| `src/address-autocomplete.js` | Accessible combobox interaction, debounce, cancellation and manual fallback |
| `src/address-matcher.js` | Geography normalization, inclusive race matching, union of ambiguous matches |
| `src/endorsement-display.js` | Shared endorsement, preference, opposition and support wording, provenance and source-rating labels |
| `src/finance-display.js` | Shared dated FEC receipts and independent-spending disclosure in both readers |
| `src/gaza-evidence-display.js` | Shared Gaza disclosure with separate publisher grades, congressional source actions, reviewed platform checks and web/social/guide evidence |
| `scripts/sync_gaza_records.py` | Capture the tracker and official grade feed; draft or locally apply exact reviewed candidate changes |
| `scripts/research_campaign_platforms.py` | Plan bounded website checks and produce held source packets/results for Hermes; no automatic political decision or publication |
| `scripts/research_campaign_issues.py` | Extract general campaign platform positions from the shared crawl cache via the local model under mechanical quote gates; import re-gates without a model. Publication stays with build_review + reviewed_updates |
| `src/platform-display.js` | Shared collapsed "What they stand for · Campaign platform" disclosure (topic chips, summaries, verbatim quotes, source links, reviewed pages) in both readers |
| `src/ballot-page.js` | Form orchestration, warnings, candidate/race display and estimate export |
| `scripts/build_site.py` | Embeds the dataset, schema where applicable, shared CSS and JavaScript into both pages |
| `scripts/prepare_dom_fixture.py` | Parses built pages into disposable DOM fixtures for Node integration checks |

`index.html` and `ballot.html` are generated and committed. The first embeds the dataset and schema; the second embeds the dataset and address modules. Both are self-contained except for remote address services invoked by user interaction. Shared style changes in the index template also affect the ballot page. Preserve the build's `<` escaping for embedded JSON and its rejection of closing-script sequences in inline JavaScript.

The downloaded address estimate uses **`bay-area-ballot-estimate/v1`**, not the inventory schema. It carries geography, confidence-tagged races and shared metadata, including the Gaza action registry and USCPR provenance needed to interpret candidate records, and deliberately omits raw addresses/coordinates. If its shape changes, treat it as a separate format contract; a dedicated schema is a possible improvement, not something already provided.

## Normal change workflow

1. Inspect the current branch, source files and relevant evidence. Use a branch or isolated worktree when concurrent work warrants it.
2. Edit maintained sources. For research, follow [RESEARCH.md](RESEARCH.md); the builder does not discover races or update counts.
3. Recompute `coverage` after data edits; inspect the metric definitions in `scripts/check_data.py`. Update dated prose and limitations only as justified by the changed evidence.
4. Run `python3 scripts/build_site.py` whenever a data/schema/template/module source changed.
5. Run the checks below. For UI or provider changes, also perform browser checks where the environment allows them.
6. Review `git diff --stat`, `git diff --check` and the source/data diff. Inspect unexpected generated churn. Commit the related source and generated files together.
7. Publish as authorized and verify the deployment. Report unresolved issues honestly.

Allocate source/note/contest IDs after synchronizing with other work. Two researchers must not independently claim the same next ID; separate patches can be reconciled before merging. Do not renumber existing records to make the JSON prettier.

## Verification commands

Run from the repository root, in this order:

```sh
python3 scripts/build_site.py --check
python3 scripts/check_data.py
python3 scripts/check_evidence.py
python3 scripts/check_published_endorsements.py
python3 scripts/check_endorsement_images.py
python3 scripts/check_endorsements.py
python3 scripts/check_ballotpedia_endorsements.py
python3 scripts/check_cair_guide.py
python3 scripts/check_peace_guides.py
python3 scripts/check_research_workflow.py
python3 scripts/check_schema.py
python3 scripts/check_fec_money.py
python3 scripts/check_gaza_ledger.py
python3 scripts/check_campaign_platforms.py
python3 scripts/check_platform_positions.py
python3 scripts/check_uscpr_scorecard.py
python3 scripts/check_gaza_voting_records.py
python3 scripts/check_gaza_records.py
python3 scripts/prepare_dom_fixture.py
node scripts/check_endorsement_display.cjs
node scripts/check_finance_display.cjs
node scripts/check_gaza_display.cjs
node scripts/check_platform_display.cjs
node scripts/check_explorer.cjs
node scripts/check_address_services.cjs
node scripts/check_address_suggestions.cjs
node scripts/check_address_autocomplete.cjs
node scripts/check_address_matcher.cjs
node scripts/check_ballot_page.cjs
```

`python3 scripts/check_release.py` runs this complete 30-check offline sequence and records its results under `.checks/`. This command must be run after the final data/build; the list is not a claim that a particular pending PR has already passed.

The fixture preparation must follow the build and precede the two page integration checks. `.checks/` contains disposable fixtures/reports and is ignored. The build's `--check` does not repair stale HTML. Do not use Python's `-O` option; these checks rely on assertions.

| Check | What it establishes | What it does not establish |
| --- | --- | --- |
| Build check | Generated pages equal current sources | Browser appearance or external availability |
| Data check | IDs/references, omission rules, global counts, FEC conventions and embedded inventory agree | Source truth, URL validity, correct geographic eligibility or exhaustive coverage |
| Schema check | Current schema keywords and positive/negative examples pass the repository's focused validator | Full standards compliance; use a standard Draft 2020-12 validator with format checking for interoperability |
| Finance checks | Official aggregate pagination/scope, exact UDP reconciliation, legacy-cache rejection, failure preservation, direction separation, safe Git push arguments/redaction, receipts metadata and disclosure output | Live FEC totals or an actual authenticated push |
| Gaza source and display checks | Complete reviewed sheet dimensions/values/colors, distinct official grade periods, candidate/source bindings, publication snapshots and shared UI sections | Independent verification of every legislative description/value, exhaustive career history or source-assigned political assessments |
| Campaign platform checks | Bounded collection, exact packet/capture/identity bindings, state-specific held decisions and no silent publication | Completion of the deferred candidate-site pass, political meaning or complete-site exhaustiveness |
| Explorer/ballot checks | Real embedded scripts work in a minimal DOM harness with fixture responses | Layout, real keyboard/browser event behavior or live geocoding |
| Service/autocomplete/matcher checks | Parsing, timeout/abort, rate handling, uncertainty, unions and regression cases | Live provider response shapes, CORS, uptime or actual district correctness |

Finance behavior uses fixed synthetic regression cases for unknown, zero, dated totals and mixed-direction spending. Page integration expectations derive current amounts and dates from the embedded dataset, with local-noon date formatting so the checks also work in America/Los_Angeles. Existing fixtures intentionally contain some known names, record IDs, seat counts and a five-county selector count. Research updates can make those expectations stale. Determine whether the changed evidence or a code defect caused a failure; update the fixture with a reason, rather than replacing precise checks with unconditional success.

Browser review should cover desktop and narrow screens, keyboard-only autocomplete, selected and manual addresses, multiple/no matches, outside-scope addresses, API failure, county fallback, expand/collapse, direct links and both downloads. Use public civic-building addresses across the covered counties and compare returned geography with current official maps. Do not store a user's residential address in fixtures. Document the browser/date/endpoints and which scenarios were actually exercised.

## Provider and boundary assumptions

- Census uses `Public_AR_Current` / `Current_Current`, JSONP and numeric layers in `src/address-services.js`. These are mutable service configurations. Consult the linked official metadata before changing or trusting them for another election.
- The matcher recognizes `120th Congressional Districts`/`CD120` and `2026 State Legislative Districts - Upper/Lower`. Schema fields also fix the congressional session and state-legislative vintage. Do not narrow November 2026 House races using 119th-Congress geography.
- The matcher has a five-county California FIPS map and a regular-election assumption for odd-numbered state Senate districts. New counties, special elections or another election year require deliberate review.
- A Census incorporated place can establish a city boundary; a mailing city cannot. Preserve the distinction between `BASENAME` and `NAME`: stripping `City` from an already-normalized name broke Foster City, Union City, Redwood City and Daly City before a regression fix.
- An unresolved local district keeps plausible alternatives. `countywide_electorate` is an explicit researched assertion, not a shortcut for anything associated with a county. Shared Board of Equalization or appellate districts must be checked when coverage expands.
- Photon autocomplete uses a US house-address filter, Bay Area preference, minimum four characters, 750 ms debounce, at least one second between request starts, cancellation and backoff. It only fills the address field; do not substitute its coordinates for verified election geography without a separately reviewed matching change.
- The public Photon demo permits limited project use and has no availability guarantee. Keep attribution and manual fallback; assess a supported hosted service or a dedicated instance if traffic grows. Do not silently remove rate limits.

Google Civic endpoints are documented in `address_lookup` for a future integration; the published site does not call them and contains no Google API key. Any integration must use current official docs, an authorized credential, the correct election ID when needed, and verified election-year boundaries. A generic division response is not automatically a certified final ballot. Preserve the current fallback and privacy behavior when changing providers.

## Expanding to nine counties

The remaining Bay Area counties are Marin, Napa, Solano and Sonoma. For each addition:

1. Research resident ballot coverage and local final rosters, not only geographic intersections. Inventory cities, county offices, schools/colleges, special districts and judicial contests as well as federal/state offices.
2. Add the county to `election.counties_in_scope`. Reuse a shared contest's stable ID and extend its `counties` only when evidence supports it; keep separate terms/seats separate.
3. Update the matcher FIPS map, official county-election URL map, fallback text mentioning five counties and any hardcoded template county lists. Most dropdowns derive from the JSON, but verify both pages.
4. Check OCD geography, boundary vintage and every `countywide_electorate` assertion for newly listed counties. Do not assume an existing BOE district or appellate district covers all nine.
5. Recompute coverage, revise limitations, refresh fixtures and test positive, negative and unresolved address matches for the new county. Rebuild both HTML pages.

## GitHub Pages publication

Repository: `salqadri/bay-area-elections-2026`. Pages publishes **`main` / root**; `.nojekyll` is committed. The entry points are `/index.html` and `/ballot.html`. There is no custom application server or repository-authored CI workflow at this handoff.

Review status/diff, commit the intended files, then push or merge under the current task's authorization. Pushing `main` changes the public site. Use normal fast-forward collaboration; do not force-push away another maintainer's work. Confirm the Pages build/deployment corresponds to the new commit and succeeds. When network access permits, open both published pages and check the modified behavior. A successful Pages build alone is not a live provider test.

Keep credentials, private addresses and `.checks/` out of Git. `.gitignore` already excludes `.env` files, Python caches and `.venv`. No application secrets are required by the current build. If a secret is exposed, remove it and rotate it; deleting the current file does not remove it from Git history.


## Evidence release guard and model-review preparation

Schema 1.20 adds the separate `platform_positions` record (general campaign-authored policy points; see [CAMPAIGN_PLATFORMS.md](CAMPAIGN_PLATFORMS.md)) alongside schema 1.19's `gaza_evidence`, `gaza_voting_records`, `uscpr_grade` and `gaza_platform`. Presence counts for the Gaza layers do not change the 245 existing prose-evidence items or imply that a candidate holds a position on any other topic; `platform_positions` presence means only that quoted points were found on the reviewed campaign-site pages. The shared renderers put the Gaza layers inside one collapsed Gaza disclosure and platform positions in their own "What they stand for" disclosure in each reader. Every tracked source action stays available in a nested Congress/member disclosure, with its actual date and source kind. Sheet colors are source assessments, accompanied by text; `Yes`, `No`, `Not voting`, `Present`, `Not elected` and missing values retain their distinct meanings. Only the official scorecard supplies USCPR grades; Column A never supplies a fallback. See [GAZA_VOTING_RECORDS.md](GAZA_VOTING_RECORDS.md) and [CAMPAIGN_PLATFORMS.md](CAMPAIGN_PLATFORMS.md).

To refresh both congressional sources, capture dated snapshots, then draft an exact local review:

```sh
python3 scripts/sync_gaza_records.py capture --checked-on YYYY-MM-DD
python3 scripts/sync_gaza_records.py review \
  --votes research/gaza-records/voting-records-YYYY-MM-DD.json \
  --grades research/gaza-records/uscpr-grades-YYYY-MM-DD.json \
  --links research/gaza-records/candidate-links.json \
  --id gaza-records-YYYY-MM-DD \
  --output research/reviews/gaza-records-YYYY-MM-DD.json
```

Replace the date with the actual retrieval date and choose an unused review ID/path. Read the source differences, reviewed identity links, old/new candidate fields and missing-profile dispositions before applying the draft with `python3 scripts/reviewed_updates.py apply research/reviews/gaza-records-YYYY-MM-DD.json`. The sync script also supports `review --apply` on its first invocation with a new output path after source review; it only applies locally and never commits, pushes or deploys. An existing review file is immutable and must not be overwritten. New sheet columns/header layouts stop capture until the adapter and source dispositions are reviewed. Keep the dated normalized snapshots and registered publication review together, bump `publication_version`, rebuild and run the full gate. A source refresh must not advance ballot or finance research dates.

`check_data.py` imports `check_evidence.py`, which rejects unresolved candidate/source pairs from `docs/reviews/evidence-quarantine.json`, duplicate source/excerpt pairs (including renamed X handles), reused evidence IDs with different meanings, invalid/future dates relative to the check date, and obvious raw/cut-off excerpts. Run `check_evidence.py` directly for its regression checks. These checks do not certify identity or political facts.

To restore a quarantined source, establish the missing identity/attribution/content/date, record the resolution in the review log, remove its active quarantine entry, and then add the verified evidence and rebuild. Do not simply change an evidence ID or URL spelling to evade the gate. After the reviewed publication change, reconcile the versioned collector with `python3 research/gaza-stance/merge_gaza_evidence.py --sync-published` (add `--dry-run` to preview). New unreviewed collector items stop reconciliation rather than being discarded. Run `python3 scripts/check_gaza_ledger.py`; the merger rejects missing or replaced published evidence and unresolved quarantined sources before writing.

Do not claim a Jev assessment unless a documented API endpoint/authentication contract was used and its results were actually reviewed; never call another model and label its results Jev, invent an endpoint, or send a credential to an unverified host. `prepare_jev_review.py --include-quarantine` writes 300 JSONL packets under `.checks/` for the current review baseline. It prepares packets only — it never claims an API call occurred. Optional `--source-texts` accepts an object keyed by evidence ID with `{url, text}`; the URL must equal the evidence URL. Without it, only stored excerpts are supplied, explicitly labeled as such. Jev's documented endpoint/authentication contract and outbound network access are still required. No keys belong in source, generated HTML, packets, or logs.


## Reviewed peace guides (October 9, schema 1.15)

`import_peace_guides.py` applies the source-card manifest as part of the combined endorsement migration. `check_peace_guides.py` checks completeness, polarity, election phase, preserved CAIR/Track AIPAC records, idempotence and observation dates. `check_published_endorsements.py` requires reviewed guide observations to remain present and unchanged. The CAIR importer preserves the order of already-correct records so rerunning it remains idempotent after another publisher is added.

Both UI date-label functions distinguish `source_observed` from historical dates. The schema requires a complete date, voter-guide source kind and explanatory date note; the evidence guard requires observation date to equal check date. The shared endorsement renderer displays Ally explicitly without upgrading it to a formal endorsement. Rebuild both HTML files and run all README checks after changing these sources.


## California campaign finance refresh

The CAL-ACCESS layer (`scripts/ca_campaign_finance.py`) reads the Secretary of State's nightly raw export. The zip (~1.6 GB), extracted TSVs and derived snapshot live under gitignored `.research/ca-finance/`; `run-state.json` records download/build/attach timestamps and the source Last-Modified/sha256.

```sh
python3 scripts/ca_campaign_finance.py download   # skips when the CDN copy is unchanged; --force overrides
python3 scripts/ca_campaign_finance.py build      # parses TSVs -> .research/ca-finance/derived-ca-finance.json
python3 scripts/ca_campaign_finance.py attach --publication-version YYYY-MM-DD.N
python3 scripts/build_site.py
python3 scripts/check_release.py
```

Receipt totals are Form 460 summary line 13 Column A summed across each controlled committee's in-window statements (highest AMEND_ID supersedes; periods opening before the cycle start are excluded, never split). IE rows require an IND expenditure code plus a support/oppose code and a parseable `EXPN_DATE` — that date requirement is what keeps coalition Schedule E memo rollups from double-counting the dated schedule-D detail rows. Do not re-add F465/F496 notice rows or undated rollup lines. Spenders resolve through `FILER_FILINGS_CD`; names through `FILERNAME_CD`. Name matching is deterministic (surname variants, nickname groups); ambiguous CAND matches drop the row rather than guess — inspect `candidacies_without_calaccess_match` after attach before assuming a miss is real absence. The SOS CDN does not answer HEAD reliably; freshness uses a 1-byte ranged GET.

## Reusable scope and review pipeline

Follow [REPEATABLE_RESEARCH.md](REPEATABLE_RESEARCH.md). County/FIPS data lives in `research/california-counties.json`; the build embeds the same registry that Node and Python read. Adding geography recognition never expands the election inventory. New reviewed changes use exact before/after records and source hashes, and are registered in `research/publication-reviews.json`. Keep review manifests, registry, canonical dataset, current coverage documentation and generated pages together. `schema_validation.py` holds the common focused validator; `check_schema.py` retains the regression suite. Improve shared adapters/guards when a failure class is found; do not create another dated one-off importer by default. Official roster research and the Gaza collector (`research/gaza-stance/`) retain their separate evidence requirements.


## Independent-expenditure refresh

The October 20 correction replaces custom raw Schedule E summation with the FEC candidate-page aggregate endpoint. It excludes 24-/48-hour notices and memo entries. Do not sum notice totals into regular-report totals, halve historical values, or revive the old filing-wide memo heuristic. `election_full=false` pins the two-year cycle; FEC owns cycle attribution and amendment handling. The [audit](reviews/2026-10-20-fec-ie-reconciliation.md) documents the source rules and per-candidate impact.

```sh
python3 scripts/fec_independent_expenditures.py plan
python3 scripts/fec_independent_expenditures.py run --force
python3 scripts/fec_independent_expenditures.py export --output .research/ie/official-aggregates.json
python3 scripts/audit_fec_independent_expenditures.py --baseline 2026-11-03_Bay_Area_Elections.json --snapshot .research/ie/official-aggregates.json --output .research/ie/impact.json
python3 scripts/fec_independent_expenditures.py attach --publication-version YYYY-MM-DD.N
python3 scripts/build_site.py
python3 scripts/check_release.py
```

Set `FEC_API_KEY` in the environment or pass global `--fec-key-file PATH` before the subcommand. Inspect the export and impact before attach. Default refresh age is seven days; `--force` refreshes every eligible candidate. A fresh clone needs no old ledger. Legacy tables remain intact but cannot satisfy the new method-version cache. Cache keys include candidate ID, cycle and method; incomplete API responses never replace a prior snapshot. Attach requires all current federal IDs and uses the oldest actual retrieval date, so partial county runs cannot label older nationwide results as freshly checked. Supplying `--checked-on` requires that exact date. Missing/unknown spenders, negative totals, unsupported directions, source renames and pagination inconsistencies stop the update for review rather than silently dropping money.

Export v2 retains FEC counts but omits transaction date ranges, which the aggregate endpoint does not supply. Existing registry committee types are preserved; new spenders can lack that optional metadata. Snapshot differences can reflect intervening filings, processing or cycle attribution as well as removed double counting. Sum-across-candidate totals are not unique national spending. The full `refresh_fec_money.py` also refreshes receipts and can publish under its existing main/clean-tree gate; use the IE-only commands above when receipts are outside scope.


## Ballotpedia endorsement supplement

Follow [BALLOTPEDIA_ENDORSEMENTS.md](BALLOTPEDIA_ENDORSEMENTS.md) for the recorded-profile collector, current-year source rules, saved-capture imports, Jev classifications, duplicate handling and the registered-review publication path. The campaign collector shares the same exact cross-source duplicate guard, so a later campaign refresh does not re-add a Ballotpedia observation. Source aliases and relationship conflicts remain reviewed/held; absence never deletes prior evidence. The new offline regression command is included in `check_release.py`.
