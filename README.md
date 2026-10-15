# Bay Area Ballot Research Assistant

An independent research inventory and searchable, static explorer of elected offices for the **November 3, 2026 California general election** in **Alameda, Contra Costa, San Francisco, San Mateo, and Santa Clara counties**.

**Website:** https://salqadri.github.io/bay-area-elections-2026/

**Research snapshot: October 4, 2026.** Publication does not refresh or recertify the underlying research.

**FEC fundraising snapshot: checked October 12, 2026.** Federal candidate finance records have their own coverage dates and do not change the ballot-research snapshot date. A scheduled weekly refresh re-checks receipts and independent expenditures through November 3.

## Development and agent handoff

Start with [AGENTS.md](AGENTS.md), which applies to Hermes and other coding/research agents. The repository is self-contained; earlier chat history and scratch files are not needed.

- [Current handoff and priorities](docs/HANDOFF.md): dated baseline, unresolved work and suggested next tasks.
- [Election research guide](docs/RESEARCH.md): evidence standards, status decisions, source/ID conventions, FEC updates and a live unresolved-work queue command.
- [Maintenance guide](docs/MAINTENANCE.md): architecture, local development, verification limits, county expansion and publishing.
- [Repeatable county workflow](docs/REPEATABLE_RESEARCH.md): county/Bay Area/California plans, cached reruns, source review drafts, exact before/after updates and an immutable publication history.
- [Endorsement research](docs/ENDORSEMENTS.md): cached collection, shared-source review and separately labeled support evidence. Current coverage: **12,953 records on 387 of 875 printed candidacies**, including the October 11–12 campaign-site scan (**+12,743 campaign claims**, page-text quotes plus logo filenames readable on each campaign's own site). See the [campaign-site scan review](docs/reviews/2026-10-11-campaign-site-scan.md), the [priority PAC review](docs/reviews/2026-10-10-priority-pac-review.md), the [Vote for Peace / AROC review](docs/reviews/2026-10-09-peace-guides.md), [CAIR correction](docs/reviews/2026-10-09-cair-action-correction.md), [captured recommendations](research/endorsements/cair-action-2026-10-09.json), and [earlier publication audit](docs/reviews/2026-10-09-targeted-endorsements.md).

Use Git, Python 3 and Node.js. No npm/pip installation or API key is needed to build, serve or validate the site. The optional endorsement collector uses a Serper key for search; imported page lookups need no key. The handoff was checked with Python 3.12.14 and Node 24.19.0; other versions are not a tested compatibility matrix.

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

`candidate.fec` holds the candidate ID, `receipts`, coverage `from` and `through` dates, authorized `committee_ids` when available, a `source_id`, and an optional `note_id`. Shared `finance` settings record the provider, 2026 cycle, USD currency, total-receipts metric, October 12 retrieval date, and method once rather than repeating them for every candidate. Amounts are in dollars to cent precision.

Receipts are copied from FEC candidate summaries, with Lofgren's current principal-committee summary corroborating her candidate summary. They include contributions, transfers, loans, offsets, and other receipts, so they are not net donations or cash on hand. Independent outside spending is excluded. Candidate aggregate totals are used without adding committee totals again; reported transfers are not manually removed. FEC candidate IDs are distinct from committee IDs and OCD geographic identifiers.

**Independent expenditures (new).** Each printed federal candidate also carries `independent_expenditures`: itemized FEC Schedule E outside spending linked to them in the **2026 two-year period**, split into totals spent **for** and **against** the candidate plus one row per spender and direction (`spender_id` resolves through the shared `ie_spenders` registry; committee type included). Every spender name links to its FEC committee page (registry `source_url`; an FEC data-search link when no committee ID exists), and each card links to the FEC independent-expenditure browse page filtered to that candidate (`browse_url`). Collection is deterministic — `scripts/fec_independent_expenditures.py` (plan → run → export → attach) reads the FEC API directly with keyset pagination, keeps only current-cycle election types and the most recent amendment, and never adds a memo subtotal twice. Shared settings live in `ie_finance`; retrieval date is **October 12, 2026**. In both readers the receipts and independent-spending cards sit inside one collapsed **Campaign money** disclosure per candidate. Amounts are independent spending by outside committees: they are not campaign receipts, coordination findings or endorsements, and support for one candidate is never treated as opposition to another. The October 12 snapshot covers all 22 printed federal candidates; **13 have current-cycle activity** ($12.5M for / $2.6M against across the set). Late filings that reference prior elections are excluded from totals, and newly filed reports can raise a candidate's total after this date.

The refresher accepts `FEC_API_KEY` or `--fec-key-file`. Publishing uses configured Git credentials, or `GITHUB_TOKEN`/`GH_TOKEN`/`--github-token-file`; token authentication is passed privately to Git, never embedded in a URL. Automated publication requires a clean `main` checkout. Use `--skip-push` to refresh, rebuild and validate a local review without committing or publishing. A first available receipts total must include a valid coverage period and authorized committee IDs. The October 14 code fixes do not refresh the October 12 finance snapshot; mixed-direction aggregation will take effect when Schedule E is next collected and attached.

**Compare coverage dates.** Most totals run through June 30, 2026; others run through September 7 or September 30. Scott Wiener's FEC summary reports January 1, 2023–June 30, 2026 even for the 2026 election. The dataset preserves the FEC's amount and period and explicitly flags that it is not verified as a January 2025 onward subtotal. These are dated snapshots, not a live feed. Follow each candidate's FEC source for later filings or amendments.

## Coverage and limitations

The snapshot contains **416 researched contests**, including **340 confirmed contests**, **443 confirmed seats**, **875 printed candidate entries**, and **0 unresolved scheduled contests** as of October 14, 2026. Every confirmed contest now carries a complete verified roster; 76 contests are recorded as excluded (confirmed not on the ballot): 51 Contra Costa after reconciliation against the county's final certification files, 21 Alameda (including all 19 races resolved October 13 against the Registrar's official Candidate List for the November 3 General Election), and Santa Clara's four zero-filing districts plus San Mateo's Bayshore ESD short term and Colma Fire Director on October 14.

