# Current-cycle Ballotpedia endorsement collection

`ballotpedia_endorsements.py` supplements campaign-page evidence with the
**Endorsements section for the election's year** on each recorded candidate
profile. It never discovers a replacement profile by name. It uses Python's
standard library and the existing `ballotpedia_url` inventory, across printed
and provisional candidacies. Missing profiles, blocked pages, unsupported
layouts, ambiguous identities and low-confidence classifications remain explicit
queues. Neither a missing section nor a failed request proves no endorsements.

## Collect and review

From the repository root, using Python 3.10+:

```sh
python3 scripts/ballotpedia_endorsements.py plan
python3 scripts/ballotpedia_endorsements.py fetch --limit 30
python3 scripts/ballotpedia_endorsements.py extract
python3 scripts/ballotpedia_endorsements.py review --jev-key-file /secure/path/jev-key
python3 scripts/ballotpedia_endorsements.py draft --id ballotpedia-endorsements-YYYY-MM-DD --reviewed-on YYYY-MM-DD --output research/reviews/ballotpedia-endorsements-YYYY-MM-DD.json --jev-key-file /secure/path/jev-key
```

Replace dates with the actual Pacific review day and use a new review path.
`TYPESAFE_API_KEY` can replace the key-file option. Never put the key in source,
HTML, exports or Git. Fetch/extract need no credential. Collection makes direct
requests to recorded Ballotpedia URLs, so **no search provider is called**. If
profile discovery is ever added, only the owner's Serper service is authorized;
search snippets must remain discovery leads rather than endorsement evidence.

Global `--dataset` and `--work-dir` options precede the subcommand. Fetch/review
and extract accept repeated `--candidate 'Mike Rogers'` filters for bounded
checks. Fetch defaults to two workers with at least one second between request
starts, reuses seven-day captures, and supports `--force`, `--retry-failed`,
`--refresh-days` and `--limit`. It stops after five failures by default; the
explicit `--stop-after-failures` budget can be adjusted for a reviewed batch.
`fetch-status.json` reports attempted/deferred profiles. Raw captures are
immutable and content-addressed; failed refreshes cannot erase their bytes or
remove published evidence. Only one coordinator should use a work directory.
The ignored default is `.research/ballotpedia-endorsements/`.

HTTP 200 is insufficient: empty pages and challenge HTML without an article
stay unavailable. The collector neither executes challenge scripts nor changes
identity to evade them. Where a browser or earlier direct retrieval succeeded,
import its actual saved HTML, including its canonical link:

```sh
python3 scripts/ballotpedia_endorsements.py import-capture --url 'https://ballotpedia.org/Mike_Rogers_(Michigan)' --html /path/to/actual-saved-page.html --observed-at '2026-10-22T17:40:59+00:00'
```

Use the **actual** retrieval timestamp with a timezone, not the import time.
Wrong canonical URLs, unrecorded profiles, future dates and challenge pages
fail. Import is source collection, not identity or relationship approval.

## Source and decision rules

The parser retains explicit year boundaries and the heading hierarchy. It
excludes older and unscoped notable-endorsement sections, and preserves nested
category/phase headings. Ballotpedia polling charts sometimes insert an `h3`
"Change over time" inside a year; that presentation heading must not erase the
explicit year. Citation links and current elected titles remain in the source
packet, while the named anchor supplies the endorser's spelling. Nested category
wrappers are not additional endorsers. Unsupported prose/tables or rows with
ambiguous named links are retained as source-layout holds, not silently omitted.

Jev `jev-1.13.0` is the sole judgment model. Source text is untrusted evidence,
never instructions. Separate typed questions assess:

- Same person, office, electorate and year (match probability at least 0.85).
- Each exact source entry's relationship (endorsed/recommended probability at
  least 0.80), preserving voter-guide recommendations and holding distinctions,
  reverse endorsements, opponents, mentions and ambiguous entries.
- A phase explicitly attributed to the entry's own section/category (primary or
  general probability at least 0.90). A general-ballot introduction and a nearby
  primary-results table do not phase the endorsements; otherwise use unspecified.
- Entity kind, with unspecified when the source/model does not establish it.
- Potential source-name variants against existing observations (at least 0.90),
  keeping PACs and parents, different people and conflicting relationships apart.

No amount of model confidence upgrades an explicit program distinction or an
opposition/withdrawal category into an endorsement. Exact names/quotes must come
from the captured row. Draft reconstructs each Jev request from its exact source
packet and checks the actual selected probability. Missing entries, altered
answers, stale candidates, refreshed captures and changed packet text fail.
Cached requests are keyed by the complete prompt/model contract; reruns reuse
identical decisions. Draft may call Jev for duplicate identity questions.

## Duplicates and publication

`endorsement_identity.py` is shared with the campaign collector. Equivalent
same-name/relationship observations are deduplicated **across source URLs**.
An unspecified phase can match an otherwise equivalent record, while explicit
primary versus general and historical versus current observations stay distinct.
Source aliases are never merged by fuzzy similarity alone: similarity only
creates a Jev review question. Every proposed new entity is also screened by Jev
against all compatible existing names and curated publisher names, so acronyms
and legal-name variants with no shared tokens are not silently treated as new. Ambiguous overlaps and same-entity conflicting
relationships/ratings stay held. Curated CAIR/peace-guide/support ratings retain
their existing official-source controls. Accepted Ballotpedia corroboration is
retained in the audit without adding a second displayed row or deleting the
original observation. This does not retroactively merge unrelated legacy data.

New Ballotpedia rows use `verification: reported`, the exact profile section link,
an observation date and an explanatory provenance note. Ballotpedia reports a
relationship; it is not the endorsing organization. No older endorsement is
renewed or carried into the general election automatically. Existing records are
preserved; absence from Ballotpedia cannot imply withdrawal. Provisional local
filers outside the common publication scope stay in the inventory/audit without
being promoted or attached.

Read the draft, complete source packets, model responses, duplicate dispositions
and unavailable queue before applying:

```sh
python3 scripts/reviewed_updates.py preview research/reviews/ballotpedia-endorsements-YYYY-MM-DD.json
python3 scripts/ballotpedia_endorsements.py archive --review research/reviews/ballotpedia-endorsements-YYYY-MM-DD.json --output-dir research/endorsements/ballotpedia-YYYY-MM-DD
python3 scripts/reviewed_updates.py apply research/reviews/ballotpedia-endorsements-YYYY-MM-DD.json
python3 scripts/build_site.py
python3 scripts/check_release.py
```

Bump `election.publication_version` before building. Keep the new immutable review,
publication registry, normalized audit, dataset, current coverage documentation
and both generated pages in the same commit. Finance and ballot research dates
must not advance. Reapplying the identical registered review is a no-op. A later
refresh uses a new review ID and exact before/after changes when replacing an
observation; the collector currently drafts additions/corroborations and never
automatically removes prior records.

The archive contains normalized source sections/rows, source hashes, collection
outcomes and the actual Jev requests/responses used by the review. It excludes raw
HTML and credentials. Raw captures stay in the ignored work directory for local
reproduction. Export refuses an existing target and verifies source bindings
before creating a new archive. `check_ballotpedia_endorsements.py` is part of the
release gate; its offline checks establish parser/decision/publication behavior,
not source truth or exhaustive endorsement coverage.
