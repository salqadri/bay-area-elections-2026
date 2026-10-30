# Candidate recommendations

Current source-selection follow-up: [publication 2026-10-29.3 and the v4 prompt](SUMMARY_SOURCE_POLICY.md). Historical rules and publications below remain archived.

Current publication **2026-10-29.1** recommends down through a **D**: a race whose
best graded candidate is a D now gets a pick (owner rule, October 29, 2026 — e.g.
Sam Liccardo, CD-16); races whose graded candidates are all E or F keep the explicit
no-recommendation line.

Publication **2026-10-28.5** renders recommendations **inside both readers**:
every confirmed race in [Explore all races](../index.html) and every ballot result in
[Find my ballot](../ballot.html) shows the pick, the Muslim-community badge, or the
explicit no-recommendation line, with a Qwen-written why-paragraph. The standalone
recommendations reader is retired.

Historical publication **2026-10-28.1** added a standalone recommendations page;
**2026-10-28.4** refreshed choices and grades against the owner's full-roster v7 rerun.

## Rules

For each race in the current dataset (539 evaluated races: 471 confirmed on the November
ballot, 68 recorded but confirmed not on it), in order:

1. **Muslim community first.** A candidate whose Muslim-community membership is confirmed
   in the [community-observations registry](../research/candidate-community/observations.json)
   (12 races) is recommended outright; the card states "Confirmed member of the Muslim
   community."
2. **Jev decides.** Otherwise, the Jev decision model
   (`jev-latest`, via the Typesafe Jev API) reads each graded
   candidate's name, party, and published letter grade from the [pro-Palestine score
   publication](PUBLISHED_GRADES.md) plus the race context and picks the candidate to
   support (160 races). Single-candidate rosters are short-circuited locally at 100%
   confidence without a model call. The model's choice is archived with confidence,
   request hash, and timestamp; a different answer is never silently overwritten.
3. **No grades → no information.** Races where no candidate has a political grade
   (285 races) display "No recommendation due to a lack of information about this race."
4. **Only E/F grades → no known good candidate.** Races whose graded candidates all
   sit below a D — grade E or F (82 races) — display "No recommendation due to a lack
   of known good candidates." A D as the best available grade IS recommended
   (owner rule, October 29, 2026).

Jev never sees raw evidence; it chooses from the published grades only.

## Recommendation reasons

Each recommended race (172) carries a voter-facing why-paragraph (≤200 words) generated
by `qwen/qwen3.8-27b` (medium reasoning, concurrency 2) from the candidates' textual
records — published explanation summaries, Gaza evidence with dates, platform positions,
and the relevance-filtered endorsement lines — under the owner framework:

- The two litmus tests lead: opposing the genocide in Gaza and ending U.S. military/economic
  aid to Israel. Concrete acts (Block the Bombs cosponsorship, arms-funding votes, genocide
  language, divestment) are named specifically with dates/bill names as shown.
- When the recommended candidate's shown record lacks litmus-test acts, the paragraph states
  that shortfall plainly, then explains why the candidate is still the best option listed —
  never hide a shortfall, never invent one. In federal races, no recorded position is
  described as supporting the status quo.
- Silence is a ding, not neutrality: a candidate who was put in the position and refused to
  properly support Palestinians is held to it; an abstention under pressure reads as
  qualified support only when the shown assessment says so.
- No numeric scores or ratings ever appear; letter grades at most in passing.
- Endorsements may be named only when Muslim-community/pro-Palestine-aligned (CAIR Action,
  BAMC Action, AROC Action, Vote for Peace, Ro Khanna and similar) or Israel-aligned /
  AIPAC / Hindu-nationalist-aligned (AIPAC, UDP, DMFI, ICAN, JStreetPAC and similar) —
  never any other backer.
- Grounding only: no outside knowledge, no invented events, dates, quotes or endorsements.

Paragraphs are cached by exact prompt hash in
`research/candidate-recommendations/race-reasons-2026-10-28-latest.jsonl` with model
provenance and word counts; a prompt or record change regenerates only affected races.

## Reproduce

```sh
python3 scripts/build_recommendations.py refresh    # current grades + Jev choices; defer narratives
python3 scripts/build_recommendations.py classify   # community + grade gates
python3 scripts/build_recommendations.py jev        # Jev picks (cached, resumable)
python3 scripts/build_recommendations.py reasons    # Qwen why-paragraphs (prompt-hash cached)
python3 scripts/build_recommendations.py build      # validate plan + rebuild index.html and ballot.html
python3 scripts/check_recommendations.py            # plan/reader binding regressions
```

Jev requires the `JEV_API_KEY` environment variable (or `--jev-key-file`). Cached answers
are keyed by exact request, so rule or roster changes trigger only the affected calls.

## Files

| File | Responsibility |
| --- | --- |
| `research/candidate-recommendations/recommendations-2026-10-28-latest.json` | The frozen recommendation plan (rules, counts, per-race decisions, per-race why-paragraphs) |
| `research/candidate-recommendations/jev-answers-2026-10-28-latest.jsonl` | Archived Jev decisions with confidence and request hashes |
| `research/candidate-recommendations/race-reasons-2026-10-28-latest.jsonl` | Archived Qwen why-paragraphs with prompt hashes and model provenance |
| `scripts/build_recommendations.py` | The four-stage pipeline (classify → jev → reasons → build) |
| `src/recommendation-display.js` | Shared race-recommendation box for both readers (display only): the why-paragraph auto-expands and remembers an explicit collapse/expand via localStorage across races; the note carries only the recommendation-set date — no model attribution |
| `index.html` / `ballot.html` | Generated, committed readers carrying the embedded recommendation map |

## Limits

- Recommendations inherit the grade publication's evidence base: a candidate marked N/A
  there is invisible to the Jev decision.
- "Muslim community" uses the owner-curated registry only; no web-discovered claims are
  used for the recommendation itself.
- The readers are display-only; all decisions are pre-computed and archived. The embedded
  map is a plan projection bound by plan SHA — neither page derives or reranks anything.
