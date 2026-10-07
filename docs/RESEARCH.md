# Research and data maintenance

This is an evidence-backed inventory of elected-office contests for **November 3, 2026**, including explicitly unresolved scheduled contests. It is not a certified exhaustive ballot. Work from the current JSON and the cited documents; this guide describes the research contract, not proof that every existing record is correct.

The canonical dataset is `2026-11-03_Bay_Area_Elections.json`; the field contract is `elections.schema.json`. Read [MAINTENANCE.md](MAINTENANCE.md) for builds and checks, and [HANDOFF.md](HANDOFF.md) for the current project priorities. Do not edit embedded data in generated HTML.

## Evidence and uncertainty

Use evidence appropriate to the claim:

1. Final official ballot proofs, sample ballots, voter information guides, and final lists explicitly identifying **on-ballot** contests establish printed ballot appearance and names.
2. Official cancellation resolutions, adopted appointment-in-lieu decisions, or certified results establishing that a June contest was resolved establish why a scheduled November contest is absent. A proposed agenda item alone does not establish adoption.
3. Official qualification lists, election notices, filing logs, and schedules establish the particular filing or scheduling facts they state. A qualified candidate may still be appointed without an election; a scheduled office may be canceled.
4. Official officeholder pages establish incumbency when they identify the same office/body sought. They do not establish ballot appearance.
5. Ballotpedia and local reporting help find and corroborate contests, candidate profiles, and contradictions. Seek primary evidence when these disagree with each other or with official records.

Inspect the document, date, election, jurisdiction, district, term, and page. Search snippets, URL filenames, an inaccessible PDF's title, or an omitted entry in a third-party guide are not substitutes for the relevant passage. Record a retrieval failure honestly; do not promote an inference to an official finding.

Treat ballot appearance and roster completeness as separate facts:

| Situation | `ballot_status` | `candidate_list_status` | `candidates` |
| --- | --- | --- | --- |
| Final appearance and complete printed roster established | `confirmed` | `complete` | Nonempty candidate array |
| Appearance established; complete printed roster unresolved | `confirmed` | `unverified` | `null` |
| Scheduled, but final appearance unresolved | `unverified` | `unverified` | `null` |
| Officially determined not to appear | `excluded` | Set from available evidence; usually `unverified` | Do not invent a printed roster |

Keep provisional names in `filed_candidates_not_confirmed_on_ballot`. They are not printed candidates. An unknown roster is `null`, never `[]`. When official evidence resolves a contest, update the status, roster, supporting sources, and contradictory or obsolete notes together. Retain an existing stable record as `excluded` with the determination rather than silently deleting useful research history.

## Per-contest workflow

1. Find the existing position by ID and by jurisdiction, office, district, and term. Cross-county coverage does not justify a duplicate. Full and partial terms can be distinct contests even when other labels match.
2. Read every relevant `source_ids` entry and `note_ids`/`candidate_list_note_id` qualification. Identify exactly which fact is missing or disputed before searching.
3. Find official November material and resolve scheduling, final appearance, seat count, term, and printed names independently. Check appointment/cancellation records for unopposed races. For a judicial or county race, determine whether June resolved it or whether a November vote remains.
4. Capture names and official ballot party preference as published. Verify incumbency for the office/body sought. A person holding a different office is not automatically an incumbent here. A campaign ending does not remove a printed name from the roster.
5. Add or reuse source and note registry entries. Preserve source dates, access/research dates, page references, and the precise reason for the update in notes and the commit description. Clearly label secondary or conflicting evidence.
6. Verify electorate membership separately from ballot appearance. Add only researched county names. Distinguish the full governing jurisdiction from the particular council, trustee, ward, or division electorate.
7. Update the JSON, applicable schema, coverage totals, and documentation that actually changed. Build and run the required checks from [MAINTENANCE.md](MAINTENANCE.md). Review the diff for unrelated factual changes.
8. In the commit or PR, state the stable IDs changed, the old/new determinations, primary evidence and document dates, and unresolved limitations. Describe testing separately from factual verification.

Do not move the global `election.research_as_of` date forward in a way that implies every contest was freshly audited after a narrow edit. Explain a partial refresh in notes/documentation, or deliberately extend the schema with per-record provenance if needed. `finance.checked_on` is a separate finance snapshot date. No existing source registry field captures an access date automatically.

## Compact field and registry conventions

