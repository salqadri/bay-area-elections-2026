# October 26 publication: Jev review tools and Fiona Ma evidence

The owner authorized publishing [PR #17](https://github.com/salqadri/bay-area-elections-2026/pull/17),
merged into main as `b472045ad6c7ac88ef2e9d037768776aa8d17719` after checking
the exact PR head.
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

The [Pages deployment for the content merge](https://github.com/salqadri/bay-area-elections-2026/actions/runs/40283362389)
completed successfully. Actual downloads of both live readers and the canonical
JSON match every artifact hash above exactly. Chromium checked both public
readers at widths 1440 and 390: Fiona Ma's divestment evidence and source link
appear, with no page errors or horizontal overflow. The address reader was
checked through county browsing; no live geocoder claim is made. Test analytics
collection requests were blocked in the verification browser.

The local Jev server now runs from the merged main checkout and uses its canonical
dataset and existing history directory. All 104 run files present at restart were
verified unchanged. No grading call was submitted. The documentation follow-up
leaves the content manifest and publication version unchanged; its own Pages
deployment is also checked before reporting publication complete.
