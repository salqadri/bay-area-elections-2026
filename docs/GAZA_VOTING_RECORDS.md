# Gaza legislative tracker and candidate identity links

The [Congressional Democrat Palestine Tracker](https://docs.google.com/spreadsheets/d/1VU1y_jSb2hanU2MrLsjRx8tujB-C--UAQ2EahaTXGUo/edit?gid=1984730710#gid=1984730710) supplies a source-selected history of legislative actions. Its authors describe themselves as anti-Zionist DSA comrades. Preserve that attribution and the source's wording: its positive/negative assessments are the tracker's assessments, not independently assigned candidate verdicts.

The October 14 capture is [voting-records-2026-10-14.json](../research/gaza-records/voting-records-2026-10-14.json). It contains all member rows and all tracked legislative-action columns in four tabs, including the hidden historical tabs:

| Tab | Member rows | Tracked actions | Member/action cells |
| --- | ---: | ---: | ---: |
| 119th House | 214 | 64 | 13,696 |
| 119th Senate | 47 | 23 | 1,081 |
| 118th House, hidden | 211 | 49 | 10,339 |
| 118th Senate, hidden | 51 | 14 | 714 |
| Total | 523 | 150 | 25,830 |

These are member records in each tab, not 523 unique people. The 150 columns comprise 127 roll-call votes, two committee votes, 15 sponsorship records, one discharge-petition signature, three letters and two statements. A sponsorship, letter or statement must never be presented as a roll-call vote. The tab's Congress number identifies the source roster/context; both current tabs include earlier actions, some dating to 2011. Display the actual action date beside the tab context. Historical actions can appear in both tabs: 41 source URLs are repeated across tabs, so counts are source entries, not unique votes. This source does not supply every congressional vote, every Congress, Republican members generally, or state/local legislative history.

Every one of the 253 source columns has an explicit disposition and its original header text, header links, dates and notes in the local snapshot. Grades, ranks, aggregate scores, endorsements, funding totals and unsourced summary columns are excluded from the action records. The experiment and demographic tabs are not legislative sources and are not imported. The sheet's Column A grade is **never** used as a USCPR grade; the separate official USCPR capture is the grade source.

## Source values and colors

`scripts/gaza_voting_records.py` uses only Python's standard library. It reads XLSX values, comments, links and fills, and evaluates the reviewed text conditional-format rules in priority order. Current Google Sheets dropdown chips have their own background colors that are missing from XLSX exports and from the Sheets API's `effectiveFormat`. The adapter therefore also reads each current tab's complete public `htmlview/sheet` grid, verifies every rendered action value against its XLSX cell, and captures that cell's chip color. The ordinary `edit` page includes only the first 100 rows and is rejected as incomplete. The current House's hidden BS:BU letters/statements retain XLSX cell fills instead of visible dropdown chips.

Each action value retains its exact source text, `sheet_color`, `assessment` and `assessment_basis`. The reviewed palette maps green shades to `positive`, red shades to `negative`, and yellow/gray shades to `neutral`. Unknown colors stay `unclassified`. The UI can use accessible pale green/red equivalents while retaining the exact source color in the JSON. Text labels accompany colors. Crucially, the adapter does not assume that a Yes vote is positive: `Yes` and `Yes (correct)` have different colors in the source, as do sponsorship and reverse sponsorship options. An explicit `(correct)` or `(incorrect)` label can supply the assessment only if no source color is available. Blank cells remain unclassified even if their background is colored. Blank, zero, `N/A`, `Not elected`, `Not voting`, `Present` and `Not on committee` remain distinct values.

The public JSON contains no search credential, Google credential, spreadsheet session or address input. Raw workbooks and HTML remain in ignored `.research/` storage. The committed normalized capture records each input URL, byte count and SHA-256 hash, plus the date checked. It does not claim that every tracked legislative description or value was independently checked against a primary roll call.

## Reviewed candidate identity links

[candidate-links.json](../research/gaza-records/candidate-links.json) explicitly binds a printed candidacy to a source member name, source tab and historical district. A 2026 district sought does not establish a prior congressional district or the identity of that district's former officeholder. The importer does not attach by surname, by FEC ID, by a shared district, or by an unreviewed name match. Duplicate source names, missing candidates, unreviewed links or changed source districts stop the preview.

The reviewed links cover 11 printed candidates and 18 tab records: John Garamendi, Josh Harder, Mark DeSaulnier, Lateefah Simon, Kevin Mullin, Sam Liccardo, Ro Khanna, Zoe Lofgren, Jimmy Panetta, Barbara Lee and Aisha Wahab. Lee's prior House record is attached to her Oakland mayoral candidacy. Her [campaign biography](https://barbaralee4oakland.com/about) connects the Oakland candidate to her congressional service; the [official 2024 House roll call](https://clerk.house.gov/evs/2024/roll477.xml) identifies Lee (CA), L000551. Other member identities are corroborated against the [official September 3, 2026 House roll call](https://clerk.house.gov/evs/2026/roll295.xml).

Wahab requires particular care. The [House Clerk member page](https://clerk.house.gov/Members/W000832) identifies Aisha Wahab, CA-14, with an oath on September 2, 2026; the September 3 roll call records her Nay vote. The tracker has her new actions and marks older actions `Not elected`. The older official USCPR feed still names Eric Swalwell under the same publisher identifier, so that grade must **not** transfer to Wahab. Match publisher grades by the reviewed person's name and service as well as any identifier. The snapshot preserves this limitation rather than inventing a grade.

Xavier Becerra's earlier House service is outside these tab rosters. His absence is recorded as an uncovered historical record, not as no voting history or a position on Gaza. A separate historical source is required to extend that coverage. Senate records are retained nationally even though this ballot inventory has no U.S. Senate contest.

## Refresh and preview

Run from the repository root, or call the script using its absolute path from another directory. The capture and preview commands do not edit the canonical election dataset, commit, push or publish.

```sh
python3 scripts/gaza_voting_records.py capture \
  --checked-on YYYY-MM-DD \
  --output .research/gaza-records/voting-refresh.json

python3 scripts/gaza_voting_records.py preview \
  --snapshot .research/gaza-records/voting-refresh.json \
  --output .research/gaza-records/voting-preview.json
```

The capture fetches the public workbook and two complete current-tab HTML grids. Use the actual retrieval date in the maintainer's timezone; do not carry forward October 14 when fetching later. Without network access, supply the same exported workbook and color captures:

```sh
python3 scripts/gaza_voting_records.py capture \
  --xlsx .research/gaza-records/source.xlsx \
  --html-dir .research/gaza-records \
  --checked-on YYYY-MM-DD \
  --output .research/gaza-records/voting-refresh.json
```

The HTML directory must contain `119th-House.html` and `119th-Senate.html` retrieved from the exact `color_sources[].url` addresses in the snapshot. Workbook and HTML values must agree. A login page, missing/renamed tab, missing identity row, new populated cells outside the reviewed dimensions, unsupported conditional rule, partial grid, changed headers or conflicting values stops collection before replacing the previous output. Outputs use atomic replacement only after the full capture succeeds.

The default layout baseline is the committed October 14 snapshot. When the sheet adds an action or changes its headers, review and update the adapter's tab dimensions, action-kind ranges, column dispositions and tests before explicitly accepting the new layout with `--accept-layout`. That switch only approves header-layout differences; it does not bypass identity, completeness or value checks. Never use it as a routine error workaround. After adopting a new snapshot, name it by its actual date and use `--baseline` to point later captures at that reviewed version.

`preview` returns shared `gaza_voting` metadata/actions and exact candidate `before`/`after` records; the public API is `gaza_voting_records.preview(data, snapshot, links)`. Publication is handled by the combined [sync script](../scripts/sync_gaza_records.py) and the common reviewed-update workflow, not by direct candidate mutation in this adapter. Inspect the combined review, source freshness, identity changes and changed assessments before applying; register the review, bump publication version, rebuild both readers and run the full release gate. The collector's prose evidence and official USCPR grade feed remain separate sources.

```sh
python3 scripts/check_gaza_voting_records.py
```

The offline regressions cover all tabs and columns, inverted Yes/No colors, historical conditional formatting, blanks versus zero/`N/A`, stale/partial HTML, layout drift, malformed input preserving prior output, explicit identity binding and ambiguous or stale identities. They verify the adapter, not every remote political fact.

## Reader ordering and Jev input assessments (October 26, 2026)

Publication **2026-10-26.6** retains every source tracker record on both public
readers. Exact dated actions are sorted newest first across tracker tabs, rather
than grouping historical 2011 actions ahead of newer votes from another tab.
Each action still names its tracker tab and retains its exact response,
assessment, notes, primary link and cell-specific sheet link. Source member,
district, snapshot date and complete tab counts remain in **Source tracker
snapshots**. Period-only or undated entries follow the dated actions in a
separate disclosure; a Congress-wide range is not treated as a vote timestamp.
Equal-date entries preserve source order, including distinct tab observations of
the same historical action.

The shared Jev state builder now includes the raw `sheet_assessment`, explicit
`alignment_with_tracker`, `assessment_basis`, `action_id`, source tab and date
precision for each retained action. A once-per-state assessment key attributes
this perspective to the Congressional Democrat Palestine Tracker:

| Sheet assessment | Alignment supplied to Jev |
|---|---|
| positive | aligned |
| negative | not_aligned |
| neutral | neutral; no inferred opposition |
| unclassified or absent | unknown; no inference from Yes/No |

For example, Garamendi's `119-house-AK` response is **No**, with sheet assessment
**positive** and alignment **aligned**. A Yes vote is not automatically aligned.
Neutral, unclassified, Not voting, Not elected and blank responses stay distinct.
This carries the existing sheet's assessment; it does not create a new political
judgment or alter any stored source record.

**Only Jev's legislative-tracker input** is restricted to **December 1, 2023 and
later**, inclusive. Date filtering uses each action's date, never its Congress,
snapshot/retrieval date, title, or a guessed timestamp. A range must start on or
after the cutoff; `2023-2025` and year-only `2023` cannot establish that and are
omitted. `2025-2027` is retained as a period-only observation, after exact dated
actions, with its original label. Unknown or invalid dates are omitted. This
cutoff does not remove historical prose evidence or aggregate publisher grades.

The current 11 candidacies with tracker records retain **596 of 1,032 source
entries** in generated Jev state. Garamendi retains **64 of 113**: 32 positive,
27 negative and five neutral. The public readers retain all 1,032 source entries.
Saved Jev inputs, scores, prompts, responses and explanations are unchanged;
no scorecards were rerun. New input versions are
`candidate-evidence-v9-legislative-assessments` and
`candidate-evidence-v9-local-federal-legislative-assessments`.

Python `scripts/legislative_actions.py` and the shared reader's date parser use
[the same calendar fixtures](../research/gaza-records/action-date-fixtures.json).
Regressions cover the cutoff boundary, range ambiguity, invalid dates, inverted
Yes/No assessments, neutral/unknown values, cross-tab ordering and unchanged
source data. The local playground's **Current input** tab previews these new
inputs; **State JSON** continues to show the exact input of the saved evaluation.

Validation for publication 2026-10-26.6: **44/44 release checks pass**.
Desktop/mobile Chromium checks confirm Garamendi's 64 assessed Jev inputs and
all 113 public tracker entries in descending date order on both readers, with no
scoring requests or page errors. The 118 existing local run files remain
byte-identical. The canonical source data, grades and explanations are unchanged
apart from the publication marker.
