# Historical Gaza evidence and the Khanna chronology correction

Prepared publication **2026-10-27.9** preserves public historical research,
expands new Jev legislative inputs to **November 1, 2023**, and refreshes only
Ro Khanna's narrative. Numeric Jev scores, thresholds and scoring requests are
unchanged. Khanna remains **A (4.71/5)**.

## What went wrong

The initial collection found the official office's February 9, 2024 repost
GE-0146, but missed earlier sources. The repost itself describes continuing
advocacy; its publication date does not establish when support began. A later
summary said “as early as February 2024,” making the incomplete collection sound
like an established timeline. There was no November Khanna record to restore
in the **98 mainline dataset revisions** inspected.

Two newly captured sources establish support in November:

- [November 21 verified post](https://x.com/RoKhanna/status/1726990658861511135):
  Khanna backed making the negotiated multi-day ceasefire permanent, linked to
  hostage releases, aid and ending violence. The exact ID, verified author and
  snowflake/API timestamps agree. GE-1536 says **by November 21**, not first ever.
- [November 26 ABC interview](https://abcnews.com/Politics/week-transcript-11-26-23-white-house-national/story?id=105156072):
  he called for a ceasefire now, said he had come out for it days earlier, and
  clarified “lasting ceasefire.” The interview date is distinct from that earlier
  call. GE-1537 retains this qualification.

GE-0146 is retained with its actual page date and a qualification that it is a
later repost, not the onset of his stance. All three source observations passed
Jev identity, meaning and date review; exact raw captures/retries stay under
ignored `.research/early-gaza-2026-10-27/`. The registered review and portable
actual decisions are in `research/reviews/early-gaza-chronology-2026-10-27{,.audit}.json`.

## Date policies

There was no global December 2024 deletion rule. Before this correction, only
Jev's **legislative actions** had a December 1, 2023 lower bound. At the owner's
request, that bound is now **2023-11-01**, inclusive. Newest-first ordering and
source assessments remain unchanged. Unknown dates and periods beginning before
the boundary do not establish an eligible action date.

This filter is a model projection. It never mutates the public candidate record
or removes older actions from either public reader. Separately reviewed direct
statements are not subject to that legislative-only filter. Their date
qualifications now survive compact Jev projection as `Date context`, so a report
or republication date cannot silently become a claimed first statement. The
organization-only funding policy still begins January 2024; it is not a general
cutoff for public statements.

New states are **v16**. Compared with the saved v6 numerical inputs, **56**
candidates gain expanded legislative/context inputs, including **95** additional
legislative actions. See `research/gaza-grading/historical-state-impact-2026-10-27.json`.
These are future-input changes; no numerical scorecards were rerun here.

## Public-history audit

`python3 scripts/audit_historical_gaza.py --start 2023-10-07 --end 2023-12-31
--output .research/NEW/history.json` is a read-only Git-history audit. Use a new
output path. It reports missing IDs as research leads; it never republishes them
or overrides source holds.

The October 27 audit found **142** historical Q4 candidate/evidence IDs, **128**
retained and **14** removed. Each removal was checked: duplicates, unestablished
or wrong identities, third-party protest activity without the candidate's own
position, or unstable/bare-profile sources. None was removed by a model date
cutoff. Cherise Khaund's removed tracking-URL variant is still represented by
GE-0261 with the same October 11, 2023 quote. Those legitimate holds and dedupes
remain intact. The reviewed dispositions are in
`research/reviews/early-gaza-history-2026-10-27.json`.

## Narrative refresh and future safeguards

At the owner's explicit request, only Khanna's paragraph was regenerated using
**GPT-6.1 Sol / low** with the complete corrected record. This is a one-off model
choice; Hermes's default Qwen configuration is unchanged. The generation input
and output are archived as `ro-khanna-summary-{input,output}-2026-10-27.json`,
including the prompt, current state, associated old numerical answers and all
100 evidence-audit rows. The new explanation archive is
`explanations-2026-10-27-v6-chronology.json`; **1,295** other paragraphs are exact
copies of the latest main archive.

A summary-only refresh must not substitute new research into the old numerical
scoring request. `summary_refreshes` binds the separately archived generation
input/output by SHA-256 and verifies their candidacy, old score request, questions,
answers, displayed grade, generating model and actual paragraph. Old Qwen and
scoring archives remain immutable.

Discovery v5 and the legacy enrichment query now explicitly search October–November
2023. Cache fingerprints change. Extraction and summary guidance forbid inferring
first/earliest support from the earliest collected item or a later repost. Keep
source verification and identity checks; a search result is only a lead.
