# Refresh research when adding races

Adding a candidate to the roster is not proof that shared publishers, campaign
images or topic-specific research were refreshed. The October 23 AZ-01 repair
([audit](reviews/2026-10-23-az01-research-gaps.md)) fixes all three gaps.

## Campaign images have a separate publication path

The campaign text extractor deliberately rejects empty-alt logos and filename
identity guesses. A successful text attach therefore does **not** publish logo
images. Keep the neutral image review as a separate required publication artifact:

```sh
python3 scripts/campaign_endorsements.py plan
python3 scripts/campaign_endorsements.py crawl --refresh --workers 4
python3 scripts/review_endorsement_images.py export-ledger --db .research/endorsements/campaign.sqlite3 --output-dir .research/images/NEW-RUN
python3 scripts/review_endorsement_images.py build-queue --queue .research/images/NEW-RUN/queue.json --id campaign-images-YYYY-MM-DD --reviewed-on YYYY-MM-DD --output research/reviews/campaign-images-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py preview research/reviews/campaign-images-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py apply research/reviews/campaign-images-YYYY-MM-DD.json
```

Use new directories/IDs and actual observation dates. The batch runner now drafts
this image-publication review automatically in a fresh run directory, before text
extraction, and says that applying text does not apply images. It never publishes
by itself. The image builder supports printed and eligible provisional nationwide
Federal/Governor records without promoting provisional filers; local provisional
filers remain outside the common publication scope.

For a cheaper audit without an existing crawl ledger:

```sh
python3 scripts/review_endorsement_images.py plan-missing --nationwide-house --output .research/images/PLAN.json
python3 scripts/review_endorsement_images.py capture-plan --plan .research/images/PLAN.json --checked-on YYYY-MM-DD --output-dir research/endorsements/images-YYYY-MM-DD
python3 scripts/review_endorsement_images.py build-queue --queue research/endorsements/images-YYYY-MM-DD/queue.json --id campaign-images-YYYY-MM-DD --reviewed-on YYYY-MM-DD --output research/reviews/campaign-images-YYYY-MM-DD.json
```

The capture command requires a new output directory and refuses an existing run before making requests or changing its queue.

Omit `--nationwide-house` for all printed candidates. This planner follows actual
published campaign-claim endorsement-page URLs, rather than guessing paths. It
flags pages with no image observations or with text observed after the image
snapshot. It is not a complete crawl or proof that a partially captured gallery
is complete. The ledger crawl/export remains the path for logo-only pages and
other pages without any published text claim.

Parser **campaign-dom-images-3** additionally reads explicitly supplied responsive
lazy URLs (`data-src-desktop-1x`, `data-src-mobile-1x`, plus common lazy fields)
when `src` is a data-URI placeholder. It never guesses a higher resolution or an
organization identity. Current ledger exports require the current parser, forcing
old caches back into the recrawl queue. Immutable v2 packets still replay by their
original hashes; archive checks retain all other source/quote/model bindings.

`all-content` retains non-chrome images neutrally, including unknown logos,
portraits and program badges. No image-byte downloads/copies are made. Every
supported occurrence has a disposition; unsupported/empty image URLs remain
explicit holds rather than being silently discarded. See [image workflow](ENDORSEMENT_IMAGES.md).

## Refresh shared publishers against the current roster

Hindu American PAC was already a seed in `research/endorsements/sources.json`.
Its older curated observations were not an automatic refresh for races added
later. `import_hapac.py` now parses the publisher's explicit **Current
Endorsements** list once and matches it to every tracked printed candidacy.
Older biography entries and the separate previous-officials list cannot create
current endorsements by themselves.

After retrieving actual HTML from the recorded publisher URL:

```sh
python3 scripts/import_hapac.py --html /path/to/actual-hapac.html --checked-on YYYY-MM-DD --jev-key-file /secure/path/jev-key --id hapac-current-YYYY-MM-DD --output research/reviews/hapac-current-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py preview research/reviews/hapac-current-YYYY-MM-DD.json
python3 scripts/reviewed_updates.py apply research/reviews/hapac-current-YYYY-MM-DD.json
```

Jev must establish the exact current person/candidacy at selected probability
≥0.90. Office/cycle conflicts stay held. Phase remains unspecified. Equivalent
current relationships are corroborations, not extra displayed records. Historical
observations remain separate and dated; a new explicit current listing can
establish renewal without rewriting the old record. Every current card receives
an added/corroborated/held/out-of-scope disposition, with actual model responses
and source hash in the companion audit. This is a named first-party statement,
not an identity inferred from the campaign's HAPAC logo filename.

## Audit evidence gaps independently of collector done flags

For IHRA definitions, AB 715/AB 1468 and Israel/Palestine education policy, use
[the all-active-candidate topic refresh](EDUCATION_POLICY_RESEARCH.md). Its scope
includes candidates with existing Gaza evidence and does not infer political
positions from ordinary antisemitism condemnation or Holocaust education.


