# Candidate community field

New Jev states may include the optional boolean `part_of_muslim_community`.
It means owner-confirmed membership in the **pro-Palestine Muslim community**.
The owner clarified on October 27 that true is affirmative evidence of general
alignment, beyond religious identification. New states carry the definition in
`community_alignment_context`; it does not prove every specific policy.
False/unknown is not an adverse stance. False values have no special
candidate-specific annotations.

`research/candidate-community/observations.json` binds each confirmed value to an
exact contest, ballot name and office, with its confirmation date. The initial
eleven owner-provided names include the ballot-name variants **Jamal Khan**
(owner: Jamaal Khan) and **Raeena S. Lari**. Later owner answers are applied to
this same registry. Research cannot overwrite a confirmed true or false.

The field is used by the shared grading state builder, including Senate races
outside the local playground's roster. Published election JSON and both public
readers are unchanged. New state versions distinguish these inputs from older
saved evaluations; original requests, answers, hashes and run files stay intact.
Rerun a candidate explicitly to submit an updated state.

## October 25 research coverage

The active repository roster has **1,296 candidacies**. The eleven initial owner
confirmations were not searched again. The remaining **1,285 candidacies** were
covered by **1,277 distinct candidate queries**; repeated names share retrieval
but retain separate candidacy/office decisions. Supplementary Serper searches
check accessible alternatives and public candidate guides.

The final registry contains **12 true and 12 false values**, all owner-confirmed.
The other **1,272 candidacies remain unknown**: 1,250 have no explicit discovery
lead, and 22 captured-source reviews do not establish a candidate-specific
identification. These are scoped research outcomes, not findings of
non-membership. Every source-review question was resolved by owner input before
this snapshot. See the [coverage summary](../research/candidate-community/summary-2026-10-25.json)
and [full candidacy ledger](../research/candidate-community/coverage-2026-10-25.csv).

## Repeatable source research

```sh
python3 scripts/research_candidate_community.py search --serper-key-file /secure/serper-key
python3 scripts/research_candidate_community.py triage --jev-key-file /secure/jev-key
python3 scripts/research_candidate_community.py review --jev-key-file /secure/jev-key
python3 scripts/research_candidate_community.py followup --serper-key-file /secure/serper-key
python3 scripts/research_candidate_community.py guides --serper-key-file /secure/serper-key
python3 scripts/research_candidate_community.py triage --jev-key-file /secure/jev-key
python3 scripts/research_candidate_community.py review --jev-key-file /secure/jev-key
python3 scripts/research_candidate_community.py report
```

The collector covers all non-excluded contests and printed, provisional and
qualified-write-in rosters. Every unconfirmed name receives the same query
pattern. It never guesses who is likely to be Muslim from names, appearance,
ethnicity, nationality, family, endorsements, policy, allies or event attendance.
All web discovery uses Serper; page captures follow the source URLs. Snippets
nominate pages only and never establish a state value.

Jev triages discovery excerpts, then separately reviews compact captured source
text against candidate/office identity. Public religious identification can
nominate an owner question; it cannot set this community field. Both unreadable
sources and ambiguous evidence are held. Owner-confirmed values are skipped on
subsequent research passes, including when a source says something different.
No confidence cutoff or automatic negative label is applied.

`--dataset`, `--work-dir`, `--workers` and a search `--limit` are available. The
default ignored work directory is `.research/candidate-community/2026-10-25`.
It retains discovery packets, actual captures, exact cached Jev
requests/responses and held results. Keys stay outside Git and never enter
research output or the browser. A changed dataset requires a new work directory.
Triage/source caches invalidate when new leads or their context change. Rerun
triage and review after collecting follow-ups. The report accounts for every
candidacy; it never applies a proposed flag or edits the published dataset.

## Integration and verification

The current shared state is `candidate-evidence-v15-chronology-community`; the
local wrapper is `candidate-evidence-v15-local-federal-chronology-community`.
New publications reject N/A when this explicit affirmative context was supplied.
Historical evaluations stay exact; see [context follow-ups](EVIDENCE_CONTEXT.md).

```sh
python3 scripts/check_candidate_community.py
python3 scripts/check_jev_playground.py
```

The complete release gate includes the community check. Offline tests cover
exact owner/office/name binding, spelling variants, unknown versus false,
provenance, all-roster scope, credential exclusion, resumability, source versus
snippet review, stale-result invalidation and preservation of confirmed values.
No live API calls occur during tests.
