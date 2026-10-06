# Bay Area Elections · November 2026

An independent research inventory and searchable, static explorer of elected offices for the **November 3, 2026 California general election** in **Alameda, Contra Costa, San Francisco, San Mateo, and Santa Clara counties**.

**Website:** https://salqadri.github.io/bay-area-elections-2026/

**Research snapshot: October 4, 2026.** Publication does not refresh or recertify the underlying research.

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

Candidate lists describe printed ballot names. Provisional filers and verified write-ins are stored separately. Write-in qualification can continue after the snapshot date. A candidate who stopped campaigning may still have a printed ballot name; relevant notes explain such cases.

Open Civic Data identifiers are included where available and carry an explicit verification status. They have **not been API-validated**. The explorer does not determine a voter's ballot from an address. Consult the relevant county election office for your official ballot.

## Files and data conventions

- [`index.html`](index.html): self-contained explorer, including its dataset and schema; works on GitHub Pages or when opened locally.
- [`2026-11-03_Bay_Area_Elections.json`](2026-11-03_Bay_Area_Elections.json): source dataset, schema version 1.3.
- [`elections.schema.json`](elections.schema.json): JSON Schema, Draft 2020-12.
- [`src/index.template.html`](src/index.template.html): maintainable explorer template.
- [`scripts/`](scripts/): dependency-free build and verification tools (Python 3 and, for the UI integration check, Node.js).

Each position uses a stable ID and a `counties` array. Multi-seat elections remain one contest with a `seats` count. Legislative seats use `AD-18`, `CD-18`, or `SD-10` style labels. Party codes resolve through `codes.party`; `NPP` means the official No Party Preference label. An omitted party in a nonpartisan contest has a different meaning. `incumbent` is emitted only when verified true. Missing URLs and IDs are omitted, while an unverified candidate roster is explicitly `null`.

`ballot_status` and `candidate_list_status` are independent. Use `ballot_status: "confirmed"` when selecting known ballot contests, and inspect `candidate_list_status` before treating a roster as complete. Source and note IDs resolve through the top-level `sources` and `notes` registries. Ballotpedia links are included where researched; a link's scope can be broader than a particular seat and is labeled accordingly.

## Update and verify

Edit the JSON, schema, or HTML template, then rebuild the single published HTML file:

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
```

The checks verify that the generated HTML is current, its embedded dataset and schema match the standalone files, references resolve, IDs are unique, and coverage arithmetic agrees with the records. The focused schema checker covers the assertion keywords used here and exercises invalid and valid examples; it is **not a standard general-purpose Draft 2020-12 validator**. The UI check executes the actual inline JavaScript in a minimal DOM harness to exercise filters, shared districts, uncertainty labels, and downloads; it is **not a browser rendering test**. These checks validate the publication's internal consistency, not the election facts or completeness.

The UI checks put temporary results in the ignored `.checks/` directory. There are no runtime package dependencies, analytics, or third-party scripts.

## GitHub Pages

The repository is prepared for GitHub Pages publishing from **branch `main`, folder `/ (root)`**. The committed `index.html` is the entry point and `.nojekyll` disables Jekyll processing. No build workflow or secrets are required for serving the site.

GitHub setting: **Settings → Pages → Build and deployment → Deploy from a branch → `main` → `/ (root)` → Save**.

The website URL above is the intended project-page address; a successful Pages deployment is required before it becomes available.
