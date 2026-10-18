# Campaign endorsement batch — October 18, 2026

The original 381-site batch and one recovered-site follow-up are complete. This
is a portable research audit, **not an applied publication review**. The public
dataset is unchanged. Both site views now display their existing text and image
entries together in one endorsements list.

| Result | Count |
| --- | ---: |
| Campaign sites attempted | 381 |
| Sites captured and extracted | 375 |
| Sites still unavailable/unreadable | 6 |
| Captured resources | 710 |
| Image occurrences inventoried | 9,491 |
| Source-verified proposals classified by Jev | 16,695 |
| Machine acceptances pending publication review | 7,211 |
| Other Jev outcomes or confidence below 0.75 | 9,484 |
| Additional extraction/quote/attribution holds | 738 |

Of the machine acceptances, 5,414 share an exact
normalized name with an existing record for that candidacy,
281 may be title/name variants, and
1,516 have unmatched names. These are comparison hints;
none establishes a new distinct endorser or justifies merging people. Each
proposal retains its exact name, quote, campaign URL, captured source binding,
model response, probabilities and dated decision. Campaign claims remain
campaign claims, and observation dates do not establish a current election cycle.

## Reviewer instructions

1. Run `python3 scripts/check_campaign_endorsement_batch.py research/endorsements/batch-2026-10-18`.
2. Read `manifest.json`, including fetch failures and the additional-site queue.
   Each listed `sites/*.json` packet is hash-bound and carries candidate/office
   references, captured page text, complete image inventories, crawl limits,
   extraction holds and all named proposals.
3. Prioritize unmatched names, then possible variants. Confirm that the source
   is endorsing this candidacy/office and establish the cycle/phase. Verify quote
   attribution: a name and a quote on the same page do not alone prove the person
   said it. Preserve publisher observations and historical records; absence from
   a refreshed page never means withdrawal.
4. Prepare explicit before/after changes using `reviewed_updates.py` only after
   this publication audit. Register a new immutable review, rebuild both pages
   and rerun the release gate. **Do not attach all machine acceptances directly.**
5. Review image source placement before adding entries. Inventory membership,
   filenames and alt text never identify an endorser. Existing image entries
   appear beside textual entries in the same public list; source/filename/alt
   metadata remain available per image.

Six original sites remain unresolved:

- Chris McDaniels (https://chris4albany.com/)
- Steve Hilton (https://stevehiltonforgovernor.com/)
- Francis Rojas (http://francisrojas.org/)
- Larry Bird (https://bird4larpd.com/)
- Pearci "PJ" Bastiany III (https://bastiany-campaign-site.replit.app/)
- Avery Wang (https://www.averyforpaloaltoschoolboard.com/)

Use the exact URLs/errors in the manifest; failed requests do not prove absence.
The recovered `votejohncraig.com` site was captured and extracted successfully;
its 42 proposals were reviewed in three additional Jev calls.

Latest upstream data also added 162 distinct campaign sites for provisional
nationwide candidates after the original batch was fixed. They are listed in
`additional_site_queue` and have **not** been scanned in this batch. The shared
Luis Reynoso site still requires office-specific attribution.

## Reproduction and limits

`export_campaign_endorsement_batch.py --db PATH --output-dir NEW_DIRECTORY`
exports a read-only SQLite snapshot without network/model calls or credentials.
The output directory must be empty; preserve prior snapshots. The audit checker
verifies packet fingerprints, counts, source-local quotes, proposal identities,
source bindings and actual Jev acceptance probabilities. It is an offline
consistency check, not independent certification of political claims.

The local model reports 5,318,192 tokens for this run.
Extraction used the local model server; there were no paid extraction API
calls. Jev usage is separate. The four media resources mistakenly decoded by
the earlier crawler yielded no accepted endorsements. Their decoded binary
content is omitted from this archive: only URLs, hashes and format warnings are
retained. The new media guard prevents sending those bytes to text extraction.
No image files or API keys are stored in this audit.

The automated run finished at 4:05 p.m. Pacific, followed by the recovered-site
retry. Scott Wiener was browser-tested in both readers at 1440px and 390px:
**59 text + 50 external image entries in one list**, all 50 previews loaded, no
separate image section, no filename-derived names, and no horizontal overflow.
Jimmy Panetta, Gail Pellerin and Connie Chan also have offline mixed-list checks.

Validation: all **29 current release checks passed**. Two exports produced identical
381 source packets. A fabricated quote was rejected even after the packet hash
and proposal ID were rewritten. Browser checks used the original external CDN
URLs; no image binaries were copied into Git.
