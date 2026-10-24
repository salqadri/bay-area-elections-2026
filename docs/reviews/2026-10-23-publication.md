# October 23 combined publication — 2026-10-23.3

The owner explicitly authorized merging the pending PRs, updating documentation,
pushing and publishing. All three PRs are merged into `main`:

| PR | Change | Merge commit |
| --- | --- | --- |
| [#14](https://github.com/salqadri/bay-area-elections-2026/pull/14) | Local Jev playground | `3b9603e260404a0cb59cd32d0210cc92d1e3b5ee` |
| [#15](https://github.com/salqadri/bay-area-elections-2026/pull/15) | Current CAIR Action guide | `c61e2d2bf25acefb73a8eee8d50bbe94b6f38238` |
| [#16](https://github.com/salqadri/bay-area-elections-2026/pull/16) | Local Gaza action evidence | `2a9a9be311dd468389bd479084af8c3a4fb84433` |

PR #16 was retargeted from the CAIR branch to `main` after #15 merged. Each merge
was conditional on the exact reviewed head SHA. There were no outstanding formal
reviews or review requests. The three changes were first merged in an isolated
local checkout; its complete committed tree exactly matched the actual three
GitHub merges. Subsequent documentation changes leave the canonical dataset,
generated readers, schema, research audits and runtime code unchanged.

## Verification

The combined tree passed **38/38 offline release checks**, including the 24
playground regressions, ten CAIR refresh regressions, fourteen local-ceasefire
regressions, publication history, ledger reconciliation, schema, finance and both
reader integration suites. The release report's dataset SHA-256 matches the
published canonical file. Both generated pages pass exact rebuild checks.

The [GitHub Pages deployment for the final content merge](https://github.com/salqadri/bay-area-elections-2026/actions/runs/40045919462)
completed successfully for `2a9a9be311dd468389bd479084af8c3a4fb84433`.
Actual downloads from the live Pages site match the reviewed local bytes:

| File | SHA-256 |
| --- | --- |
| `2026-11-03_Bay_Area_Elections.json` | `258b2f36eb13df670bc441a3a08afc4c85fbe436cc3fbf9efb68b650dfd95f95` |
| `index.html` | `93b946ebea0137e9633cbf77d73bc957a4f06540ac1c3230c12f589eba84aa4a` |
| `ballot.html` | `8cd018bfc832af69ce0659af126b5b45b8a71ecb40a6d17e0d6833add08a8606` |

Actual Chrome checks against **both live readers**, at widths 1440 and 390,
verified Kevin Park's CAIR Action **Preferred** display, both Gaza source links,
the qualified United Against Hate wording, and the opinion's championing/blocked
outcome. All four combinations had no page errors or horizontal overflow. County
browsing was used on the address reader; no live geocoder availability is claimed.

The public version is **2026-10-23.3**, schema **1.23**. CAIR Action retains 109
records (81 endorsed, 27 preferred, one opposed). The Gaza update adds 36 records
across 35 candidates, yielding 1,049 records on 332 printed candidacies. Identity,
date and source-layout holds remain documented; publication does not resolve
them or refresh ballot/finance research dates.

## Local playground

The primary checkout is synchronized to `main`. The local Jev server uses that
checkout's default canonical dataset, with 685 candidacies across 268 races and
publication 2026-10-23.3. All 65 existing saved runs were verified unchanged after
the server reload. Historical baseline requests/results remain exact; opening
the playground does not rerun or publish political grades.

GitHub Pages serves the public readers. The Jev API remains on loopback at
http://127.0.0.1:8787/ with its key outside the repository; it is not deployed as
a public API. The documentation follow-up records these verified content hashes
without another dataset/publication-version change. Its own final Pages run must
also finish successfully before reporting the publication task complete.
