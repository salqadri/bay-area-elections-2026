# Refresh CAIR Action's California guide

`refresh_cair_guide.py` refreshes every candidate card in the official California
2026 general-election guide. The [California page](https://cairaction.org/california/)
embeds the same PDF returned by its
[state-guide endpoint](https://cairaction.org/wp-json/cair/v1/state-guide/CA-2026).
Despite its `/wp-json/` URL, that endpoint currently returns `application/pdf`.
The adapter therefore checks the actual payload rather than assuming JSON.

The October 9 HTML migration remains a historical baseline and validator.
Do not rerun its destructive full-layer replacement as a refresh. The new adapter
uses the registered, candidate-specific before/after publication workflow.

## Repeatable commands

Use Python 3.10+ with `pdfplumber` installed (also used by the offline parser
regressions). Raw PDF/HTML and response caches stay under ignored `.research/`.
Choose a new date/path for a later capture; existing artifacts are never replaced.

```sh
python3 scripts/refresh_cair_guide.py fetch --output .research/cair-YYYY-MM-DD.pdf
python3 scripts/refresh_cair_guide.py capture .research/cair-YYYY-MM-DD.pdf --checked-on YYYY-MM-DD --output research/endorsements/cair-california-YYYY-MM-DD.json
python3 scripts/refresh_cair_guide.py review --capture research/endorsements/cair-california-YYYY-MM-DD.json --jev-key-file /secure/path/key --id cair-california-general-YYYY-MM-DD --output research/reviews/cair-california-general-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py preview research/reviews/cair-california-general-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py apply research/reviews/cair-california-general-YYYY-MM-DD.json
python3 scripts/build_site.py
python3 scripts/check_release.py
```

Review the generated dispositions and exact changes before applying. An all-hold
review needs no application. Update only the publication version/coverage
metadata for an applied source refresh; do not advance ballot, finance or other
research dates. Commit the normalized capture, review, actual Jev audit, registry,
canonical dataset and both rebuilt readers together. See the
[October 23 audit](reviews/2026-10-23-cair-action-refresh.md).

## Parsing and relationship rules

The PDF adapter binds names, offices and labels to each white candidate card's
geometry, so adjacent columns and wrapped names cannot be interleaved. It checks
the explicit general-election header and November 3, 2026 date. It accounts for
every candidate badge and rejects unsupported layouts, incomplete cards, unknown
levels, unbound badges and candidate/measure mixtures. Measure-only pages are
recorded separately and never yield candidate recommendations. Source-page and
bounding-box coordinates, raw label, source hash/size and every normalized card
are retained in the portable capture.

- `Endorsed` becomes `endorsed`.
- `Joint Endorsement` becomes `endorsed` with `shared: true`.
- `Preferred` remains `preferred`.
- `Oppose`/`Opposed` becomes `opposed` on the opposed candidate.
- A `No Endorsement` card, if present in a future supported capture, is retained
  without creating or deleting a recommendation.

Name similarity and previously reviewed spelling aliases only shortlist leads.
Jev alone decides whether the source names the same California candidacy and
current office/seat. The existing identity-review probability requirement is
0.90; this is separate from the playground's unfiltered political-grade outputs.
An ambiguous match or numbered-seat conflict stays held. No source card adds an
office or candidate to the roster. Current matching supports published candidates;
filed-but-unconfirmed local candidates stay outside publication, rather than
being silently promoted to the printed ballot.

Each card has a disposition, including outside-inventory names and rejected
leads. Duplicate cards deduplicate only after candidate/office/relationship
agreement; conflicting source levels and multiple current records stay held.
A newer explicit current tier replaces the exact earlier current/unspecified
CAIR observation once. Existing historical/primary records remain separate.
Other publishers and CAIR records absent from the new source are preserved.
An identical source/date rerun reuses cached Jev requests and produces no change.

## Tests

`check_cair_refresh.py` covers PDF header/layout failure, wrapped names, all
polarity states, source conflicts, rejected identities, California-only scope,
additive updates, precise replacements and rerun idempotence. Its published
checks verify every card disposition, actual Jev request hashes and target
bindings, Kevin Park's preference, Marc Cooper's opposition, updated tiers, and
the unresolved Tomara Hall district hold. It is part of the offline release gate.
The dated workflow fixture restores only the older CAIR layer when testing an
empty review history; current Gaza quarantines and other research stay intact.
