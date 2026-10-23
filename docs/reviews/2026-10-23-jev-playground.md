# Local Jev playground — implementation review, October 23, 2026

Prepared against main `6f4db0f` (post-PR-13 research update). The owner chose a
local test workspace instead of a public GitHub Pages area after the API rejected
the Pages origin. The canonical election dataset, both generated readers, and
historical 165-candidate grading archive remain byte-for-byte unchanged.

## Behavior

`python3 scripts/serve_jev_playground.py --jev-key-file /secure/path/key` serves
http://127.0.0.1:8787. Opening the page loads stored results without model calls.
Monaco 0.52.2 supplies JSON syntax highlighting/formatting; a usable textarea and
JSON preformatted inspector remain when the pinned CDN fails.

The owner-provided October 23 questions are the exact defaults. Run freezes edited
questions and **current** candidate states for every tracked active House race:
**187 candidates / 72 races**, including Bay Area contests omitted from the old
nationwide-prefix scope. Printed, provisional and qualified-write-in rosters stay
distinct; excluded contests/other offices stay outside this scope. There are no
tracked House write-ins in this snapshot.

Each candidate shows all returned answers and confidence, with no acceptance
cutoff or confidence-based omissions. Custom/renamed choice, score and yes/no
`noul` questions work. The latter returns probability of true instead of a
separate confidence; no artificial confidence is manufactured. State groups use
the shared state labels and numeric district ordering.

Selecting a candidate reveals the exact State JSON, Answers JSON or Full request
with request SHA-256. Editing the draft questions does not mutate displayed old
requests. Run history/downloads preserve frozen questions, states, answers,
confidence/probabilities, returned model, errors and dataset hash. A local run
makes fresh API calls rather than relabelling cached results as a new evaluation.
One failed candidate stays explicit while other results survive. Stop prevents
queued calls; in-flight calls may finish. Restarts label unfinished runs interrupted.
A user can inspect old results while another run continues, without mixing answers
or accidentally starting a second job.

## Compact, source-backed endorsement input

Full House endorsement context would add **3,690 observations**. The focused
registry (`endorsement-focus-v2.json`) instead supplies **41 observations on 23
candidates, at most three each**. It includes the owner's explicit Track AIPAC,
Vote for Peace and HAPAC request plus five relevant entities/brands selected by
Jev from primary-source material: AIPAC, DMFI, J Street/JStreetPAC, RJC and JDCA.
The sibling review file contains the actual selection questions/responses and
source packets. Five discovery queries used Serper exclusively. Primary sources
were retrieved directly; four blocked direct HTTP retrievals were read using
ordinary source-page retrieval, not search-result snippets as proof.

This is an inclusion focus, not an organization political-category assignment or
a candidate grade. Different organizations are not equated. Parent and PAC source
names remain separate in their observations; alias groups only control inclusion.
No relevance is inferred from religion or ethnicity. Names, relation, phase,
history, rating and verification are retained; preferences/support ratings are
not silently converted to endorsements. Neutral image observations do not become
named endorsements. The registry can be extended deliberately without embedding
an organization keyword guesser in each run.

The common state builder also repairs congressional action serialization: the
stored response rows have `action_id`/`value`, while title/kind/date live in the
shared action registry. Previously the builder read nonexistent title/date
fields and omitted the actual response. New states resolve those IDs and include
actual response and Congress, retaining source-selected action scope. Official
USCPR scores remain a separate input where present.

## Actual default run

Immutable archive:
`research/gaza-grading/house-all-focused-2026-10-23/results.json`.

- Criteria: `pro-palestine-v2` (exact owner JSON).
- State: `house-evidence-v3-focused`, focus registry v2.
- **187/187 answered, zero call errors**, every response `jev-1.14.0`.
- A 22 · B 4 · C 2 · D 47 · E 2 · F 110. No result is accepted/rejected by grade
  probability or confidence; these counts describe all model outputs.
- Run timestamp `2026-10-23T18:21:30+00:00`.
- Dataset canonical-content SHA-256:
  `663f4c3e5ae0bc9e37dbbf08db5ec324a9394893692c7908cbf25f052f5ac0ca`.
- Archive file SHA-256:
  `15bf0267ff8e1183f39029be837232ea953d0fe65dfb81c5a2b65b2e4a098d05`.

All 187 requests, returned answer pairs, question JSON and current-state bindings
were independently checked. The original `house-2026-10-22` archive is unchanged;
its historical cutoff flags are not used by this UI or new grading path.

## Local API and credentials

The Python server is loopback-only, with a narrow static-file allowlist, no
credential endpoint, no provider-header/body logging and no arbitrary upstream
URL. Host checks reject non-loopback hostnames; JSON writes require the exact
same Origin, preventing ordinary cross-origin job starts. API keys remain on the
server and never enter browser JSON, exports or committed files. API failures
are redacted. Run history/request caches are ignored under `.research/`.

Provider calls use the real System One API with bounded concurrency (three),
transient-error retries, question/answer shape validation, and no political
acceptance threshold. Shape errors are reported as call errors, never fabricated
answers. Source and model text is rendered as text/JSON, not executable markup.

## Validation

- **36/36 offline release checks pass**. New suites cover 16 Python regressions
  plus Node assertions for generic question rendering, zero/low-confidence
  retention, state/district sorting and immutable delta merges.
- Real Chrome at **1440px and 390px** loads actual Monaco, all 187 stored answers,
  all 72 races, CA CD-1 before CD-17, exact Ro Khanna state/action responses,
  and invalid-JSON Run disabling. No page errors or document overflow.
- A fixture-only local server exercised actual browser/server Run plumbing with
  custom questions across all 187 candidates, confidence 0/0.12, one failed
  candidate, frozen requests, JSON download, cancellation, history/reload and
  comparing a prior run while an active job completes. The fixture never becomes
  the committed default or uses the owner's API key.
- Actual default grading used Jev, not fixtures. API credentials were scanned
  against every changed/new tracked file; no matches. Existing dataset/readers
  and prior archive equal their baseline Git blobs; generated build remains exact.

No public deployment, political-grade publication, roster/finance/endorsement
mutation or publication-version bump is part of this change. This is a local
playground and reproducible experimental batch for owner/Hermes review.
