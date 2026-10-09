# Post-enrichment review — October 8, 2026 (America/Los_Angeles)

Reviewed upstream commit `d0ee70b718c663dfc6b0b835c0621be492f4a226`, after Hermes completed its work. This document describes corrections on the review branch, not a claim that the public site has deployed them.

## Scope and method

Compared all committed changes with the preceding reviewed snapshot `6ba1537b8106b858289f95ff4544bcf8ec4dc1e7`; inspected the application/data integration, all 300 current evidence summaries, relevant stored excerpts, and targeted original sources. The core 416-contest inventory, candidate rosters, and structured candidate FEC records are unchanged. This is not an independent recertification of all 869 printed candidate entries.

**Jev has not assessed these records.** The supplied key does not identify its API endpoint/authentication protocol; documentation or an existing integration is needed. A Serper request to `https://google.serper.dev/search` was rejected by the execution environment with HTTP 403, “Calls to this URL are not allowed.” No alternative search engine was used. Source verification used direct opens of cited URLs and links from those pages.

The research collector, resumable ledger, `validate_evidence.py`, and merge implementation still live outside this repository. Their reported behavior cannot be audited or reproduced from this repository alone.

## Result of the manual correction pass

| Disposition | Evidence items |
| --- | ---: |
| Original input | 300 |
| Summaries rewritten | 44 |
| Quarantined with original records and reasons | 68 |
| Left unchanged after summary screening | 188 |
| Retained in this branch's dataset | 232 |

The remaining evidence appears under **81 candidates**. County counts overlap: Alameda 36, Contra Costa 23, San Francisco 22, San Mateo 24, Santa Clara 28. An unchanged item is not a certification of identity, source accuracy, or dates. Quarantine is reversible and does not assert that every held record is false.

The machine-readable [per-item review](2026-10-08-summary-review.json) covers every original evidence ID, records each before/after summary, and distinguishes source-reopened rewrites from edits based on the stored excerpt or snapshot. [The quarantine file](evidence-quarantine.json) preserves every held record and explains what is required before restoration.

## Highest-priority findings

### 1. Identity and attribution failures remain after the earlier cleanup

Hermes removed the previously confirmed Shruti Kumar/Harvard, Gary McCoy/cartoonist, Amy Callaghan/SNP, and Fred Simon/JFrog examples. It also removed the unsupported 2018 Ahrens/Pellerin co-signature claims. Those fixes are present.

Other unestablished identity matches remain in the new input: Sarah Duffy/Irish councillor under Brisbane School District; Karen Fletcher/Wirral pension campaigner under Pleasanton Unified; Kimberly White/Arcata council under El Cerrito; Craig Pearson/Windsor Star editor under Oakley Union; and a cluster of journalists, academics, and same-name social accounts. There are **25 identity-unverified items** in this branch's quarantine. They need positive identity evidence, not merely a name match. Examples of the actual source contexts: [Wirral statement](https://www.labournet.net/ukunion/2512/MPF1_Fletcher.html), [Arcata letter](https://kymkemp.com/2024/11/01/redwood-peace-and-justice-coalition-supports-creating-an-arcata-sister-city-with-palestine-in-letter-to-the-editor/), [Canadian editor letter](https://www.cjpmemap.ca/2024_08_13_ln_windsor_star).

Three additional items (Jeff Frese `GE-0109`, John Delgado `GE-0254`, Jeremy Lee `GE-0010`) cite another account's parent X post instead of the alleged candidate reply. The parent-post snowflake date differs from the stored date. These require a direct reply URL, the reply's own date, and verified author identity.

### 2. The source sometimes contradicts or fails to support the summary

