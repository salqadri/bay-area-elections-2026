# October 26 publication: Jev review tools and Fiona Ma evidence

The owner authorized publishing [PR #17](https://github.com/salqadri/bay-area-elections-2026/pull/17).
The release uses publication version **2026-10-25.2**, schema **1.23**. The
version identifies the underlying October 25 content; publication does not
advance its observation dates. Main/root is the GitHub Pages publication source.

The public change adds GE-1288, Fiona Ma's historical May 16, 2024 opposition to
divestment from Israel. Its exact source, date, identity and meaning passed Jev
review. Coverage is 1,050 dated evidence items across 333 printed candidacies.
The immutable review/audit, evidence ledger, coverage and both generated readers
are synchronized. See the [research diagnosis](2026-10-25-evidence-sufficiency-and-fiona-ma.md).

The local playground includes latest-per-candidate evaluation history, saved
prompt restoration, five-county batch/filter controls, CAIR comparisons, tunable
derived grades, focused Vote for Peace observations and owner-confirmed community
inputs. A saved compatible `evidence_score` below 0.10 / 1 suppresses the derived
letter as **Insufficient Info**; original Jev answers and confidences stay exact.
The Jev API and credentials remain local; political grades and private local
run history are not published in public candidate records. No candidate grading
or finance/roster refresh was required for this publication.

## Verification

The complete offline release gate passes **40/40**, with a matching dataset hash.
Chromium verifies the new evidence suppression, exact saved prompts, current
versus historical Fiona inputs, CAIR metrics and mobile layout. Python and
JavaScript agree on all 1,042 latest saved evaluations; 807 suppressed at
inspection. All 102 preexisting saved run files remain byte-for-byte unchanged.

Content manifest (documentation-only follow-ups leave these bytes unchanged):

| Artifact | SHA-256 |
|---|---|
| `2026-11-03_Bay_Area_Elections.json` | `2561367c7b25134daede074fd4264af3e533284907a8be7f01a359a55ab7162a` |
| `index.html` | `2e012dbe65d48cfd2bd99bc560eae5c148416f5ff9006d151b8a79111f76451b` |
| `ballot.html` | `531417d2a06e356fe0123cd1de1d7a60605bf040093000799224d7c3a4219d98` |

Publication verification must confirm a successful Pages deployment for the
merged main commit and exact live bytes for both readers and the canonical JSON.
Offline checks alone do not establish deployment or live provider availability.
