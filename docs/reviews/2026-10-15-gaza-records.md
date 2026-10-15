# Congressional Gaza records and platform-workflow review — October 15, 2026

This proposed release uses schema **1.19** and publication **2026-10-15.1**. The source captures and identity review began October 14; their actual `checked_on` dates remain October 14. This report does not assert a GitHub Pages deployment.

## Captured and published scope

The [tracker adapter guide](../GAZA_VOTING_RECORDS.md) documents the source-selected history, provenance, palette, complete column dispositions and identity proofs. The committed capture contains all **523 member/tab records, 150 action columns and 25,830 values** across current and hidden historical House/Senate tabs. It preserves original values, dates, notes and links, without treating metadata/grades as votes. Current dropdown colors were checked against the complete rendered grid because the workbook and Sheets API omit chip colors. Historical formatting comes from the workbook. Green/red classifications are attributed tracker assessments and do not assume Yes means positive.

The candidate binding review attaches **18 member/tab records to 11 candidates**, exposing all **1,032 source entries**, including blanks and nonparticipation labels. Barbara Lee's prior House service is linked to the reviewed Oakland mayoral candidacy. Aisha Wahab's new House service is corroborated by the Clerk. The source does not cover Becerra's earlier House roster, state/local votes or every member/career. Historical actions repeat across tabs, so the displayed counts are source entries rather than unique votes. Each action retains its date; tracker tab names do not date every action.

The separate [official USCPR Action capture](../../research/gaza-records/uscpr-grades-2026-10-14.json) retains **261 profiles**, including publisher N/A values and missing identifiers, and binds **nine profiles** by reviewed name, state and member identity. **Spreadsheet Column A is never a grade source.** Current-Congress and publisher Lifetime grades/percentages are copied without recalculation. Their methodology combines votes and other actions; the Lifetime label is not complete-career coverage. The stale Swalwell profile cannot transfer to Wahab through a reused publisher ID. Wahab and Lee remain ungraded.

The immutable [publication review](../../research/reviews/gaza-congressional-records-2026-10-14.json) contains 27 exact additions and two shared-source changes. It pins the voting and grade snapshots by path and SHA-256. The common workflow now supports singleton grade/platform records, exact legislative records and shared source metadata, while retaining source/date/identity checks, idempotence and superseding review history. A finance collector's schema compatibility check now reads the schema's authoritative version so this migration does not block its future refresh; it does not refresh finance figures.

Both generated readers place the grade, complete tracked legislative record, future reviewed campaign-platform results and existing web/social/guide evidence within one collapsed Gaza evidence disclosure. Legislative record groups are collapsed separately; source-entry links identify the candidate's actual sheet cell. Assessment colors have explicit text labels. Exports retain the shared action definitions and grade provenance.

A structural comparison against base commit `22613fc` removes only the newly added fields, coverage metrics and schema/publication versions and establishes equality of every preexisting value: **all 416 positions, 875 printed candidacies, ballot decisions, finance dates/amounts, 12,953 endorsement records and 245 prose Gaza evidence items under 82 candidacies are preserved**.

## Deferred campaign-platform research

Only the reusable workflow and [Hermes/subagent instructions](../CAMPAIGN_PLATFORMS.md) are included. The offline inventory identifies **875 candidacies, 383 recorded website bindings and 381 unique source URLs**, leaving 492 without a verified URL in this inventory. This is not website discovery or evidence of a platform position. No broad website crawl, model call or platform research pass ran, and **zero platform results** are published.

Hermes should plan, crawl bounded source batches and assign only the current manifest's content-addressed source packets. Imports require inspected captures, identity proofs, exact quotes and state-specific scope checks. Every result remains held until separately reviewed through the common publication workflow. An incomplete/blocked site cannot establish silence, and missing inventory URLs cannot establish that no website exists.

## Verification

- `TZ=America/Los_Angeles python3 scripts/check_release.py`: all **24 checks pass** against the final dataset. This includes source captures, pinned candidate records/grades, schema, publication history, platform workflow, existing finance/research guards and both reader integrations. The focused schema validator now enforces the percentage maximum required by the new grade contract.
- Chromium browser checks pass for **both pages at 1440×1000 and 390×844**: collapsed groups, all 113 Khanna entries, visible distinct green/red colors and text, safe source links, no horizontal overflow or JavaScript errors, Wahab's missing grade/nonparticipation labels, Lee's historical record and Enter-key disclosure.
- Repeating the combined sync makes no changes; reapplying the registered review reports already applied without modifying the dataset. All candidate-name intersections with the tracker and official California grade feed are covered by the reviewed links.
- Changed-file credential-pattern scan, local Markdown-link checks and `git diff --check` pass. Raw captures and generated test artifacts remain ignored.

Offline checks establish internal source consistency and regressions, not the truth of every source claim, a complete career history or completion of the deferred platform pass.
