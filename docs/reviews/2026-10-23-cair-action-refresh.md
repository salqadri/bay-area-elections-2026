# CAIR Action California general-election refresh — October 23, 2026

The October 9 source capture had 200 cards and did not contain Kevin Park. The
current official guide has 242 candidate cards. Its California HTML page renders
that same 34-page PDF using PDF.js; the supplied `/wp-json/cair/v1/state-guide/CA-2026`
endpoint serves a PDF, not a JSON roster.

`refresh_cair_guide.py` adds a repeatable PDF capture → Jev identity review →
registered update pipeline. The existing dated HTML migration and its historical
200-card review remain unchanged. No web searches or models other than Jev were
used. The source was fetched directly, parsed by card geometry, and visually
inspected, including Kevin Park's card on page 15. All 242 recommendation badges
bind to individual cards; measure pages 28–34 are excluded from candidate import.

## Source and complete dispositions

Normalized capture: `research/endorsements/cair-california-2026-10-23.json`.
The PDF explicitly says **2026 California General**, **GENERAL ELECTION: 11/3/26**.
Its SHA-256 is `ff7e0f1f6c7f3fe4e07410a72f0c8af74d68b9405fd01bb5482b804b26203bd6`
(11,347,688 bytes). Observation date is October 23, not an announcement date.

| Source level | Cards |
| --- | ---: |
| Endorsed | 160 |
| Joint Endorsement | 5 |
| Preferred | 76 |
| Opposed | 1 |
| Total | 242 |

| Final card disposition | Count |
| --- | ---: |
| Added current recommendation | 14 |
| Refreshed exact older current/unspecified record | 93 |
| Held after Jev review | 20 |
| No plausible tracked California roster lead | 115 |

The 20 holds include eighteen rejected/ambiguous current-identity leads and two
existing recommendations (Gordon Chester and Johnny Ray Reyna) retained without
redating after the fresh source match did not clear the existing 0.90 identity
probability rule. Tomara Hall remains held: source District 1 conflicts with
tracked Trustee Area 2. None of these holds delete existing data. Unmatched cards
remain in the capture and do not prove that a person is absent from the ballot.
Five joint cards are retained in the capture; none maps to a tracked candidacy
in this refresh. Joint mapping is covered by regression tests.

## Changes and preservation

Publication review: `research/reviews/cair-california-general-2026-10-23.json`;
actual request/response audit is its sibling `.audit.json`. All applied matches
have Jev source-card/target bindings and exact candidate-office identities.
The 127 actual final request hashes and responses are archived; prior preliminary
identity-review attempts remain in the ignored request cache, not publication.

New records: Richard Pan, Randy Villegas, Fiona Ma, Eleni Kounalakis, Richard
Barrera, Kashef Qaadri, Kathy Kimberlin, Yvonne Inciarte, Eric Crutchlow, **Kevin
Park**, Paul Sethy, Sarah Syed, William Yragui and Olivia Sanwong.
Kevin Park is **Preferred by CAIR Action**, not Endorsed. Two current tiers change:
Scott Sakakihara and Mer Curry Nuñez are now **Preferred**, replacing Endorsed.
The exact general-election phase and source page replace earlier unspecified
provenance where the same current candidacy is confirmed. Marc Cooper remains
**Opposed**, with no positive endorsement inferred for another candidate.

The final dataset has **109 CAIR records: 81 endorsed, 27 preferred, 1 opposed**.
Total printed endorsement/recommendation coverage is **24,501 records on 548 of
1,294 candidacies**. Publication version is `2026-10-23.2`; schema stays 1.23.
A structural reversal of precisely the reviewed CAIR changes, coverage metric
and publication version recovers the original main dataset exactly. Other
publishers, parties, rosters, finance, Gaza evidence, dates and source registries
are unchanged. Both readers are rebuilt from that reviewed dataset.

An actual repeat against the updated data uses identical cached Jev requests,
retains 107 records unchanged and produces no dataset changes. Source absence is
never a removal operation; no blanket replacement is used.

## Validation and related playground fix

Ten new offline regressions cover parsing, matching, relation/phase preservation,
exact replacements, idempotence, source conflicts and applied audit bindings.
The **35/35 offline release checks pass**, including `check_cair_refresh.py`. Chrome checks verify Kevin's
Preferred label in the rebuilt reader at desktop/mobile widths. The release
command on this Mac uses `TMPDIR=/private/tmp` to avoid the pre-existing temporary
path symlink mismatch. Offline consistency is not official ballot certification.

The separately reviewed Jev playground in PR #14 also omitted CAIR Action from
its compact focus registry. Registry v3 explicitly includes this owner-requested
publisher and preserves preferred/opposed/shared flags; historical registry v2
and archived grading requests remain unchanged. The playground's canonical data
changes are not duplicated in that PR. Locally it can preview this research
checkout's dataset using `--dataset` before the research PR is merged.
