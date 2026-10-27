# Targeted Jev rerun review — October 27, 2026

Compared PR #19 with main `5d35c5c` (publication 2026-10-27.5). Prepared evidence publication is 2026-10-27.6. Hermes’s latest `qwen/qwen3.8-27b` summaries and the current numerical evaluations are preserved.

## What is updated

The shared state builder and local playground generate v15 inputs for all 1,296 active candidacies across 471 races. These are generated on demand; saved request states and provider responses remain immutable. Opening **Current input** shows the new state. A displayed saved result still belongs to its old **State JSON** until that candidate is rerun.

PR #19 changes exact inputs for 22 candidacies: 21 gain substantive evidence/context and Barbara Lee receives only a generic legislative-context clarification. The other 1,274 input states match the current main builder. The removal of the twelve-item cap does not newly expose older observations for additional candidates in this snapshot.

No questions, grade bounds or evidence threshold changed. A full-roster rerun is unnecessary solely for this PR. No candidate scoring or summary regeneration was performed for this audit. A separate Jev choice-only call assessed rerun priority; it did not grade candidates.

## Recommended small batch

Four cases have priority numerical-input corrections. Include Ro Khanna as a fifth case to address the owner’s identified omission, even though his existing A already reflects a favorable overall assessment. Do not assume any specific new grade before running Jev.

| Candidate | Race | Current grade | Evidence score | Why rerun |
|---|---|---|---|---|
| Scott Wiener | CD-11 United States Representative — United States House of Representatives | C (2.70/5) | 0.97 | Debate refusal, backlash and later statement qualify the apparent change in stance. |
| Sam Liccardo | CD-16 United States Representative — United States House of Representatives | D (2.44/5) | 0.95 | Dated official cosponsorship supersedes obsolete no-support guide prose. |
| Ro Khanna | CD-17 United States Representative — United States House of Representatives | A (4.74/5) | 0.98 | Initial Yes, attributed explanation, later No and UNRWA-restoration support need evaluation together; already A, so numeric refresh is less urgent. |
| Kiran Mohammad | At large Mayor — City of Dublin | N/A | 0.17 | Confirmed community alignment exists, but evidence 0.17 currently produces N/A. |
| Jamal Khan | At-large Governing Board Member — Berryessa Union School District | N/A | 0.16 | Confirmed community alignment exists, but evidence 0.16 currently produces N/A. |

These are candidate-level reruns. Opponents in those races do not need new evaluations merely because one candidate’s input changed. Keep the current owner-saved v5 questions and saved bounds **0.7 / 1.4 / 2.5 / 3.2 / 4.4**, minimum evidence **0.20**, and no confidence cutoff. Never manually turn the two N/A results into A; obtain fresh evidence-score responses.

## Optional or explanation-only updates

**Aisha Wahab:** official dated cosponsorship corroborates the Sponsor response already present in her evaluated record. She is already A (4.85/5) with 0.99 evidence. A fresh score is optional; future summaries should use the dated primary source.

The other already-A community cases gain explicit semantics for a true boolean that was already supplied to scoring: Lateefah Simon, Abdul El-Sayed, Shafina Barnett, Kashef Qaadri, Aziz Akbari, Qasim Lodhi, Seema Badar, Raeena S. Lari, Kamal Yassin. They do not have the low-evidence N/A problem, so numerical refresh is optional.

These candidates gain only legislative grouping/explanatory context, with the actual actions already supplied: John Garamendi, Josh Harder, Mark DeSaulnier, Kevin Mullin, Zoe Lofgren, Jimmy Panetta, Barbara Lee. Refresh prose where it omits material sequence details; numerical rescoring is not required by these context-only changes.

Hermes’s latest published summaries already mention Liccardo and Wahab’s sponsorship. Khanna’s latest summary still omits the new explanation/follow-up context, and Wiener’s still describes a sharp reversal without the debate/backlash sequence. After a targeted scoring refresh, regenerate explanations only for the newly evaluated candidates, using Hermes’s current owner-approved prompt and Qwen runtime. Preserve all unrelated final-prompt summaries. Newly sourced drafts must not pretend the new material was in an old frozen scoring request.

## Scope and audit trail

This is a recommendation about PR #19. Before this PR, **336** current main input states already differed from the published scoring archive because of earlier organization-context and spending-projection changes. With this PR, the exact-difference count is **339**. Exact JSON drift is not evidence of a wrong grade, and these counts are not a recommendation to rerun 339 candidates. This targeted review does not resolve or certify all earlier input drift.

The [machine-readable manifest](../research/gaza-grading/rerun-impact-2026-10-27.json) records every changed candidate ID, race, before/current state hashes, saved request hash, existing grade/evidence, Jev triage probabilities and recommended-small-batch flags. It is bound to the baseline commit and published score archive hash. The five flags allow Hermes to select just these candidacies without changing opponents or unrelated results.