- **Ruben Abrica, GE-0277:** the source body says he was absent; the summary claimed he was present, apparently from a photo caption. [Source](https://www.sfgate.com/news/bayarea/article/east-palo-alto-mayor-s-oct-7-remembrance-22466114.php).
- **Malia Vella, GE-0167:** leaving to care for her child before a vote is not a recorded abstention. The rewrite explicitly distinguishes absence from support or opposition. [Source](https://eastbayinsiders.substack.com/p/alameda-city-council-rejects-mayors).
- **Malia Vella, GE-0168:** a short live-post excerpt and an AD-18 event hashtag do not establish a formal council divestment vote. Held pending a roll call or other direct attribution.
- **Gail Pellerin, GE-0314:** the excerpt praising London Breed's leadership supplies no context showing whether the linked position supported or opposed the resolution. Held pending the complete post/thread.

### 3. Headline summaries obscure positions and invite invented replacements

The user's example, Becerra `GE-0049`, cannot honestly be rewritten into a Gaza position: the [L.A. Times article](https://www.latimes.com/politics/story/2025-05-08/california-gubernatorial-candidates-israel-palestine-villaraigosa-porter-yee-thurmond-becerra) quotes his praise of California's Jewish community, but no specific Gaza policy. That record is quarantined. This is not evidence of neutrality.

His separate `GE-0095` now links to the [CalMatters transcript](https://calmatters.org/california-voter-guide-2026/governor/videos/transcripts/) and says: “Asked whether Israel's actions in Gaza were genocide, Becerra criticized Netanyahu's conduct and called for international accountability, without answering yes or no.”

Other substantive rewrites include DeSaulnier's opposition to offensive military aid (`GE-0111`), Liccardo's humanitarian-aid demands (`GE-0105`), Wiener's qualified position on Iron Dome purchases (`GE-0030`), his 2024 distinction between ending the war and endorsing local resolutions (`GE-0084`), and the reasons Eakin and Howard opposed Redwood City's resolution (`GE-0280/0281`). The Redwood City officials are councilmembers; the vote rejected the resolution, rather than constituting a mayoral veto. [Redwood City source](https://peninsula360press.com/en/redwood-city-veto-gaza-resolution/).

Five title-only official statements could not be reopened: Harder `GE-0244`, Simon `GE-0120`, Panetta `GE-0293/0296/0410`. Their titles do not establish their substance. They are retained in the queue until their text is available. Rewriting from a title alone would manufacture a position.

### 4. Financial summaries confuse campaign money with outside spending and cycle scope

The structured `candidate.fec` total-receipts fields are unchanged. The defects are in the newer narrative evidence layer.

- [Mullin's tracker](https://whofundsmyrep.com/rep/kevin-mullin) separates $130,185 in direct/earmarked contributions from $603,681 in outside spending supporting him. Calling the combined $733,866 money he “received” was misleading.
- [Liccardo's tracker](https://whofundsmyrep.com/rep/sam-t-liccardo) separates $51,389 in contributions from $134,844 in supportive outside spending.
- [Wahab's tracker](https://whofundsmyrep.com/rep/aisha-wahab) separates $19,602 received, $104,048 spent for her, and $2,253,111 spent against her in the race.

Rewrites retain these distinctions, attribute the claims to the tracker, and distinguish totals across tracked election cycles from a 2026-only total. They do not claim an independent transaction-level FEC audit. McBride's unsupported positive AIPAC-link claim (`GE-0245`) is held pending reconciliation with the other tracker's zero result and dated FEC filings. A scoped “no record in this tracker” does not prove that no relevant contribution exists anywhere.

### 5. Remaining chronology, duplicates, and low-value evidence

The prior correction added date provenance, but both UIs ignored it. Four retained archive-bounded items could look like precisely dated statements. Both pages now label archive bounds and distinguish page metadata, event dates, and post dates. Garamendi's 2010-speech/2022-URL contradiction (`GE-0234`) is held pending the original date. Two summaries spanning October and November 2023 now use year precision with an explanatory note.

Vin Kruttiventi `GE-0194/0195` was the same X status under two handles. One is retained; the duplicate is quarantined. Third-party petitions, unsupported criticism, directory placeholders, archive tags, an unsubscribe request, and unrelated material are held when they do not establish an attributable candidate position or action. Truncated summaries are rewritten as complete sentences instead of slicing at 240 characters.

## Application and validation findings

- **Filtered JSON counts were wrong:** the export recalculated older coverage metrics but retained full-inventory counts for X accounts, secondary accounts, campaign sites, and Gaza evidence. All four now describe the downloaded subset; a regression exercises an actual filtered download.
- **Archive-date provenance was hidden:** both renderers now display it, with UI regression checks.
- **Year-only `0000` passed the custom partial-date validator:** it is now rejected, with a negative case. Hermes's month/day validity checks and candidate-list `<details>` nesting fix were already present and remain intact.
- **Three campaign links still opened generic platform homepages:** Dennis P. Sanchez/Anedot, Kevin E. Jenkins/Donorbox, Sonja Shephard/Nextdoor. The unsupported URLs are omitted and recorded in the review log; campaign URL coverage becomes 383.
- **Known quarantined material could be remerged:** the repository now checks candidate/source fingerprints, including changed X handles and tracking parameters, and rejects unresolved held sources even if their evidence IDs change. Distinct claims from one legitimate source are allowed. Duplicate-source quarantine uses a separate duplicate check so the retained representative remains valid.

`scripts/check_evidence.py` is called by `check_data.py` and has targeted regressions. It guards known failures; it cannot establish candidate identity, article truth, or a complete position record. The external merge must reconcile this repository's quarantine before publishing again.

## Validation and remaining work

All 10 upstream checks passed before editing. All **11 release checks passed** after the corrections, including the new evidence guard and its seven regression cases. Core contest/roster/FEC preservation, audit counts, and absence of the supplied credentials were also checked. Rebuilt HTML must match the source JSON, schema, and scripts. UI checks use the existing minimal DOM harness, not a real-browser rendering test.

The inventory still has 80 unresolved contests and one confirmed contest without a verified printed roster. Election research remains October 4 and structured FEC research October 6. The address-service code is unchanged, and this review does not establish live provider availability.

To finish the specifically requested Jev stage, supply Jev's API documentation/base URL and enable outbound API access to its verified host and `google.serper.dev`. Do not put keys in the repository or frontend. `python3 scripts/prepare_jev_review.py --include-quarantine` prepares 300 bounded review packets and explicitly reports `api_called: false`. It can accept source text keyed by evidence ID with `--source-texts`; source URLs must match. The script is preparation, not a Jev client or completed model audit. Model proposals must retain source support and receive review before application.
