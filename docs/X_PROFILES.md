# Recover missing X profiles from campaign websites

`scripts/research_x_profiles.py` reads the **current canonical inventory** rather
than historical discovery batches. It includes printed candidacies at every
level and the common eligible nationwide provisional scope. Local provisional
filers stay outside publication scope. It never replaces an existing `x_url`.

This is a first-party campaign self-link pass, not an exhaustive account search.
Missing campaign sites, unreadable pages, pages without a captured profile link,
identity uncertainty, multiple accounts and cross-candidate handle collisions
have separate queue statuses. None means the candidate has no X account.

## Run a bounded check, then a full pass

From the repository root with Python 3.10+:

```sh
python3 scripts/research_x_profiles.py plan
python3 scripts/research_x_profiles.py collect --candidate 'Xavier Becerra'
python3 scripts/research_x_profiles.py collect
python3 scripts/research_x_profiles.py enrich
python3 scripts/research_x_profiles.py draft --id campaign-x-profiles-YYYY-MM-DD --output research/x-profiles/YYYY-MM-DD/review.json --jev-key-file /secure/path/jev-key --publication-version YYYY-MM-DD.N
```

Replace the dates/version with the actual review date and next publication
version. `--dataset` and `--work-dir` are global options before the subcommand.
Default work directory `.research/x-profiles/` is ignored. `collect` accepts
repeated exact `--candidate` filters, `--limit`, `--workers` (1–4, default 4), and
`--force`. It requests each distinct recorded campaign URL once, retaining raw
content by SHA-256. Seven-day cache entries include failures; use `--force` to
retry them earlier. Existing cache entries never become permanent done flags.

The optional `enrich` command looks up **only handles actually linked on captured
campaign pages**, using `api.fxtwitter.com`. It validates the returned handle and
records the actual timestamp/hash, name, biography, location and profile website.
This is third-party corroboration, not X's verification badge. Empty success
responses, malformed metadata, errors and wrong handles stay unavailable. The
campaign evidence can still be reviewed if this service is unavailable.

No web search is called. If search-based discovery is added later, use only the
owner-authorized Serper service; result snippets remain leads rather than proof
of ownership. Credentials must remain outside the repository and generated pages.

## Acceptance and safety rules

Only actual `a[href]` profile links on recorded campaign pages are collected.
Legacy Twitter URLs normalize to `https://x.com/HANDLE`. Post/embed URLs, share
intents, reserved routes, script/plain-text strings and spoofed hosts are excluded.
Jev `jev-1.13.0` is the sole judgment model, with separate typed questions for:

- Exact candidate/campaign and office/jurisdiction identity: selected probability
  at least 0.90.
- Explicit presentation of the candidate's own personal/campaign social account:
  selected probability at least 0.95. Endorser, party, vendor, embed-author and
  mention links are not ownership evidence.

Every question contains the candidate/office, captured source URL, title/page
text, and actual anchor HTML/context. Optional profile metadata is supplied as
corroboration. Source content is untrusted evidence, never model instructions.
The complete request/model contract keys the decision cache. Low-confidence
choices remain held. Two accepted accounts remain held rather than choosing one
arbitrarily. A handle already present as secondary cannot be duplicated as primary.
Existing and same-batch handles assigned to different candidate names/parties
produce collision holds. A political organization is not silently substituted
for its candidate.

`draft` verifies the raw captured bytes and normalized evidence before sealing an
immutable JSON review. It contains all page outcomes, normalized evidence,
actual source hashes/timestamps, Jev requests/responses and the policy decision.
It refuses to overwrite an existing review. Raw HTML/API response files and keys
stay in the ignored work directory. Cached judgments are reusable only for exact
requests; a new site/candidate/source requires a new judgment.

## Inspect and apply

Review the proposed/held outcomes and source context before applying:

```sh
python3 scripts/research_x_profiles.py apply research/x-profiles/YYYY-MM-DD/review.json
python3 scripts/build_site.py
python3 scripts/check_release.py
```

This focused link adapter uses its own source-bound before/after dataset hashes;
`reviewed_updates.py` supports structured research records, not scalar profile
links. The review replays every classification from the archived requests and
responses without network access, rejects stale dataset/campaign/candidate
bindings, appends dated source references, recomputes printed X coverage, and
applies only missing `x_url` fields plus provenance/publication metadata. An exact
reapplication is a no-op. Concurrent unrelated data changes require a new draft
against the new baseline; never force an old draft onto changed data.

Commit the immutable review, code, updated coverage/prose, canonical dataset and
both generated readers together. Preserve all roster, finance, endorsement,
platform and Gaza research. The 21 offline regressions in
`check_x_profiles.py` are included in the 31-check release gate; they establish
collection/decision/publication behavior, not exhaustive coverage or source truth.