| County | Confirmed contests | Unresolved scheduled contests |
| --- | ---: | ---: |
| Alameda | 117 | 0 |
| Contra Costa | 87 | 0 |
| San Francisco | 37 | 0 |
| San Mateo | 89 | 0 |
| Santa Clara | 100 | 0 |

County totals overlap: a shared district appears once in the data with multiple county names. A contest's inclusion for a county does **not** mean every county resident can vote in it.

**This inventory is not yet certified exhaustive.** Every scheduled contest now carries a final ballot status; excluded contests record final ballot status only — how each excluded seat was filled (holdover or appointment in lieu) is not asserted, and unverified local OCD identifiers remain. The explorer defaults to confirmed contests, labels uncertainty, and preserves the source and research-note registries.

Contra Costa's local contests were reconciled on October 12, 2026 against the county's certified August 14 candidate list and its exhaustive August 27 Contest/Candidate Proof List (both archived under `research/contra_costa/` and cited as S1087/S1088). Contests absent from that on-ballot proof — including Canyon Elementary SD and Rodeo Sanitary District, which never appear in either file — are recorded as excluded with their filers retained separately; unopposed candidates elected at certification are named in the contest notes. Santa Clara's Lion's Gate CSD (both terms), San Martin County Water District and Silver Creek Valley Country Club GHAD, and San Mateo's Bayshore ESD short term and Colma Fire Protection District Director were resolved October 14 as excluded on the same zero-filing pattern: each county's exhaustive final candidate documentation contains no row for these contests at all (Santa Clara additionally shows zero write-in filings in its unofficial write-in list), with ballot-material deadlines already passed; evidence and the Jev adjudication are archived under `research/unresolved_2026-10-14/`. See `coverage.limitations` for remaining boundaries.

