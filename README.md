# Bay Area Elections · November 2026

An independent research inventory and searchable, static explorer of elected offices for the **November 3, 2026 California general election** in **Alameda, Contra Costa, San Francisco, San Mateo, and Santa Clara counties**.

**Website:** https://salqadri.github.io/bay-area-elections-2026/

**Research snapshot: October 4, 2026.** Publication does not refresh or recertify the underlying research.

**FEC fundraising snapshot: October 6, 2026.** Federal candidate finance records have their own coverage dates and do not change the ballot-research snapshot date.

## Development and agent handoff

Start with [AGENTS.md](AGENTS.md), which applies to Hermes and other coding/research agents. The repository is self-contained; earlier chat history and scratch files are not needed.

- [Current handoff and priorities](docs/HANDOFF.md): dated baseline, unresolved work and suggested next tasks.
- [Election research guide](docs/RESEARCH.md): evidence standards, status decisions, source/ID conventions, FEC updates and a live unresolved-work queue command.
- [Maintenance guide](docs/MAINTENANCE.md): architecture, local development, verification limits, county expansion and publishing.

Use Git, Python 3 and Node.js. No npm/pip installation or API key is needed for the current implementation. The handoff was checked with Python 3.12.14 and Node 24.19.0; other versions are not a tested compatibility matrix.

```sh
git clone https://github.com/salqadri/bay-area-elections-2026.git
cd bay-area-elections-2026
python3 scripts/build_site.py --check
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/` or `http://127.0.0.1:8000/ballot.html`. Use `python` instead of `python3` where that is the installed executable. For an existing clone, inspect local changes and fetch the current remote state before editing.

**Edit the dataset, schema, templates and JavaScript modules; rebuild both generated HTML files.** The builder does not update coverage totals or research facts. See the verification commands below and the maintenance guide before publishing.

## Navigation and ordering

The default **By office priority** view uses expandable sections for federal, state, judicial, county, city, education, and special-district contests. State contests appear in the requested order: **State Senate → State Assembly → other state offices**. Within the latter, Governor comes first, followed by Lieutenant Governor, Secretary of State, Controller, Treasurer, Attorney General, Insurance Commissioner, Superintendent of Public Instruction, and Board of Equalization. This is an editorial display preference, not a constitutional hierarchy.

Click a section heading to expand it, or use **Expand all / Collapse all**. Counts include contests inside collapsed sections. Search results and direct contest links open the relevant sections automatically. City contests are grouped by jurisdiction. The jurisdiction and office sorts offer flat lists. Shared ordering settings live in `display_order`; the JSON positions array also follows the requested state-office priority.

## Find my ballot by address

**Address view:** https://salqadri.github.io/bay-area-elections-2026/ballot.html

Enter a full US street address with city, state, and ZIP code. The public U.S. Census Geocoder supplies estimated address geography without an API key. If it returns multiple locations, the page initially shows the union of their races and lets the user choose a particular location. Unsupported counties and failed lookups receive explicit messages; neither is presented as an empty official ballot. County browsing remains available when an address cannot be resolved.