For California local action sources, first run the
[shared ceasefire-tracker refresh](LOCAL_CEASEFIRE_RESEARCH.md). It evaluates the
whole current California roster even when candidates already have evidence.
The generic planner/collector additionally accept `--refresh-existing --state CA`
for a bounded update pass; their default remains the missing-evidence queue.

```sh
python3 scripts/research_gaza_gaps.py plan --output .research/gaza-gaps/PLAN.json
python3 scripts/research_gaza_gaps.py collect --candidate 'Amish Shah' --candidate 'Jay Feely' --limit 2 --output-dir .research/gaza-gaps/NEW-RUN --serper-key-file /secure/path/serper-key
```

The plan reads current published records, not the old per-person `done` flag.
It includes candidate-specific Israel/Palestine points and exact source URLs
already captured in general platform research, including nested `/issues` pages.
Its fingerprint changes with candidate/source context. A missing record means
source review is pending, not neutrality or absence of a position.

Current discovery version `gaza-discovery-v4-context-followups` adds debate/backlash,
UNRWA explanation/follow-up and Block the Bombs cosponsorship queries, alongside
the earlier dedicated IHRA,
AB 715/AB 1468 and education queries and retains the earlier divestment layer.
That layer separates the name + Israel +
divestment search from jurisdiction + ceasefire queries, and adds a BDS/boycott/
bonds/investment query. Divestment/BDS-only result snippets remain discovery leads
instead of being discarded. Existing candidate fingerprints include this search
version. Run a fresh bounded collection for a previously incomplete candidate;
do not treat old collector `done` flags as an empty-stance finding. Neither
search terms nor snippets themselves create an evidence record.

For news pages with an explicit `<time itemprop="datePublished" datetime="…">`,
`capture --kind dated-html` extracts the unique calendar publication date;
source-bound review rejects a proposed `page_metadata` date that differs. Older
capture kinds retain their exact replay format. Use actual retrieved HTML and
precise excerpts so navigation and unrelated stories cannot establish a claim.

Collection is bounded (default ten candidates, at most twelve source attempts per
candidate), with every deferred/unavailable source and search recorded. Omit the
Serper key to fetch only recorded first-party leads. Searches use only Serper;
snippets are discovery leads. Actual source captures, not snippets, support
publication. Collection always ends `pending_claim_review`, never a published
finding of silence. Use fresh output directories to preserve observations.

Capture other retrieved source bytes and draft proposed claims with Jev:

```sh
python3 scripts/research_gaza_gaps.py capture --url https://source.example/actual-page --raw /path/to/actual-page.html --checked-on YYYY-MM-DD --output .research/gaza-gaps/source.json
python3 scripts/research_gaza_gaps.py draft --claims /path/to/claims.json --jev-key-file /secure/path/jev-key --id gaza-source-review-YYYY-MM-DD --checked-on YYYY-MM-DD --output research/reviews/gaza-source-review-YYYY-MM-DD.json
```

`claims.json` is an array with exact candidacy/field, capture and raw-capture paths,
proposed schema-valid record, source publisher/role, identity/date explanations,
and optional exact source context/date excerpt. The committed AZ-01 claims show
the format. For a verified author's X post, use `capture --kind x-json` with the
actual Fxtwitter response and canonical X status URL. Post ID, author and
snowflake/API timestamps must agree. This is a transparently labelled retrieved
copy, not proof that X itself served the content. Quoted/reposted material cannot
be treated as the candidate's own position without source review.

Draft rechecks actual raw bytes against the packet and verifies source-local
context/quotes (≤25 words). Jev is the only judgment model: identity ≥0.90,
faithful attributed meaning ≥0.85, and date provenance ≥0.90. Undated campaign
pages use `gaza_platform` with an observation date; they cannot acquire invented
statement dates. Guide assessments use explicit `source_observed` provenance and
`voter_guide` kind. Historical X/news dates remain historical. Holds remain visible.

Apply through `reviewed_updates.py`, then synchronize the public evidence back to
the collector without discarding drafts:

```sh
python3 scripts/reviewed_updates.py apply research/reviews/gaza-source-review-YYYY-MM-DD.json
python3 research/gaza-stance/merge_gaza_evidence.py --sync-published
python3 scripts/build_site.py
python3 scripts/check_release.py
```

Keep the immutable reviews/audits, normalized source/model evidence, coverage,
canonical JSON and generated readers together. Credentials/raw captures stay
outside Git. Reapply each identical registered review to verify a no-op. These
steps do not publish held Gaza grades or infer positions from outside spending.
The release gate includes `check_research_gaps.py`; source truth and exhaustive
coverage still require source review.

Source entries in Gaza review drafts bind the page URL to the exact candidate and contest. Several candidates can share a publisher guide without overwriting one another's source attribution.

See [evidence context](EVIDENCE_CONTEXT.md) for verified secondary X accounts,
official bill-status XML and the all-candidate context-lead audit.
