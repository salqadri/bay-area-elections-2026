# Local Jev playground

The playground runs on this computer, separate from the GitHub Pages readers.
It includes every candidate in **all active U.S. House contests tracked in this
repository**, including the Bay Area races. Current scope: **187 candidates / 72
races**. It does not discover additional nationwide contests or alter the roster. Separate printed, provisional and qualified-write-in rosters remain distinct.

## Start

From the repository root, with Python 3.10+:

```sh
python3 scripts/serve_jev_playground.py --jev-key-file /secure/path/jev-key
```

Open **http://127.0.0.1:8787/**. `TYPESAFE_API_KEY` can replace `--jev-key-file`.
The key stays on the local server; it is never sent to the browser, included in
an export, or written into this repository. Without a key, stored results still
load and remain inspectable. `--port`, `--dataset` and `--work-dir` are available;
the server always binds loopback, never the network interface.

GitHub Pages does not serve the local API. Jev rejected a preflight from the
Pages origin, and the owner chose a local test page instead of deploying a relay.
There is no new public site area or main-reader UI change in this PR.

## Use

1. The page loads the stored **all-House focused run**, using the owner's exact
   October 23 question JSON (`pro-palestine-v2`). Nothing runs or incurs API calls
   merely by opening the page.
2. Use the candidate picker or previous/next arrows above the workspace. On
   desktop, the Monaco question editor and selected candidate's answers sit
   side by side, with Run controls always above them. On mobile, **Questions**
   and **Results** tabs share the same controls; running switches to Results.
   The textarea fallback works when the pinned Monaco CDN is unavailable.
3. Edit the questions, then press **Run selected candidate** or **Ctrl/Cmd +
   Enter** to evaluate exactly that candidate. Each iteration is saved separately.
   Select another candidate without losing the draft. When ready, **Run all
   187 candidates** evaluates the full roster with that same question text.
   Both actions take fresh snapshots of current data. Up to three Jev calls run
   concurrently; `choice`, `score` and yes/no `noul` questions can be renamed/added.
4. The selected response shows each question key/instructions, answer, type and
   confidence. Choice rows preview the leading returned probabilities; expand
   a row (or **Expand all**) for all options/score levels and their criteria and
   probabilities. **Find in questions** takes you to the editable question.
   Probabilities and confidence are separate. For `noul`, the answer is the
   probability of true, with no invented confidence. There are **no acceptance
   cutoffs or hidden low-confidence answers**.
5. **Inspect generated state & raw JSON** opens the read-only State JSON,
   Answers JSON and Full request with SHA-256. It is collapsed by default.
   Editing a prompt never changes the instructions or state attached to an
   existing result; a visible notice identifies answers from a saved prompt.
   Unevaluated candidates show an input preview with no inherited answers.
6. **Browse all House races** opens the state/district groups and search/state
   filters. Selecting a card brings that candidate into the workspace. Races
   remain sorted by state name and numeric district number.
7. Run history and JSON downloads preserve exact questions, model alias and
   returned model, frozen states, request hashes, answers, confidence/probability
   distributions, errors, cancellation status and dataset snapshot hash.

Runs are stored under ignored `.research/jev-playground/runs/`. Requests for each
run are also saved in its local cache. Each Run makes fresh calls, even when the
prompt is unchanged; the browser does not reuse old answers as new results.
Individual failures stay visible and do not remove other answers. Stop prevents
queued calls; in-flight calls may finish, including normal provider retries.
After a restart, an unfinished job is labelled interrupted rather than silently
resumed. A new run can be started; existing runs remain available for review.
The default view is the committed stored run, unless a local run is currently
active (in which case reload reconnects to it).

## Compact candidate input

The same `grade_gaza.build_state` supplies CLI runs, local runs and previews:

- Identity/party, the top 12 supporting and opposing IE spenders (separate lists,
  rounded dollars), recorded USCPR grades, up to eight platform summaries, a
  reviewed Gaza-platform statement when present, and up to twelve dated Gaza
  evidence summaries.
- Focused endorsement/recommendation observations only. The versioned exact-name
  registry is `research/gaza-grading/endorsement-focus-v2.json`: owner-named
  Track AIPAC, Vote for Peace and HAPAC, plus AIPAC, DMFI, J Street/JStreetPAC,
  RJC and JDCA context selected by Jev from the organizations' own material.
  Selection evidence/actual Jev answers are in the sibling `.review.json`.
  Related parent/PAC names are included for context without merging entities or
  assigning them the same position. Actual source names and relation types,
  ratings, phases, verification and historical flags remain intact.
- The focused pass includes **41 observations on 23 candidates**, at most three
  per candidate, instead of all 3,690 House endorsement observations. Other names
  are omitted for context budget, not declared unimportant or absent. No category
  is inferred from religion or ethnicity. Neutral image observations are not
  converted into named endorsements.
- Recorded congressional actions resolve `action_id` against the shared action
  registry and include the actual response, title/kind, date and Congress. The
  old builder read nonexistent title/date fields from response rows, resulting
  in blank action summaries; that is corrected before grading Bay Area members.
  Source-selected actions remain distinct from a complete voting history.

Inspect the JSON to see the exact available evidence. Missing fields do not
establish a neutral position. These are experimental model answers, not verified
candidate findings or grades published into the election dataset.

## Stored runs and CLI

The immutable default is
`research/gaza-grading/house-all-focused-2026-10-23/results.json`:
**187/187 answers, zero call errors**, `jev-latest` resolving to `jev-1.14.0`.
All answers are shown, including low confidence. Questions are in
`research/gaza-grading/criteria-pro-palestine-v2.json`; the prior v1 archive is
unchanged. Its historical cutoff flags are not imported into this playground.

To create a new CLI batch, use a fresh batch name:

```sh
python3 scripts/grade_gaza.py plan --scope house-all --batch house-all-YYYY-MM-DD
python3 scripts/grade_gaza.py grade --scope house-all --batch house-all-YYYY-MM-DD --jev-key-file /secure/path/jev-key --force
python3 scripts/grade_gaza.py report --batch house-all-YYYY-MM-DD
```

The CLI retains all valid answers/confidences too. `--force` bypasses exact-request
cache reuse; without it the CLI may reuse identical validated requests. The local
Run button always uses fresh calls. Do not overwrite committed historical batch
files. No command in this workflow writes to the canonical dataset, builds the
readers or publishes political grades.

## Verification

`check_jev_playground.py` covers question/answer contracts, focused input context,
congressional metadata, frozen snapshots, low-confidence retention, cancellation,
failure isolation, single-candidate isolation and repeated prompt iterations,
stale-selection rejection, persisted history, same-origin/Host checks and credential
redaction. `check_jev_playground.cjs` covers numeric ordering, custom questions,
confidence display and immutable state during delta updates. Both are in the
36-check offline release gate. Browser coverage includes real Monaco loading at
desktop/mobile sizes and, using a fixture transport, full Run/Stop/history/export
flows with custom questions, low confidence and a failed candidate. The iteration
workspace is checked at 1440×900, 1024×768 and 390×844 for adjacent editing/results,
mobile tabs, selected-candidate keyboard runs, expandable distributions, input
inspection, old-prompt labeling, history and exports. The actual
187-candidate default batch was run against Jev, not the fixture transport.