- Position IDs match `CA2026-001` style (`^[A-Z]{2}[0-9]{4}-[0-9]{3,}$`). They are permanent contest identifiers; do not renumber them after sorting. Check the current registry before allocating the next unused ID.
- `sources` is an object keyed by `S` plus at least three digits. Each value is `{ "url": "https://…", "title": "optional descriptive title" }`. The schema currently permits only `url` and optional `title`; put dated provenance and qualifications in notes, not undeclared source fields.
- `notes` is an object keyed by `N` plus at least three digits, with nonempty string values. Reuse truly shared wording, but avoid changing a shared note to mean something different for its other users.
- `source_ids` is a nonempty array of source keys. Optional `note_ids` preserves the intended explanation order. All references must resolve. `primary_source_page` is text, allowing document page labels as well as numbers.
- `counties` is an array of names registered in `election.counties_in_scope`. It includes only researched counties whose residents may vote in the contest; it does not imply countywide eligibility or list every county intersecting a district.
- Use `CD-18`, `AD-18`, and `SD-18` for congressional, Assembly, and state Senate districts. Preserve source-specific local labels and distinguish full/partial terms.
- One at-large multi-seat contest has one candidate pool and a `seats` count. Do not duplicate it once per seat. `seats: null` and `term: null` mean those facts remain unknown.
- Candidate `party` uses `codes.party` (currently `D`, `R`, `G`, `NPP`). For a new official party label, add a short code to the registry. Do not assign party from endorsements or presumed personal affiliations.
- Omit `party` for nonpartisan candidates. `NPP` is an official No Party Preference label for a partisan contest, not a generic substitute for no party field.
- Emit `incumbent: true` only when supported; omit false. Omit unavailable optional URLs/notes rather than setting them to `null`.
- Retention/confirmation contests use `election_type: "retention"`, `seats: 1`, `partisan: false`, and `ballot_responses: ["Yes", "No"]`. A known roster contains the single justice, not opposing candidates.
- Qualified write-ins belong in `qualified_write_in_candidates`, with `qualified_date` and `source_ids` per candidate, plus the required contest-level write-in research/source dates and status. Absence of the field does not prove no write-ins exist. Do not mix write-ins into the printed roster count.
- Ballot measures are outside this elected-office inventory. Party central committees, U.S. Senate, police-related offices, odd-year district cycles, and June-resolved offices must be included only when evidence establishes a relevant November contest; a category requested by the user is not evidence of an election.

## Geography, OCD IDs, and expansion

An OCD division ID identifies geography, not a unique contest. `ocd_division_id` must describe the **electorate**; `jurisdiction_ocd_division_id` may describe a broader parent. Never substitute the parent when determining address eligibility.

- `ocd_id_status: "convention"` means naming-convention derived; `"verified"` requires an exact registry/authoritative verification; both require `ocd_division_id`.
- `ocd_id_status: "unverified"` means no electorate ID is supplied. A syntactically valid guessed ID is not API validation.
- If an electorate ID is present and `ocd_source_ids` is omitted, use `defaults.position.ocd_source_ids`. No ID means no inherited ID evidence.
- Dataset-wide `address_lookup.api_validated` is currently false. Do not change it merely because fixtures or schema checks pass.
- Only emit `countywide_electorate: true` when every voter in each listed county belongs to the electorate. It is currently used for certain appellate retention contests and Board of Equalization District 2; do not propagate it to every shared district.

For additional Bay Area counties, append county registry entries and extend `counties` on shared records rather than cloning them. Then audit all cities, school/college trustee areas, county boards, and special districts against official resident-ballot material. Service territory, a station location, ZIP code, or a mailing city does not establish voting eligibility. BART service in San Mateo or Santa Clara is not evidence that their residents elect BART directors.

The address matcher also has an explicit five-county `COUNTY_FIPS` map in `src/address-matcher.js`, with a county-name fallback. Updating JSON alone is not the complete county-expansion procedure: update the explicit map and verify live and fixture matching. Add official county lookup URLs, review text mentioning five counties, and update fixtures. Audit each shared BOE/appellate/school/special-district electorate before extending its counties. Do not assume all nine counties share the existing BOE district.

Congressional matching is deliberately limited to the **120th Congress** geography, and state legislative matching to **2026** boundaries. OCD IDs do not encode boundary vintage. Retain alternatives when vintage or local district membership is uncertain; do not silently narrow using the 119th Congress or mailing address. Address suggestions are not electorate evidence.

## Ballotpedia links

Verify an existing corresponding page before adding its full HTTPS URL. Omission means no match has been verified, not that no page exists. Candidate identity must match; a same-name page is insufficient. A historical candidate profile can be useful when explicitly qualified by a note and current official candidacy evidence.

For position links, use `ballotpedia_page_scope` when the available page is a broader city/county/office page rather than exact contest coverage. Do not manufacture election URLs or treat a Ballotpedia roster as authoritative when an official final roster conflicts.

## Federal fundraising

Every currently printed federal candidate has a `fec` record. Preserve this coverage when adding federal candidates. The shared `finance` object specifies provider, cycle, USD currency, metric, check date, and methodology.

- Use **FEC candidate-level total receipts** for the election cycle, preserving the source's actual coverage period. Candidate IDs (`H…`, `S…`, `P…`) differ from committee IDs (`C…`).
- Store `receipts` as a dollar number to cent precision, not a formatted string or cents integer. Zero means a reported zero; `null` means unavailable and requires a note. Never infer zero from a missing summary.
- Numeric receipts require `from`, `through`, and nonempty `committee_ids`. Unavailable receipts must not have coverage dates. Keep a source link to the corresponding FEC data page.
- Total receipts include more than donations. Do not add authorized committee totals on top of a candidate aggregate, conflate cash on hand with receipts, or include independent outside spending.
- Compare coverage dates, not just totals. Scott Wiener (`CA2026-229`) currently has a source period starting in 2023, explained in `N284`; do not silently relabel it a January 2025 onward subtotal.
- Jeff Frese (`CA2026-001`, FEC `H6CA10187`) and Charles Hoelter (`CA2026-230`, FEC `H6CA15194`) currently have unavailable totals (`N283`). A refresh should resolve official summaries if available, not overwrite null with assumptions.

