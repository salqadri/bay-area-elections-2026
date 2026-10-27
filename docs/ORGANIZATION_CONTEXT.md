# Organization context in model inputs

New grader and playground states use **v14**. `scripts/organization_context.py`
resolves documented organizations through the versioned
`research/gaza-grading/organization-context-v1.json` registry. The registry has
15 entries, with primary-source passages/filing facts and an exact-hash Jev
review in `organization-context-v1.review.json`. This is a context layer, not
a candidate score or an automatic endorsement importer.

## Meaning and identity

- Federal spending resolves by exact FEC committee ID. CAL-ACCESS uses a separate
  ID namespace; name similarity never supplies a committee funding link.
- Endorsement names use exact normalized registered aliases. Explicit organization
  mentions in already-projected Gaza evidence use whole aliases, longest first.
  A mention of Track AIPAC does not also match AIPAC. Discarded historical/mixed
  funding evidence is not rescanned or reintroduced.
- AIPAC, its PAC, UDP, J Street, JStreetPAC and J Street Action Fund retain their
  different roles and policy descriptions. CAIR Action and Vote for Peace retain
  recommendation tiers, phase, joint status and source qualifications. Vote for
  Peace inclusion alone is not endorsement. No political label comes from an
  organization's religious/ethnic identity.
- FEC receipts and UDP disbursements confirm funding to BOLD America and EDW Action
  Fund in 2026, and 314 Action Fund in **2024**. The dates stay explicit. UDP also
  reports a contribution to Palmetto Action in August 2026; that context is explicitly
  donor-reported because the receipt query did not return recipient-side confirmation.
- **Owner criterion:** a documented UDP funding connection is sufficient to count
  the receiving organization as a negative funding signal for Palestinian justice.
  The state labels this as `guide_assessment`, separate from sourced facts. It does
  not require candidate-specific earmarking. Actual spending direction remains
  supporting/opposing; no transfer becomes a direct candidate contribution, proof
  of control, or an assertion about the topic of every ad.

## Input contract

`spenders_supporting`, `spenders_opposing` and their `ca_` equivalents now contain
objects with `spender` and exact `amount_usd`, plus either an `organization_context`
reference or `relevance: "unestablished"`. They retain the largest twelve per direction
**plus all registered relevant spenders**, so a small relevant expenditure is not
silently lost. These lists are not exhaustive financial totals.

`organization_context` includes only organizations actually appearing in the state,
deduplicated by entity, with role, relevance, source links, observed spellings and
any dated funding relationship. `spending_context` tells models to omit unestablished
spender relevance from a Palestine assessment unless other supplied evidence makes
the connection. Unknown relevance is not proof an organization is unrelated.

The shared builder handles both federal and California spending. Focused endorsement
selection combines the existing v3 focus list with the new reviewed aliases. Candidate
records and endorsement relationships are not rewritten.

## Repeatable funding discovery

```sh
python3 scripts/discover_organization_funding.py \
  --donor C00799031 --start 2024-01-01 --end 2026-10-27 \
  --fec-key-file /secure/fec-key \
  --output .research/organization-funding/udp.json
```

`FEC_API_KEY` is also supported. The script walks Schedule B keyset pagination,
selects positive non-memo intercommittee contributions, retains exact recipient IDs,
and marks which recipients appear among tracked spenders and in the context registry.
It stores no key, performs no automatic classification and makes no candidate edits.
It reports leads rather than totals: refunds, other schedules, intermediaries and
non-committee recipients are outside its coverage. Other donors can be checked with
`--donor`. Date bounds are explicit, never inferred from a report's publication date.

The initial capture is `research/gaza-grading/organization-funding-leads-2026-10-27.json`:
24 positive transfers to nine recipients since 2024, four of them tracked spenders.
Before registering a new organization, check committee identity, source dates and
recipient filings; retain donor attribution if only that side is available. Review
the proposed role/relevance with Jev, archive the exact request/response and registry
hash, then add regression coverage. Runtime state generation remains fully offline.

## Hermes and historical evaluations

No candidate evaluations were rerun for this change. Saved questions, thresholds,
requests, responses, public grades and explanations remain unchanged. Old requests
retain their old string spending format and exact hashes; never retrofit the new
context into them and claim it was evaluated.

For future evaluations, the new state is automatic in both the CLI and playground.
For summaries of already-published grades, use the frozen input as required by the
explanation workflow. New organization research must not be represented as a reason
the old model used. If separately supplied as an editorial reference, label it as
additional context, retain its provenance separately, and do not replace the archived
candidate record. To make it part of the actual evaluated record requires an explicit
new evaluation and publication.

Checks: `python3 scripts/check_organization_context.py` and the full offline release gate.