Candidate lists describe printed ballot names. Provisional filers and verified write-ins are stored separately. Write-in qualification can continue after the snapshot date. A candidate who stopped campaigning may still have a printed ballot name; relevant notes explain such cases. **135 printed candidate entries (135 people)** carry a separately verified official X account (`x_url`), **10 federal incumbents add a second verified account** (`secondary_x_url`, personal vs office handle) and **383 carry a verified campaign or official website** (`campaign_url`; five unverifiable generic-platform-homepage claims removed October 8), each with its own evidence source checked October 6–7, 2026. Verification confidence is recorded per entry in the cited source: most were confirmed against live profile text; **27 entries are explicitly "probable match" (indirect biographical evidence)** and their source titles say so — treat those as probable, not certain. Organization pages, same-name professionals and city-government sites are excluded. Most local candidates publish no findable account, and omission never means none exists.

Open Civic Data identifiers are included where available and carry an explicit verification status. They have **not been API-validated**. The address view estimates races and retains unresolved alternatives; it does not determine an official ballot or voter registration. Consult the relevant county election office for your official ballot.

**Israel/Gaza/Palestine evidence (ungraded).** This branch retains **245 evidence items for 82 printed candidates**: Alameda 38, Contra Costa 25, San Francisco 24, San Mateo 26, Santa Clara 30 (county counts overlap). A manual post-enrichment review rewrote 44 summaries and moved 69 of the 300 input items into a documented, reversible quarantine. Fourteen new items capture attributed voter-guide assessments, explicitly dated as observations rather than historical statements. Their funding and legislative claims have not been independently audited. The [October 14 audit](docs/reviews/2026-10-14-gaza-and-finance-review.md) searched all 72 printed federal/state candidacies for Gaza and ceasefire evidence, restored three readable Panetta statements, added three other sourced observations, and quarantined or deduplicated six records. It screened all existing summaries and retried their citations; it did not exhaustively search the 803 local/judicial candidacies or independently verify tracker funding claims. Statements describe attributable positions/actions; missing evidence is never labeled neutrality. Financial summaries distinguish campaign contributions from outside spending and state the tracker's scope. No candidate grades are stored.

**Endorsements and recommendations.** **387 printed candidacies carry 12,953 records**: 12,867 endorsement observations, 18 preferences, 6 recommendations, 53 other support observations and 9 oppositions. Three records explicitly preserve historical race/office context under the owner’s policy; renewal research is not required. The October 11–12 campaign-site scan added **12,743 records labeled `campaign_claim`** — supporters named on each candidate's own website (page text quote-verified against cached snapshots, plus logo endorsements whose name comes from the campaign-published image filename), triaged by the Jev decision model (see [the scan review](docs/reviews/2026-10-11-campaign-site-scan.md)); they are campaign claims, not independent confirmation. The pages explicitly distinguish **Endorsed by**, **Preferred by**, **Listed as Ally by** and **Opposed by**. Presence counts include negative recommendations; they do not mean every listed organization endorsed the candidate. Sources include Vote for Peace, AROC Action, Track AIPAC, CAIR Action, Hindu American PAC, JStreetPAC, JDCA, DMFI PAC, United Democracy Project, California Jewish Democrats, local groups, campaign pages and secondary reports about Dr. Romesh Japra/Americans4Hindus. Publisher statements, campaign claims, secondary reports, election phase and qualifications remain visible; 1,877 records display the endorser's logo as published on the cited page. Source ratings are not this site's grades. County presence counts overlap: Alameda 128, Contra Costa 71, San Francisco 46, San Mateo 78 and Santa Clara 135.

The earlier October 9 audit removed **725 unsupported records**, including 723 neutral Chronicle voter-guide mentions incorrectly treated as endorsements. The subsequent CAIR correction replaces 15 secondary reports with **95 recommendations from a supplied capture of the official Explore page: 76 Endorsed, 18 Preferred and 1 Opposed**. All 200 captured cards have review dispositions; duplicates are collapsed and unmatched names remain in the review manifest. Tomara Hall's recommendation is held because the source says District 1 while the current roster and her campaign say Area 2. The capture omits the selected-election header, so its election phase remains unspecified. The linked PDF could not be read. Older records are not all independently audited, and AIPAC's dynamic list and several local lists remain unresolved. **488 candidacies have no published record; that is unknown, not proof of no endorsements.** Endorsements never determine official party preference. See [the research guide](docs/ENDORSEMENTS.md) for refresh commands and [the CAIR correction report](docs/reviews/2026-10-09-cair-action-correction.md) for source limits.

