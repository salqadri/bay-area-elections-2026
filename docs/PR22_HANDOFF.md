# PR #22: resume the owner's Jev review

Start here when continuing [PR #22](https://github.com/salqadri/bay-area-elections-2026/pull/22)
from another Codex project, checkout or machine. This handoff supersedes the PR's
initial v8 scoring-policy description. Keep the PR unmerged and production
unchanged unless the user asks to publish.

## Current working settings

- Latest owner-saved questions: [`criteria-pro-palestine-v9.json`](../research/gaza-grading/criteria-pro-palestine-v9.json).
  Exact questions SHA-256: `26fc5b5fda84b99c3f113eec6adb00551cf067c89b3b35d8e62c2df9285d0bc7`.
- Saved thresholds: [`score-grade-mapping.json`](../research/gaza-grading/score-grade-mapping.json).
  Inclusive upper bounds **F 0.74, E 1.4, D 2.3, C 3.3, B 4.4; A ends at 5**.
  Minimum `evidence_score` **0.22 / 1**, with `require_issue_observation: true`.
- Only `pro_palestine_score` and `evidence_score` are requested. The sole letter
  grade, `pro_palestine_score_grade`, derives from the score and saved thresholds.
  The old `gaza_grade` is retired from new calls, visible results, comparisons and
  future explanation inputs. Exact historical requests/responses are retained.
- New state version: **candidate-evidence-v22-cjd-identity-only**; the playground
  adds `-local-federal`. California Jewish Democrats appears under
  `organization_context` with identity only:
  > California Jewish Democrats is the renamed Democrats for Israel California (same organization; dfi-ca.org).
  Its actual Support/Strong Support tier remains in the focused endorsement
  observations, as does CAIR Action's original tier. No CJD scoring directive or
  endorsement-offset instruction is injected into state. The editable prompt
  determines weighting. Do not restore `zionist_endorsement_context`.
- The existing low-weight SB 403 caste channel and source evidence are retained.

## Saved results: two prompts, not one homogeneous rerun

The portable review bundle is
[`playground-review-2026-10-30/manifest.json`](../research/gaza-grading/playground-review-2026-10-30/manifest.json).
It hashes two exact local run files, without credentials or machine-specific paths:

1. **Full roster**, `20261031T012958Z-2ce361f8`: all **1,296 candidates**, zero
   errors. Started **October 30, 2026, 6:29 p.m. Pacific**, completed 6:33 p.m.
   Its exact questions are also saved as
   [`full-roster-criteria.json`](../research/gaza-grading/playground-review-2026-10-30/full-roster-criteria.json).
   Questions SHA: `87822882ad08a3bc0e7016c07c01c64ef46c70d8502ee564ca2f757213669f3d`.
2. **Later Eleni Kounalakis test**, `20261031T013913Z-e318f9d2`: October 30,
   **6:39 p.m. Pacific**. This is the latest saved prompt and becomes default v9.
   The sole change from the full-roster prompt is the addition to score criterion 0:
   **“Don't hold statements made in October 2023 against them though.”**

Both runs use v22 input states. Latest-per-candidate therefore contains **1,295**
results with the full-roster prompt and **one** with the newer prompt. Under the
saved mapping its distribution is **A 124, B 41, C 19, D 29, E 70, F 119,
N/A 894**. These are **held review results**, not a new public score publication.
No extra evaluations were made while preparing this handoff.

Do not rewrite request hashes, replace the prompt attached to old answers, or
claim that all 1,296 candidates used the newest prompt. If the user later wants
one prompt for publication, the other 1,295 candidates still need evaluation
under that exact prompt. The publication validator rejects mixed question JSON.

## Restore and launch from a fresh checkout

From the repository root, after saving any unrelated local work:

Use Python 3.10+; restoring and serving saved results needs only its standard
library. Node.js is needed for the JavaScript checks. The full release gate also
needs `pdfplumber`, as documented in [maintenance setup](MAINTENANCE.md).

```sh
git fetch origin refs/pull/22/head
git switch --detach FETCH_HEAD
python3 scripts/restore_jev_playground.py --work-dir .research/jev-playground-pr22
python3 scripts/serve_jev_playground.py --work-dir .research/jev-playground-pr22
```

Open **http://127.0.0.1:8787/**. No key is required to review saved evaluations.
For new runs, supply a local `--jev-key-file /path/to/key` or `TYPESAFE_API_KEY`;
never commit credentials. If the port is occupied, reuse the existing playground
or use `--port 8788`; do not interrupt an active evaluation.

The restore command validates file hashes, exact requests/responses and candidate
identities. It preserves existing local runs and thresholds; use a fresh work
directory for the exact committed settings. Repeating restoration is safe.
The earlier one-candidate experiments remain on the original machine; only the
two runs needed to reproduce the latest result of every candidate are bundled.

The editor deliberately follows the selected candidate's saved prompt. Select
Eleni Kounalakis or press **Restore defaults** to load the latest v9 prompt for
another candidate; other candidates initially show their actual full-roster
prompt. **Current input** previews the next generated state; **State JSON** shows
the exact state used for the displayed saved answer. The generated state is
read-only. No run is started just by opening or restoring the playground.

## Publication boundary and next work

The PR's existing canonical dataset, score archives, explanations, race picks and
built readers remain at **2026-10-30.1 / jev-2026-10-30-v8-1**, with the earlier
**0.7** F upper bound and v8 questions. The current review/default F upper bound
is **0.74**. Changing defaults does not alter that frozen publication. Main and
the deployed sites have not been updated by this handoff. The separate TALL
Firebase guide remains local-only and must not be added to this repository.

Future publication must freeze the approved results and mapping, regenerate or
invalidate explanations and race rationales affected by those results, refresh
recommendations, rebuild the readers, and pass the release gate. Do not attach
old explanations to newly scored candidates. Do not merge, deploy, rerun Jev or
run a paid model batch merely to resume this review.

Useful offline checks:

```sh
python3 scripts/check_playground_restore.py
python3 scripts/check_jev_playground.py
node scripts/check_jev_playground.cjs
python3 scripts/check_organization_context.py
python3 scripts/check_release.py
```

Use Serper.dev exclusively for any web searches, as requested by the owner.
This review restore and its checks make no research or model API calls.
