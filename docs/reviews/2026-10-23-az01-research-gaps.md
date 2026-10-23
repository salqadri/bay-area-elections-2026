# Endorsement and Gaza research gaps — October 23, 2026

Baseline **d6238fe**, publication `2026-10-22.5`; proposed publication
**2026-10-23.1**, schema **1.23** unchanged. The [repeatable workflow](../RESEARCH_GAP_RECOVERY.md)
addresses new-race coverage, rather than hardcoding one candidate.

## Why Amish Shah's logos were missing

Shah had 30 named campaign claims from his [endorsements page](https://www.amishforarizona.com/endorsements)
but no `endorsement_images`. The actual source has **31 image occurrences under
Organizations**, all with **empty alt text**. Filename-only identity inference is
intentionally prohibited; the text extractor was therefore not a logo importer.

The publication gap was concrete: `build_queue` in `review_endorsement_images.py`
explicitly skipped every empty-county contest as `outside_reviewed_county_scope`,
including the added nationwide House races. The common publication workflow had
already gained nationwide support, but this adapter had not. The House batch also
exported image inventories without a separate image-publication draft/apply step.
Attaching its text records did not publish the exported image observations.

The builder now supports the common eligible nationwide scope, including eligible
provisional filers without promoting them. The batch runner creates a separately
reviewable image-publication draft, using a fresh run directory. A current-roster
planner finds known campaign endorsement pages with missing or older image
snapshots. The all-content policy keeps unknown images neutrally without inferred
names, political relationships, or count caps.

The initial House pass found **63 pages across 52 candidacies**. All 63 HTML pages
were retrieved; **59 were ready**, producing **1,345 neutral observations on 42
candidacies**. Four pages had unresolved image URLs. A follow-up found a real
parser gap on Michael Bouchard's page: `src` was a data GIF while actual URLs were
in `data-src-desktop-1x`. Parser v3 now preserves those explicit URLs, recovering
**39 additional observations**. Existing v2 captures stay immutable and replayable;
current ledger exports require v3 and flag old captures for recrawl.

Total: **1,384 added image observations on 43 candidacies**. Shah gains **32**:
all 31 organization logos plus one introductory campaign image. These are image
evidence entries, not 32 independently identified organizational endorsements.
No image files were copied; both readers use original external URLs.

Sam Forstag, Bob Harvie and Bill Reeside remain explicit image-layout holds: their
captures contain empty/unsupported image sources that cannot be published as
external URLs. The original queue and subsequent resolution record account for
them. There are also **271 known endorsement-page gaps/older snapshots** across
the wider roster after this scoped repair; the new planner exposes them, but this
pass does not claim to have refreshed every local campaign or every subpage.

## Hindu American PAC existed as a seed, not a live roster-wide import

The publisher was registered in `research/endorsements/sources.json`, and older
curated findings covered Melissa Hernandez plus explicitly historical local
observations. Those dated findings were not recomputed when new House races were
added. Thus Shah's [current publisher listing](https://www.hinduamericanpac.com/endorsements)
never became a named endorsement in his dataset record.

The new `import_hapac.py` parses **17 explicit current-list cards**, distinct from
old biographies and eight previous officials not up for election in 2026. It
matches the current roster and uses Jev to adjudicate exact person/office/cycle:

- **Added:** Amish Shah, Pia Dandiya, and a current renewal for Murali Srinivasan.
- **Corroborated:** Melissa Hernandez, retaining her existing current observation.
- **Held:** Yang Shao, because the source's city-council context does not establish
  endorsement of his tracked school-board candidacy.
- **Outside tracked printed roster:** twelve other current cards. No new races or
  provisional local filers were promoted.

All three additions are `endorser_statement`, phase unspecified, with the official
publisher URL and an observation-date note. Srinivasan's old historical record is
preserved separately. Campaign-site and publisher duplicates are not newly added.
The script does not identify the HAPAC logo from its filename.

## Gaza/Israel evidence: done was not published coverage

Both candidates' old collector entries were `done: true` on October 21, but both
had zero published `gaza_evidence` and no `gaza_platform`. The legacy collector
can complete with zero accepted findings, checks only the campaign homepage for
its direct campaign-text step, and caches empty source results. Its done flag
therefore cannot certify source coverage or absence of positions. Feely already
had an Israel point in **general platform research** from `/issues`; that nested
source was not fed into the Gaza disclosure.

`research_gaza_gaps.py` now audits current published gaps independently of those
flags, includes exact nested topical-platform source URLs, and provides bounded
first-party/Serper collection with explicit pending/deferred/failure outcomes.
Actual captured bytes, exact source-local quotes, author/date checks and separate
Jev identity/meaning/date decisions gate a common immutable publication review.
It does not call the legacy local extraction models or publish search snippets.

New published evidence:

- **Amish Shah:** his [October 9, 2023 post](https://x.com/DrAmishShah/status/1711221277787041963)
  supporting Israel and condemning attacks on civilians; a [July 24, 2026 Algemeiner
  report](https://www.algemeiner.com/2026/07/24/slate-of-pro-israel-arizona-moderates-emerge-victorious/)
  quoting his support for Israel's war against Hamas while describing his concern
  for civilian casualties and Jain faith; a candidate-specific [JDCA assessment](https://jewishdems.org/endorsements/)
  reporting Iron Dome funding and two-state support.
- **Jay Feely:** his [October 7, 2023 post](https://x.com/jayfeely/status/1710685934377898232)
  defending Israel's right to self-defense; his [October 7, 2025 post](https://x.com/jayfeely/status/1975691167791829139)
  calling for continued support for Israel and for Hamas to accept Trump's peace
  deal or face annihilation; his [current campaign issues page](https://www.jayfeelyforcongress.com/issues)
  pledging to stand with Israel and strengthen the bilateral relationship.

That is **five dated evidence records plus one current campaign-platform record**.
X evidence uses retrieved Fxtwitter copies of exact canonical posts, matched to
verified candidate accounts, with post IDs/snowflakes and API timestamps checked.
Older posts remain dated 2023/2025. The article date is not asserted as the policy
paper's date. JDCA uses an explicit **October 23 observation date**, not a date for
Shah's underlying statements. The undated campaign page uses `gaza_platform` with
its check date, not an invented announcement date. The collector evidence files
are synchronized to publication. Existing held grade archives remain unchanged;
new evidence requires fresh grade inputs if grades are later reviewed.

## Artifacts and validation

Four registered reviews, all additive:

- `research/reviews/house-image-gap-recovery-2026-10-23.json`
- `research/reviews/lazy-image-gap-recovery-2026-10-23.json`
- `research/reviews/hapac-current-endorsements-2026-10-23.json` and companion audit
- `research/reviews/az01-gaza-gap-recovery-2026-10-23.json` and companion audit

Normalized captures/complete dispositions: `research/endorsements/image-gaps-2026-10-23/`
and `lazy-image-gaps-2026-10-23/`. Source captures, exact proposed claims and
actual Serper discoveries: `research/gaza-stance/gap-review-2026-10-23/`. Actual
Jev requests/responses and source hashes are retained in the audits; raw HTML/API
bytes and credentials stay ignored. Jev alone supplied judgment decisions.

Printed coverage after the repair: **24,487 named relationship records on 544
candidacies**, **1,847 neutral image observations on 134 candidacies**, **309
candidacies with dated Gaza evidence**, and **222 with a Gaza platform review**.

The structural reverse comparison removes exactly **1,384 images, three named
endorsements, five dated evidence records and one platform record** on **46
candidacies**, removes the new provenance note, restores publication/coverage
metadata, and recovers the complete baseline dataset. Finance amounts/dates,
ballot rosters, existing evidence, general platforms and all prior reviews remain
unchanged. Identical registered applies are no-ops.

Validation: **all 34 release checks pass**, including **21 new gap regressions**
and the existing image/batch/publication checks; real Chrome at **1440px and 390px**.
Chrome loaded all **31 organization logos** at both widths, showed exactly one
named HAPAC entry for Shah, and rendered Shah's three evidence records and Feely's
two evidence records/current campaign section with their actual dates. No page
errors or horizontal overflow; screenshots visually inspected. Both readers'
shared rendering is also covered by the offline integration checks. Arizona's
nationwide records intentionally are not returned by Bay Area county address
matching; the real-browser AZ-01 pass used the explorer. Remote images may change
or fail later; source/image links remain available.