Read the [detailed review and limitations](docs/reviews/2026-10-08-post-enrichment-review.md), [per-item decisions](docs/reviews/2026-10-08-summary-review.json), and [quarantine](docs/reviews/evidence-quarantine.json). The optional Jev assessment was canceled by the project owner. These are manual corrections, not model-reviewed findings. Unchanged records have not all been independently fact-checked.

Schema 1.17 adds display-only `logo_url` on endorsement records and `election.publication_version`, a dated release marker (`YYYY-MM-DD.N`) shown in both page footers so readers can tell when content was last published; bump the sequence with each published dataset change. Schema 1.16 preserves calendar-valid dates and date provenance and explicitly labels historical endorsements/support. Both pages label archive captures as upper bounds and `source_observed` voter-guide assessments as dated snapshots with unknown original dates. These snapshots cannot establish the chronology of underlying candidate statements, votes or contributions. The collector/ledger (versioned at `research/gaza-stance/`) is reconciled to this publication; synchronize it after future manual changes before merging again; `check_data.py` now rejects unresolved quarantined sources. Omission means no retained evidence, not that a candidate has no position. The ballot and structured FEC research dates above are unchanged.

## Files and data conventions

- [`ballot.html`](ballot.html): address-based ballot estimate with inclusive district alternatives.
- [`index.html`](index.html): self-contained explorer, including its dataset and schema; works on GitHub Pages or when opened locally.
- [`2026-11-03_Bay_Area_Elections.json`](2026-11-03_Bay_Area_Elections.json): source dataset, schema version 1.18 (`schema_version` in the file is authoritative).
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
python3 scripts/check_evidence.py
python3 scripts/check_published_endorsements.py
python3 scripts/check_endorsements.py
python3 scripts/check_cair_guide.py
python3 scripts/check_peace_guides.py
python3 scripts/check_research_workflow.py
python3 scripts/check_schema.py
python3 scripts/check_fec_money.py
python3 scripts/check_gaza_ledger.py
python3 scripts/prepare_dom_fixture.py
node scripts/check_finance_display.cjs
node scripts/check_explorer.cjs
node scripts/check_address_services.cjs
node scripts/check_address_suggestions.cjs
node scripts/check_address_autocomplete.cjs
node scripts/check_address_matcher.cjs
node scripts/check_ballot_page.cjs
```

Run the full sequence above with **`python3 scripts/check_release.py`** (19 checks); its report and detailed logs go to `.checks/`.

The checks verify that the generated HTML is current, its embedded dataset and schema match the standalone files, references resolve, IDs are unique, coverage arithmetic agrees with the records, and FEC amounts and dates obey their conventions. The focused schema checker covers the assertion keywords used here and exercises invalid and valid examples, including the difference between unknown and zero receipts; it is **not a standard general-purpose Draft 2020-12 validator**. The UI check executes the actual inline JavaScript in a minimal DOM harness to exercise priority ordering, expandable sections, direct links, fundraising displays, filters, shared districts, uncertainty labels, and downloads; it is **not a browser rendering test**. These checks validate the publication's internal consistency, not the election facts or completeness.

The UI checks put temporary results in the ignored `.checks/` directory. There are no runtime package dependencies or analytics. The address page requests Photon suggestions while typing and loads a Census JSONP response when the user submits an address.

## GitHub Pages

The repository is prepared for GitHub Pages publishing from **branch `main`, folder `/ (root)`**. The committed `index.html` is the entry point and `.nojekyll` disables Jekyll processing. No build workflow or secrets are required for serving the site.

GitHub setting: **Settings → Pages → Build and deployment → Deploy from a branch → `main` → `/ (root)` → Save**.

The website is published at the URL above. A push or merge to `main` publishes the committed root files. Include rebuilt HTML when its sources change, and confirm the Pages deployment succeeds for the exact new commit. A successful deployment does not establish that live address providers work. See the maintenance guide for the complete release workflow.