## Coverage totals and verification limits

Recompute `coverage` from actual records using the definitions in `scripts/check_data.py`; there is no automatic coverage updater. In particular:

- `confirmed_contests` counts positions with `ballot_status == "confirmed"`; `confirmed_seats` sums their known seats, treating unknown seat counts as zero for this arithmetic.
- `unresolved_scheduled_contests` counts `unverified` records, independently of candidate names retained provisionally.
- `printed_candidate_entries` counts `candidates` entries, not unique people and not provisional/write-in lists. Do not assume candidates running in two contests should be deduplicated.
- `confirmed_contests_missing_candidate_rosters` counts confirmed positions whose roster status is not `complete`.
- The remaining URL/OCD coverage values count presence of the applicable fields. These counts do not certify identity accuracy or successful API matching.

County counts overlap. Their sum exceeds the number of unique positions. The checks verify data/schema consistency, referential integrity, arithmetic, and generated pages; they do not verify election truth, exhaustiveness, provider uptime, or live browser behavior. Keep unresolved evidence visible even when every check is green.

## Research queue at handoff

Snapshot from the committed inventory: **416** unique positions, **336** confirmed contests, **80** unresolved scheduled contests, and **869** printed candidate entries. Ballot research is dated October 4, 2026; finance is dated October 6. Regenerate this queue after edits.

| Priority | Work and stable records | Starting evidence already in `sources` |
| --- | --- | --- |
| 1 | Resolve final printed roster for **CA2026-381**, East Bay Regional Park District Ward 7. Appearance is confirmed, but two-name and three-name reports conflict (`N265`, `N266`). | `S494` county candidate statement; `S495` district notice; `S496` post-filing guide; `S497` Ballotpedia. Obtain final county ballot proof. |
| 2 | Retrieve Contra Costa final on-ballot proof and official cancellation/appointment determinations. **55** unresolved records intersect this county; the pre-filing schedule is not a final ballot. | `S457` county positions-up-for-election PDF. `S483` is an August 7 secondary filing report, not final proof. |
| 3 | Resolve **CA2026-327** Antioch City Clerk partial term: proposed appointment/cancellation was not verified as adopted (`N237`). | `S437` final qualification list; `S438` August 20 agenda; `S439` later agenda item. |
| 4 | Audit **CA2026-204–224**, Alameda's 21 unresolved school/special-district contests, including shared **217** AC Transit Ward 1 and **219** Byron-Bethany Division III. | `S003` county election hub; `S243` and `S345` partisan-site filing reproductions (secondary evidence); contest-specific official district sources. |
| 5 | Resolve **CA2026-225–228**, Santa Clara scheduled offices absent from the final qualified roster: Lion's Gate full and short terms, San Martin Water, Silver Creek Valley GHAD. | `S213` September 28 qualified-candidate PDF; `S214` scheduled-office notice; `N167`. |
| 6 | Resolve **CA2026-302** Bayshore Elementary short term and **CA2026-308** Colma Fire. Scheduled but absent from the September 3 qualified roster. | `S356`, `S388` / `S362`, `S400`; `N218`, `N222`. |
| 7 | Validate local electorate IDs and boundaries; refresh FEC summaries and write-in research with dated evidence. Expand to Marin, Napa, Solano, and Sonoma only with a new coverage audit. | Current `ocd_id_status`, `address_lookup` docs, federal `fec.source_id`, and county election resources. |

Preserve distinct full/short-term records when researching **CA2026-405/406** Kensington CSD. `S510` establishes three full-term seats plus one two-year vacancy seat; a seven-member board is not seven seats on this ballot (`N271`, `N272`).

Generate a current queue, including exact source URLs, from the repository root:

```bash
python3 - <<'PY'
import json
from collections import Counter
data = json.load(open('2026-11-03_Bay_Area_Elections.json'))
for county in data['election']['counties_in_scope']:
    rows = [p for p in data['positions'] if county['name'] in p['counties']]
    print(county['name'], dict(Counter(p['ballot_status'] for p in rows)))
for p in data['positions']:
    unresolved = p['ballot_status'] == 'unverified'
    missing = p['ballot_status'] == 'confirmed' and p['candidate_list_status'] != 'complete'
    if not (unresolved or missing):
        continue
    print('\n', p['id'], p['jurisdiction'], p['district_or_seat'], p['term'])
    print('status:', p['ballot_status'], '| roster:', p['candidate_list_status'])
    notes = p.get('note_ids', []) + ([p['candidate_list_note_id']] if p.get('candidate_list_note_id') else [])
    for ref in dict.fromkeys(notes):
        print(ref, data['notes'][ref])
    for ref in p['source_ids']:
        print(ref, data['sources'][ref]['url'])
PY
```
