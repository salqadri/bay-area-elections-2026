# Campaign-website endorsement scan — review (October 11, 2026; extended October 12)

**Result: +7,058 campaign-claim endorsement records on ~310 candidacies across 381 campaign sites.** Dataset moves to schema **1.17** with publication version `2026-10-11.3`. Total endorsement coverage is now **383 of 869 printed candidacies carrying 7,448 records**.

## What ran

`scripts/campaign_endorsements.py` (crawl → extract-llm → propose → propose-logos) plus `scripts/jev_review_proposals.py`:

1. **Crawl.** Each printed candidacy's own campaign site (`campaign_url`) was fetched and cached in `.research/endorsements/campaign.sqlite3` (never in Git). 366 sites crawled, 700 pages captured; 15 sites failed (403 bot-walls, broken TLS chain, or JS-only rendering) and remain explicit limitations — no results were guessed for them.
2. **Extract.** LM Studio `qwen/qwen3.8-27b` (medium reasoning, concurrency capped at the server's 2 parallel predictions) read each site's cached text plus its image inventory (src | alt | nearby text). No vision model was used anywhere: logo-only endorsements without a readable name became `unidentified_logos` leads (76 captured), never guesses. The model may only return endorser names appearing verbatim in the page text or image labels.
3. **Quote gate.** 12,095 proposals; every record's quote is re-checked mechanically against the cached snapshot — 11,707 passed (`quote_verified`), 388 failed and stay unapplied.
4. **Jev triage.** Each surviving entry was classified by TypeSafe Jev (`jev-1.13`, `/v1/systemone` choice questions) as a genuine endorsement of that campaign's candidate versus page noise (staff/volunteer rosters, donor thank-yous, ballot measures, the candidate endorsing others, same-race rivals). Calibration found entries must ride in each question's instructions — lumping them into `state` degrades batch accuracy. Accept required Jev `endorsement` with p ≥ 0.75: **4,385 accepted; 7,161 held** (conservative by design — held records stay in the ledger for later review and were not published). Spot checks confirmed correct rejection of primary opponents, staff titles, and rival candidates listed on shared pages.
5. **Attach.** Accepted records were deduplicated against existing endorsements (28 skipped) and attached with `verification: campaign_claim` plus an explanatory note per contributing site, matching the convention of hand-reviewed claims. 744 records carry a display-only `logo_url`, accepted only when it exactly matches an image src from that site's captured inventory (path percent-encoded for schema URI compliance).
6. **Logo filenames (`propose-logos`, added after owner review).** The first pass missed endorsements displayed as org logos with no alt/nearby text — e.g. Scott Wiener's CD-11 page, where every organization appears only as an image. No vision model is used: campaigns name their logo files after the endorser (`SEIU Local 87.png`, `Sierra Club Endorsement Seal_Color-1.png`), and a filename is campaign-published readable text. A mechanical slug filter derives candidate names from image filenames (dropping icons, headshots, screenshots, hex/CDN artifacts, copy counters and years) and emits `filename_gate` proposals carrying the verbatim filename as quote plus the logo URL — 2,215 across the ledger. Jev triaged each with a filename-aware question ("the campaign named this logo file X; plausible endorser or page furniture?"): **406 confident accepts** (Wiener gained 24 including Sierra Club, AFSCME, CSEA, LIUNA CSCL, SEIU Local 87, J Street PAC, EqualityVotesPAC, Moms Demand Action, SF Dems), 995 confidently rejected as staff/event/asset files, 814 held. Their explanatory notes state explicitly that the name comes from the image filename, not readable page text or image analysis.

## What this means on the pages

- These are **campaign claims**: the campaign's own site names the supporter. They are not independent confirmation with the endorser, never change official party preference, and are labeled as such by both readers (`Campaign claim` provenance label; per-site explanatory note).
- Election phase stays `unspecified` unless stated on the page.

## Limits / what remains uncertain

- ~~15 campaign sites could not be read~~ **Recovered October 12:** browser-UA retry + Internet Archive fallbacks are built into `crawl`, and `scripts/render_failed_sites.py` renders JS-only/bot-walled sites with headless Chromium (per-site context isolation; media-blocked retry for renderer-crashing animated sites). All 381 known campaign sites are now crawled.
- **Oversized endorsement walls silently returned nothing** from the model (prompt overflow) — fixed October 12: prompts over 45K chars split into a text pass + an image pass, doubled alt-text is deduped, and malformed JSON from long outputs is salvaged entry-by-entry. This recovered 20 sites including Connie Chan's CD-11 page (Pelosi, Schiff, Boxer, Khanna + union wall) and Ben Allen's 414-endorser page; every recovered entry still passes the quote gate and Jev triage.
- The ~11,300 held proposals are extraction candidates Jev did not confidently classify; they need human review before any future publication.
- Named private individuals (`kind: other`) inherit the campaign's own framing; titles shown are identification-only.
- Logo images hot-link from campaign sites (display evidence only); if a site removes an image, the endorsement record and its text quote remain intact.

## Reproduce / extend

```sh
sh scripts/run_campaign_scan.sh                 # resumable crawl (+render fallback) + extract pass
python3 scripts/render_failed_sites.py          # headless-Chromium render of JS-only sites (needs playwright)
python3 scripts/campaign_endorsements.py propose
python3 scripts/campaign_endorsements.py propose-logos   # logo-filename endorsements
TYPESAFE_API_KEY=*** python3 scripts/jev_review_proposals.py   # writes decisions JSON
python3 scripts/campaign_endorsements.py apply-review .research/endorsements/review/campaign-jev-decisions.json
python3 scripts/campaign_endorsements.py attach --output <candidate-dataset>
```

The API key lives only in the environment; it is never written to source, packets, logs, or generated HTML.