**Address autocomplete:** [Photon](https://github.com/komoot/photon) supplies OpenStreetMap address suggestions without an API key. After at least four characters and a 750 ms pause, the page requests US house addresses with a Bay Area location preference. It displays up to six complete returned addresses; it never invents a house number for a street-only result. Arrow keys and Enter select a suggestion, Escape dismisses the list, and ordinary Enter still submits a manually entered address. Selecting a suggestion fills the field without submitting. The Census lookup remains responsible for ballot geography.

The public Photon demo permits reasonable project use and can throttle requests; it has no service availability guarantee. Requests are limited to at most one per second per page, superseded requests are canceled, failures back off, and manual entry always remains available. Suggestions require internet access and OpenStreetMap address coverage varies. Provider attribution appears beside the field. For sustained high traffic, use a hosted provider or a dedicated Photon service rather than relying on the demo. The public Nominatim endpoint is not used.

The matcher keeps three geographic classifications separate from ballot appearance:

| Geographic classification | Meaning |
| --- | --- |
| `expected` | A statewide, whole-county, current legislative, citywide, or at-large school-district geography matches. This is still an estimate. |
| `district_uncertain` | A parent jurisdiction matches, but a council, supervisor or trustee district remains unresolved. All researched alternatives are retained. |
| `membership_uncertain` | Membership in the local district itself has not been established. County-relevant alternatives remain visible. |

The expected/possible counts include confirmed ballot contests only. Unverified scheduled contests have a separate count and a visible ballot-appearance label. A missing district response broadens the result. It never means that the voter has no contest. Schools and special districts without an established geographic match remain county-level possibilities even when another school district was located; this intentionally favors inclusion over silently omitting a race. Do not treat all the displayed alternatives as votes available to one person.

The Census request uses JSONP because the [official API documentation](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html) says browser CORS requests are not supported. It requests incorporated places, unincorporated Census-designated places, school districts, counties, states, **120th Congressional Districts**, and **2026 state legislative districts** from `Public_AR_Current` / `Current_Current`. [Current TIGERweb metadata](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer) identifies those layers; [California's 2026 congressional boundaries](https://www.sos.ca.gov/elections/california-redistricting) must not be replaced with 119th-Congress maps. The matcher refuses to narrow House races from a 119th-Congress response. Legislative responses for a different vintage stay uncertain.

Mailing cities are not used as municipal boundaries. A returned incorporated place can narrow city contests; a [Census-designated place identifies an unincorporated community](https://www.census.gov/programs-surveys/bas/information/cdp.html). Census does not establish the local council, supervisor, college trustee, or special-district voting areas needed for many races. For appellate retention and BOE records that encompass entire listed counties, the dataset explicitly records `countywide_electorate: true`; this property does not extend to other county-associated districts.

Partial address text is sent to Photon while typing; the submitted address is sent to the Census service. The site does not put addresses into page URLs, browser storage, analytics, or downloaded estimates. Requests time out and can be canceled; stale responses cannot overwrite a newer lookup. Census range-based geocoding is an estimate of a location, not proof of a registered voting residence. The new page links to official county election resources.

The optional estimate download has the distinct format `bay-area-ballot-estimate/v1`, with matched geographic areas, warnings, confidence-tagged races, and the shared candidate/source/finance metadata. It excludes raw street addresses and coordinates. It is a report of a lookup, rather than the full-inventory format described by `elections.schema.json`.

**Verification:** API parameters and 2026 layer metadata were checked against official documentation. The service transports, autocomplete controls, matcher and page are tested using deterministic response fixtures and a minimal DOM. Live Census and Photon requests could not be completed from the execution environment, so `address_lookup.api_validated` remains false. This does not turn convention-based OCD identifiers into API-validated records. The published app makes real requests when used in a browser; it has no simulated address results or embedded API credentials.

## Federal campaign fundraising

All **22 printed federal candidates** have an FEC ID and a finance record. **20** have published total receipts; **Jeff Frese and Charles Hoelter** have `receipts: null` because their FEC candidate summaries did not publish a total. Null is not a reported zero.

`candidate.fec` holds the candidate ID, `receipts`, coverage `from` and `through` dates, authorized `committee_ids` when available, a `source_id`, and an optional `note_id`. Shared `finance` settings record the provider, 2026 cycle, USD currency, total-receipts metric, October 6 retrieval date, and method once rather than repeating them for every candidate. Amounts are in dollars to cent precision.

Receipts are copied from FEC candidate summaries, with Lofgren's current principal-committee summary corroborating her candidate summary. They include contributions, transfers, loans, offsets, and other receipts, so they are not net donations or cash on hand. Independent outside spending is excluded. Candidate aggregate totals are used without adding committee totals again; reported transfers are not manually removed. FEC candidate IDs are distinct from committee IDs and OCD geographic identifiers.

**Compare coverage dates.** Most totals run through June 30, 2026; others run through September 7 or September 30. Scott Wiener's FEC summary reports January 1, 2023–June 30, 2026 even for the 2026 election. The dataset preserves the FEC's amount and period and explicitly flags that it is not verified as a January 2025 onward subtotal. These are dated snapshots, not a live feed. Follow each candidate's FEC source for later filings or amendments.

## Coverage and limitations

The snapshot contains **416 researched contests**, including **336 confirmed contests**, **439 confirmed seats**, **869 printed candidate entries**, and **80 unresolved scheduled contests**. One confirmed contest has an unverified candidate roster.

| County | Confirmed contests | Unresolved scheduled contests |
| --- | ---: | ---: |
| Alameda | 117 | 21 |
| Contra Costa | 83 | 55 |
| San Francisco | 37 | 0 |
| San Mateo | 89 | 2 |
| Santa Clara | 100 | 4 |

County totals overlap: a shared district appears once in the data with multiple county names. A contest's inclusion for a county does **not** mean every county resident can vote in it.

**This inventory is not yet certified exhaustive.** Unresolved records describe scheduled contests whose final ballot inclusion or cancellation has not been established. They must not be treated as confirmed ballot contests. The explorer defaults to confirmed contests, labels uncertainty, and preserves the source and research-note registries.

The full Contra Costa final on-ballot proof PDF could not be retrieved during research. That county uses the available official material and corroborating election coverage; many unopposed contests remain unresolved. See `coverage.limitations` and each contest's notes for the specific boundaries of the research.

Candidate lists describe printed ballot names. Provisional filers and verified write-ins are stored separately. Write-in qualification can continue after the snapshot date. A candidate who stopped campaigning may still have a printed ballot name; relevant notes explain such cases. **135 printed candidate entries (90 people)** carry a separately verified official X account (`x_url`), **10 federal incumbents add a second verified account** (`secondary_x_url`, personal vs office handle) and **386 carry a verified campaign or official website** (`campaign_url`; two unverifiable generic-platform-homepage claims removed October 8), each with its own evidence source checked October 6–7, 2026. Verification confidence is recorded per entry in the cited source: most were confirmed against live profile text; **27 entries are explicitly "probable match" (indirect biographical evidence)** and their source titles say so — treat those as probable, not certain. Organization pages, same-name professionals and city-government sites are excluded. Most local candidates publish no findable account, and omission never means none exists.

Open Civic Data identifiers are included where available and carry an explicit verification status. They have **not been API-validated**. The address view estimates races and retains unresolved alternatives; it does not determine an official ballot or voter registration. Consult the relevant county election office for your official ballot.

**Gaza stance research (in progress, ungraded).** **113 printed candidate entries (113 people) across all five counties** carry a `gaza_evidence` list — 45 Alameda, 35 Contra Costa, 24 San Francisco, 30 San Mateo, 37 Santa Clara: **every item carries a calendar-valid date** — schema 1.11 requires it and records how each was established (`date_method`: source-stated, page metadata, X snowflake, Wayback first capture (an upper bound), or event-recorded, with an optional `date_note`), because an undated item cannot establish how a stance evolved — plus a link to dated public evidence (statements, votes, funding records) relevant to positions on Israel/Gaza/Palestine, checked October 7–9, 2026. Items whose date cannot be established are quarantined in the ledger and never enter the dataset. Each item names one dimension (genocide language, war crimes, military aid, AIPAC/pro-Israel funding, framing, actions/votes). This is deliberately **evidence only: no grades or verdicts are stored**. The research ledger and pipeline live in `/workspace/gaza-stance-research` (see `AGENTS.md`, section "Gaza stance evidence research"). Two October 8 external reviews found systematic wrong-person attribution, unsupported collective/co-signature claims, relevance misses and unreliable dating; the full ledger was revalidated twice against deterministic acceptance rules (`validate_evidence.py`) plus manual identity audits, and every removed item is quarantined with a written reason (`ledger/undated_quarantine.json`, 111 entries). Omission never means nothing exists, and most local candidates publish no findable record.

## Files and data conventions

- [`ballot.html`](ballot.html): address-based ballot estimate with inclusive district alternatives.
- [`index.html`](index.html): self-contained explorer, including its dataset and schema; works on GitHub Pages or when opened locally.
- [`2026-11-03_Bay_Area_Elections.json`](2026-11-03_Bay_Area_Elections.json): source dataset, schema version 1.11 (`schema_version` in the file is authoritative).
- [`elections.schema.json`](elections.schema.json): JSON Schema, Draft 2020-12.
- [`src/index.template.html`](src/index.template.html): maintained explorer markup, shared styles and explorer logic.
- [`src/ballot.template.html`](src/ballot.template.html) and [`src/`](src/): maintained address page and its service, matching and autocomplete modules.
- [`AGENTS.md`](AGENTS.md) and [`docs/`](docs/): agent instructions, research workflow, architecture and current handoff.
- [`scripts/`](scripts/): dependency-free build and verification tools (Python 3 and Node.js for the JavaScript checks).

Each position uses a stable ID and a `counties` array. Multi-seat elections remain one contest with a `seats` count. Legislative seats use `AD-18`, `CD-18`, or `SD-10` style labels. Party codes resolve through `codes.party`; `NPP` means the official No Party Preference label. An omitted party in a nonpartisan contest has a different meaning. `incumbent` is emitted only when verified true. Missing URLs and IDs are omitted, while an unverified candidate roster is explicitly `null`. A candidate's optional `x_url` records a separately verified official X (Twitter) account and `campaign_url` their own campaign or official website, each with its own evidence source; omission means nothing was verified for that person, not that none exists. City-government profile pages are deliberately excluded from `campaign_url`.

`ballot_status` and `candidate_list_status` are independent. Use `ballot_status: "confirmed"` when selecting known ballot contests, and inspect `candidate_list_status` before treating a roster as complete. Source and note IDs resolve through the top-level `sources` and `notes` registries. Ballotpedia links are included where researched; a link's scope can be broader than a particular seat and is labeled accordingly.

## Update and verify

Edit the JSON, schema, JavaScript modules, or HTML templates, then rebuild the published HTML pages:

```sh
python3 scripts/build_site.py
```

Run the checks from any working directory, using the appropriate path to each script:

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

The checks verify that the generated HTML is current, its embedded dataset and schema match the standalone files, references resolve, IDs are unique, coverage arithmetic agrees with the records, and FEC amounts and dates obey their conventions. The focused schema checker covers the assertion keywords used here and exercises invalid and valid examples, including the difference between unknown and zero receipts; it is **not a standard general-purpose Draft 2020-12 validator**. The UI check executes the actual inline JavaScript in a minimal DOM harness to exercise priority ordering, expandable sections, direct links, fundraising displays, filters, shared districts, uncertainty labels, and downloads; it is **not a browser rendering test**. These checks validate the publication's internal consistency, not the election facts or completeness.

The UI checks put temporary results in the ignored `.checks/` directory. There are no runtime package dependencies or analytics. The address page requests Photon suggestions while typing and loads a Census JSONP response when the user submits an address.

## GitHub Pages

The repository is prepared for GitHub Pages publishing from **branch `main`, folder `/ (root)`**. The committed `index.html` is the entry point and `.nojekyll` disables Jekyll processing. No build workflow or secrets are required for serving the site.

GitHub setting: **Settings → Pages → Build and deployment → Deploy from a branch → `main` → `/ (root)` → Save**.

The website is published at the URL above. A push or merge to `main` publishes the committed root files. Include rebuilt HTML when its sources change, and confirm the Pages deployment succeeds for the exact new commit. A successful deployment does not establish that live address providers work. See the maintenance guide for the complete release workflow.
