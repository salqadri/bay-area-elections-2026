# Research and development handoff

**Prepared October 6, 2026 (America/Los_Angeles).** This is a handoff of existing work, not a new verification of election facts. Recheck the JSON and Git history before using these numbers as the current state.

The baseline implementation is commit `f2e15251ca44f2baf50e141fd14d77d09f480ed8`, which added address autocomplete. This documentation may be followed by additional commits. The repository contains the maintained project; no prior ChatGPT conversation, scratch files or connector account is needed to work on it.

## Current state

| Item | Handoff baseline |
| --- | --- |
| Election | November 3, 2026 California general election |
| County scope | Alameda, Contra Costa, San Francisco, San Mateo, Santa Clara |
| Ballot research snapshot | October 4, 2026 |
| FEC research snapshot | October 6, 2026; individual financial coverage dates differ |
| Schema | Inventory version 1.9, Draft 2020-12 (`x_url`, `secondary_x_url`, `campaign_url`, `gaza_evidence`) |
| X accounts / sites | 135 printed entries (90 people) with verified official X URLs; 10 federal incumbents add a second verified account in `secondary_x_url` (personal vs office handle); 388 with verified campaign/official websites (checked October 6–7, 2026; each has its own evidence source) |
| Gaza stance research | 26 San Francisco-ballot candidates carry dated, linked, **ungraded** `gaza_evidence` items (101 total; checked October 7–8, 2026). Evidence only — no grades exist in this dataset. Other counties not yet researched |
| Inventory | 416 researched contests; 336 confirmed, 80 unresolved |
| Confirmed seats | 439 |
| Printed candidate entries | 869; these are entries, not necessarily unique people |
| Confirmed races with missing roster | 1: `CA2026-381`, East Bay Regional Park District Ward 7 |
| OCD electorate IDs | 188, all currently convention-based; not live API validated |
| Federal finance | 22 printed candidates with FEC IDs; 20 totals, 2 unknown amounts |
| Live address checks | Census and Photon requests were blocked in the original execution environment; fixture checks passed |

The site already includes a downloadable JSON/schema, hierarchical explorer, candidate and FEC details, address-to-ballot estimates, inclusive warnings for unresolved districts and accessible autocomplete. Do not recreate these features before inspecting the existing implementation.

## Suggested next work

These are priorities for the next maintainer, not permission gates or claims that the work has already been done.

1. **Resolve final ballot inclusion and missing rosters.** Start with Contra Costa's final on-ballot proof and `CA2026-381`, then process the unresolved queue. [RESEARCH.md](RESEARCH.md) has exact source pointers and a command to list the live queue. Confirm appointments/cancellations explicitly; a sole filer is not enough evidence.
2. **Verify address services in a real browser.** Test autocomplete and Census lookups using public civic-building addresses across all five counties. Check actual responses, CORS/JSONP behavior, map vintage, mobile/keyboard interaction and failure fallback. Keep `api_validated: false` until evidence justifies a clearly scoped change; a single successful request does not validate every OCD ID or every race.
3. **Refresh time-sensitive evidence.** Check official final candidate/retention materials, qualified write-ins, FEC filings and unresolved incumbent/link assertions. Preserve printed names when campaign withdrawal does not remove them from the ballot. Revisit the two missing FEC totals and the Scott Wiener coverage-period exception.
4. **Audit local geographic coverage.** Validate convention-based OCD IDs, investigate official GIS/precinct-to-ballot sources for council, supervisor, school, college and special districts, and compare with official county ballots. Only narrow alternatives when the evidence is reliable; missing API fields must not suppress plausible races.
5. **Expand coverage to the remaining four counties.** Marin, Napa, Solano and Sonoma are the longer-term goal. Follow the code/data expansion checklist in [MAINTENANCE.md](MAINTENANCE.md); shared districts, countywide flags, FIPS mappings and hardcoded five-county text all need attention.
6. **Continue Gaza stance evidence research.** San Francisco is done (26 people, 101 ungraded `gaza_evidence` items). Run the remaining ballot counties — Alameda, Contra Costa, San Mateo, Santa Clara — via `/workspace/gaza-stance-research` (see its README and AGENTS.md "Gaza stance evidence research"): one `--county` pass each, then re-run `merge_gaza_evidence.py`, rebuild and run the full suite. Grading (A–F) is a separate future step that only begins on explicit user instruction; until then no verdicts enter the data.
7. **Improve maintainability where it helps research.** Candidate opportunities include a reproducible coverage-summary updater, per-record provenance dates, a standard JSON Schema validation gate, a schema for the estimate export, browser smoke checks and CI. These are not implemented promises. Add them in small reviewable changes and avoid making fixture success stand in for factual accuracy.

## Known research exceptions to preserve

- The full Contra Costa August 27 final on-ballot proof PDF could not be retrieved during the prior research. Some official and corroborating material was available, but the county is not certified exhaustive. Retain uncertainty until the actual final evidence is checked.
- EBRPD Ward 7 has confirmed ballot appearance but conflicting roster evidence. Its provisional names are stored separately; do not promote them all to a final roster by copying the filed list.
- Jeff Frese and Charles Hoelter have `fec.receipts: null`, with explanatory notes. These are unknown totals, not zero.
- Scott Wiener's FEC summary has a coverage period beginning in 2023. Preserve the reported period and exception note; do not relabel the same amount as a 2025–2026 subtotal.
- The inventory currently excludes ballot measures and is not a complete official sample ballot. Missing/unverified local IDs and unresolved scheduled elections are separate limitations.
- Some prior exclusions are described in notes/limitations rather than retained as position records. When establishing exhaustive coverage, explicitly audit what is absent as well as what is present.

## Working agreement

Read [AGENTS.md](../AGENTS.md), then maintain evidence and implementation together. Keep stable IDs, compact shared metadata, official party labels, `incumbent` only when true, and the user's Senate → Assembly → other-state-offices display preference. Both generated HTML files must reflect any data or source-code change.

For each research batch, record the contest IDs checked, evidence/document dates, resulting status changes and unresolved questions. Refresh this handoff after material progress so a future agent can distinguish completed work from the original backlog. Do not merely move a date forward to make stale research appear fresh.
