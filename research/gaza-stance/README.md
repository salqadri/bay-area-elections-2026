# Gaza Stance Research (evidence collection)

Evidence-only research layer for the November 3, 2026 Bay Area ballot inventory.
Collects **dated, linked evidence** of each candidate's record on Israel / Gaza /
Palestine: genocide recognition, war-crimes language, military aid & arms sales,
AIPAC and pro-Israel funding, ceasefire votes, framing/balance.

**No grades are stored here.** A future A–F grading step will consume these files.
Grading rubric (for reference only): A = openly against the genocide and Israeli
military assistance; B = says "genocide" but leaves reset room (blames Netanyahu);
C = refuses "genocide", uses war-crimes language; D = condemns humanitarian harm
only; E = Israel-centric framing with sympathy for Palestinians; F = shields Israel.

This collector and its ledger live **inside the election repository** at
`research/gaza-stance/` (moved from the external `/workspace/gaza-stance-research` on
2026-10-15). All paths resolve relative to this directory; the dataset is read at
`../../2026-11-03_Bay_Area_Elections.json`. `xhunt2.py` is a vendored copy of the shared
X-handles helper. Raw page/FEC caches under `raw/` are gitignored — they are regenerable
captures, not evidence records; `evidence/`, `ledger/`, code and tests are versioned.

## Layout

- `gaza_research.py` — resumable collection pipeline (see below)
- `ledger/state.json` — per-person stage flags (`x`, `fec`, `site`, `wiki`, `web`)
- `evidence/<name>|<party>.json` — append-only evidence lists, deduped by URL
- `raw/x|fec|wiki|pages/` — cached raw pulls; never refetched once present

Evidence item: `{id: GE-NNNN, person, date (YYYY-MM-DD|YYYY-MM|YYYY|null), url, domain,
summary (one line of what it conveys), quote, dimension, source_kind, checked_on}`.
Dimensions: `genocide_language | war_crimes | military_aid | aipac_funding |
framing_balance | actions_votes | other`.

## Pipeline stages per person (all resumable)

1. **x** — recent timeline via Twitter syndication endpoint (no auth), keyword-filtered
2. **fec** — full Schedule A receipts for the candidate's committee(s); scan for
   pro-Israel PAC/contributor names (regex list `PRO_ISRAEL`)
3. **site** — campaign website; jev gate then flash-low extraction if stance-relevant
4. **wiki** — Wikipedia summary + article text, keyword-gated extraction
5. **web** — serper.dev Google searches (`gaza genocide`, `Israel Palestine ceasefire`,
   `AIPAC`, `site:x.com <handle>`); jev relevance prefilter; flash-low extraction of ≤2 pages/query

LLMs run on a local LM Studio server; the extractor is `qwen/qwen3.8-27b` (medium
thinking). Configure via environment, never commit secrets:

- `GAZA_LMS_URL` — OpenAI-compatible endpoint (default `http://127.0.0.1:11434/v1/chat/completions`)
- `SERPER_KEY_FILE` / `FEC_KEY_FILE` — key-file paths (default `~/.config/gaza-research/{serper,fec}_key`)

## Usage

```bash
python3 gaza_research.py --county "San Francisco"          # one county pass (resumable)
python3 gaza_research.py --county "Santa Clara" --limit 10 # smoke test a new county
python3 merge_subagent_evidence.py file.json               # merge agent-produced items
```

People are keyed by `norm_name(name)|party` — **not** by county — so statewide and
cross-county candidates researched once are never repeated. Re-running any county
skips completed stages; kill it anytime and resume.

## Dates are mandatory

Every evidence item must carry a date (schema 1.10 requires `date`); an undated
item cannot establish stance evolution and is never merged. Recovery order, all
deterministic (`date_resolvers.py`, tested in `tests/test_date_resolvers.py`):
X/Twitter snowflake ID → page metadata (og/meta/JSON-LD/`<time>`) → Wayback
metadata; for static pages with no stated date, `date_content_first_seen.py`
binary-searches captures for the earliest containing the claim keywords and
records that capture's YYYY-MM as an upper bound. Items still undated go to
`ledger/undated_quarantine.json` (skipped by `add_evidence`, reported) instead of
the ledger; `merge_gaza_evidence.py` also refuses dateless items. Retrofits:
`backfill_dates.py` + `date_first_capture.py`.

## Status

- **All five counties complete** (base + `--enrich` depth passes for all 861 tracked people; enrichment finished 2026-10-09 under the post-audit acceptance rules — logs in `enrich_run.log`). After three review passes (two Hermes audits + Codex PR #1 per-item summary review) and full reconciliation: **231 dated items / 81 people** — the ledger mirrors `docs/reviews/evidence-quarantine.json` in the election repo, which is the authority for holds; quarantine file now 179 entries. Merged and published ungraded into the election dataset as `gaza_evidence` (schema 1.11: every item carries a calendar-valid date + `date_method`, optional `date_note`). Further enrichment has hit diminishing returns; remaining work is targeted follow-up on high-salience federal/statewide dossiers
- **Acceptance rules** live in `validate_evidence.py` (hard quarantine + soft review flags via `ledger/review_flags.json`); apply them to existing output with `revalidate_ledger.py`, regression cases in `tests/test_validate_evidence.py`. The extraction prompt now requires an identity link between source and candidate office/jurisdiction before any item is proposed
- Post-run review quarantines same-name misattributions and non-evidence items into `ledger/undated_quarantine.json` with a reason (**111 entries** as of 2026-10-09); the merge removes dataset evidence whose ledger entry is gone. Scan new local-candidate items for far-away place names after each county run — the LLM extractor does not check candidate identity against geography
- Second-review rules (October 9): collective statements/current rosters never establish an individual co-signature (contemporaneous membership + explicit attribution required); a relevance regex gate with cached-page-text fallback keeps only Israel/Gaza/Palestine items; `normalize_url()` dedupes tracking params/fragments/trailing slashes; `$None`-style failed extractions rejected. Regression cases in `tests/test_validate_evidence.py`
- Evidence from sub-agent deep dives is merged with `source_kind: "agent"`.
