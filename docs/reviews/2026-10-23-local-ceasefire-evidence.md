# California local ceasefire evidence refresh — October 23, 2026

This change adds **36 records across 35 printed candidacies**. Of those
candidacies, 23 previously had no published Gaza evidence; coverage rises from
309 to **332**. Existing evidence is retained. No political grades are changed
or automatically rerun. Publication version is `2026-10-23.3`.

Kevin Park gains two distinct attributed records:

* The [CAIR-SFBA tracker](https://ca.cair.com/sfba/ceasefire-tracker/) reports his
  support under the Santa Clara City Council section dated December 19, 2023,
  preserving the separate United Against Hate resolution qualification.
* [Sameena Usman's Silicon Valley Voice opinion](https://www.svvoice.com/op-ed-we-will-prevail-inshaallah-opinion/),
  published December 26, 2023, credits him with championing the effort and says
  its introduction was blocked. This is attributed opinion, not a passed vote
  or a candidate-authored statement. Reader comments are excluded.

The current official city profile and campaign body establish the historical
councilmember/current mayoral-candidate identity bridge. Their actual captured
packets, source hashes, exact excerpts and Jev judgments are archived in the
review audit.

## Coverage and unresolved work

The shared source has **214 rows in 33 sections**, checked against all **883**
printed California candidacies. Existing evidence and old collector done flags
never exclude a person from this shared-source refresh.

The main registered review evaluates 59 claims (58 tracker target matches and
one opinion), adds 33 records, and retains **26 model holds**. It accounts for
all 214 source rows: 55 reviewed rows, 124 without a plausible printed-roster
lead, and 35 source/parser holds. Some rows have multiple candidate leads;
names alone never establish identity. These are coverage dispositions, not
proof that the roster contains every official or that every candidate's entire
Gaza record is complete.

Three of the original parser holds were valid Alameda rows with paragraph
elements inside cells. A follow-up corrects quote construction and adds Tony
Daysog, Tracy Jensen and Malia Vella through a second registered review. Their
published actions remain opposition to a letter, support for a letter, and
absence, respectively. The initial audit is preserved. Its remaining **32 source
holds** concern inconsistent/duplicated municipal headings, N/A, an unspecified
amendment subject, or a malformed action/name cell. Several holds overlap.

The tracker itself places the same Oakland roster under San Bruno and uses an
Oakland heading for a different roster. These sections are held without guessing
the correct dates/cities. Rico Medina/Marty Medina's incompatible Santa Cruz
heading also fails Jev identity review. Undated congressional assessments stay
held. No previous records are deleted because a refreshed source is absent or
uncertain. The import includes opposition and absence, not just support.

## Reproducibility

* Normalized source: `research/gaza-sources/cair-ceasefire-tracker-2026-10-23.json`.
* Search discovery/retrieval audit: `research/gaza-sources/kevin-park-discovery-2026-10-23.json`.
  Searches used Serper only; snippets were leads, never publication evidence.
* Immutable review/audit: `research/reviews/cair-local-ceasefire-evidence-2026-10-23.json`
  and its `.audit.json` companion; follow-up `cair-local-block-rows-2026-10-23`.
* Every final judgment uses actual pinned `jev-1.14.0` responses, cached against
  exact request hashes. Existing source-review probability safeguards remain.
  Playground grading has no acceptance cutoff.
* Canonical dataset, immutable review registry, synchronized collector dossiers
  and both generated readers are included. Raw captures, keys, and exploratory
  unapplied model attempts remain in the ignored research workspace.

See [the repeatable workflow](../LOCAL_CEASEFIRE_RESEARCH.md) for capture, draft,
identity bridges and publication commands. The legacy collector's clipping and
stale done flags explain concrete failure paths; missing historical HTTP/search
archives prevent proving which original request omitted Park. A nationwide
search rerun is unnecessary to repair this shared California source gap.

## Validation

Fourteen offline regressions cover table completeness, qualified support and
opposition, malformed/mislabeled sections, repeat-event dates, article comments
and metadata, forged excerpts, identity bridges, refresh scope and actual
archived model bindings. The existing 23 research-gap checks also pass.
The complete offline release gate passes **36/36**, including exact rebuilds,
schema, finance, immutable publication audits, ledger reconciliation and both
reader DOM suites. Its dataset hash matches the final canonical JSON.

Four actual Jev counterexamples reject a reversed action/invented military-aid
claim, the wrong nearby politician, the wrong event year, and an opinion falsely
presented as candidate-authored with a successful resolution. The relevant
question chooses hold in every case; the request/response audit is archived in
`research/gaza-sources/source-review-negative-probes-2026-10-23.json`. These
counterfactuals are never applied as candidate evidence.

An actual full-source rerun produces **zero changes across 62 decisions**.
Both registered reviews also reapply without changing the dataset. Reversing
their 36 additions, the evidence coverage count and publication version exactly
recovers the parent dataset: rosters, endorsements, finance and existing Gaza
records are untouched. Credential and whitespace checks pass.

The local playground previews this dataset; its 65 stored runs remain intact.
An actual Chrome selection of Kevin Park shows both new evidence inputs plus
his separate CAIR Action preference, with no page errors. Stored grades remain
historical until explicitly rerun.
