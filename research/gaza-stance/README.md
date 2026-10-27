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
thinking; the flash-next GGUF ignores reasoning-effort hints). Respect the GPU
limits: at most four concurrent LM Studio calls across everything running,
including work launched by other agents; prefer script passes to agent fan-out.
Configure via environment, never commit secrets:

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

- **October 25 divestment repair:** added one historical Fiona Ma interview
  observation through source-bound Jev review: **1,050 dated items across 333
  printed candidacies**. Legacy logs show a timeout and zero-item passes despite
  a done/enriched flag. The current gap workflow now separates divestment/BDS
  searches and retains those discovery leads. See the
  [diagnosis](../../docs/reviews/2026-10-25-evidence-sufficiency-and-fiona-ma.md).
  This targeted repair does not certify comprehensive research for other candidates.

- **October 23 gap repair:** publication and this evidence ledger contain **1,013 dated items across 309 printed candidacies**. Shah gains three source-attributed items and Feely two; Feely's current campaign statement is separately stored in `gaza_platform`. The new [gap workflow](../../docs/RESEARCH_GAP_RECOVERY.md) checks current published fields and nested topical sources instead of treating old `done` flags as proof of coverage. It uses Serper for searches and Jev for judgments; no new grades are published. The counts below describe earlier snapshots.

- **October 14 manual audit:** the ledger then mirrored **245 dated items / 82 candidacies**, including the 14 earlier guide observations, three restored Panetta statements and three additional ceasefire-related observations. Six syndicated/uncertain records are held or deduplicated; one retained Bachelor summary now explicitly identifies its Gaza context. The quarantine history has 186 entries, including three resolved Panetta holds whose original reasons remain preserved. See [the review](../../docs/reviews/2026-10-14-gaza-and-finance-review.md). No new model collection ran in this audit; these counts do not certify exhaustive research.
- **Earlier collection:** all five counties had base + `--enrich` depth passes for the then-tracked 861 people; enrichment finished October 9 under the post-audit acceptance rules (logs in `enrich_run.log`). Before the guide/audit reconciliation, the corrected ledger had 231 items under 81 people. The publication uses the current schema's full calendar dates and date provenance. Further collection should target unresolved dossiers rather than repeat the broad enrichment pass.
- **Acceptance rules** live in `validate_evidence.py` (hard quarantine + soft review flags via `ledger/review_flags.json`); apply them to existing output with `revalidate_ledger.py`, regression cases in `tests/test_validate_evidence.py`. The extraction prompt now requires an identity link between source and candidate office/jurisdiction before any item is proposed
- Post-run review quarantines same-name misattributions and non-evidence items into `ledger/undated_quarantine.json` with a reason (**111 entries** as of 2026-10-09); the merge removes dataset evidence whose ledger entry is gone. Scan new local-candidate items for far-away place names after each county run — the LLM extractor does not check candidate identity against geography
- Second-review rules (October 9): collective statements/current rosters never establish an individual co-signature (contemporaneous membership + explicit attribution required); a relevance regex gate with cached-page-text fallback keeps only Israel/Gaza/Palestine items; `normalize_url()` dedupes tracking params/fragments/trailing slashes; `$None`-style failed extractions rejected. Regression cases in `tests/test_validate_evidence.py`
- Evidence from sub-agent deep dives is merged with `source_kind: "agent"`.

## Manual corrections and safe merging

The repository quarantine and immutable publication reviews govern published evidence. Apply new manual findings through `scripts/reviewed_updates.py` from the repository root, then copy those reviewed records and holds back into this ledger:

```bash
python3 research/gaza-stance/merge_gaza_evidence.py --sync-published --dry-run
python3 research/gaza-stance/merge_gaza_evidence.py --sync-published
python3 research/gaza-stance/revalidate_ledger.py --dry-run
python3 scripts/check_gaza_ledger.py
```

Synchronization refuses to discard unknown draft items. Review those through the common capture/review workflow first. The merge rejects missing or replaced publication records, unresolved quarantined sources and invalid dates before writing. It preserves `source_observed` guide dates and full summaries; it cannot silently remove manual guide observations. A reconciled merge is a dataset-preserving round trip. Raw source caches are not required for these offline regression checks, and the deterministic rules still require human identity/context review.


## Funding chronology repair — October 26, 2026

Seven Track-JPAC observations were replaced through an immutable source-bound
review and synchronized back into this ledger. Haney’s PAC row covers 2021–2023;
the old 2025 label borrowed another donor’s endpoint. All seven summaries now
separate donor periods, individuals and analysis dates. Do not restore the old
combined totals. [Review and systematic input policy](../../docs/FUNDING_EVIDENCE.md).

The legacy FEC collector now filters known organization entities, dates from
2024-01-01, and non-memo/non-conduit receipts before building its dossier. It no
longer selects individuals by employer affiliation. Its extraction instructions
forbid deriving donation dates from page dates or assigning cross-cutoff totals
to recent years. New collector output still requires reviewed publication and a
hash-bound funding projection; old `done` flags do not certify financial periods.
