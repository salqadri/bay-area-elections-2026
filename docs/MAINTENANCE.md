# Maintaining the explorer

This guide describes the implementation at the October 6, 2026 handoff. Inspect current code before relying on a fixed provider layer, snapshot count or version.

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
| `src/ballot-page.js` | Form orchestration, warnings, candidate/race display and estimate export |
| `scripts/build_site.py` | Embeds the dataset, schema where applicable, shared CSS and JavaScript into both pages |
| `scripts/prepare_dom_fixture.py` | Parses built pages into disposable DOM fixtures for Node integration checks |

`index.html` and `ballot.html` are generated and committed. The first embeds the dataset and schema; the second embeds the dataset and address modules. Both are self-contained except for remote address services invoked by user interaction. Shared style changes in the index template also affect the ballot page. Preserve the build's `<` escaping for embedded JSON and its rejection of closing-script sequences in inline JavaScript.

The downloaded address estimate uses **`bay-area-ballot-estimate/v1`**, not the inventory schema. It carries geography, confidence-tagged races and shared metadata, and deliberately omits raw addresses/coordinates. If its shape changes, treat it as a separate format contract; a dedicated schema is a possible improvement, not something already provided.

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
python3 scripts/check_schema.py
python3 scripts/prepare_dom_fixture.py
node scripts/check_explorer.cjs
node scripts/check_address_services.cjs
node scripts/check_address_suggestions.cjs
node scripts/check_address_autocomplete.cjs
node scripts/check_address_matcher.cjs
node scripts/check_ballot_page.cjs
```

The fixture preparation must follow the build and precede the two page integration checks. `.checks/` contains disposable fixtures/reports and is ignored. The build's `--check` does not repair stale HTML. Do not use Python's `-O` option; these checks rely on assertions.

| Check | What it establishes | What it does not establish |
| --- | --- | --- |
| Build check | Generated pages equal current sources | Browser appearance or external availability |
| Data check | IDs/references, omission rules, global counts, FEC conventions and embedded inventory agree | Source truth, URL validity, correct geographic eligibility or exhaustive coverage |
| Schema check | Current schema keywords and positive/negative examples pass the repository's focused validator | Full standards compliance; use a standard Draft 2020-12 validator with format checking for interoperability |
| Explorer/ballot checks | Real embedded scripts work in a minimal DOM harness with fixture responses | Layout, real keyboard/browser event behavior or live geocoding |
| Service/autocomplete/matcher checks | Parsing, timeout/abort, rate handling, uncertainty, unions and regression cases | Live provider response shapes, CORS, uptime or actual district correctness |

Existing fixtures intentionally contain some known names, FEC amounts/dates, record IDs, seat counts and a five-county selector count. Research updates can make those expectations stale. Determine whether the changed evidence or a code defect caused a failure; update the fixture with a reason, rather than replacing precise checks with unconditional success.

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
