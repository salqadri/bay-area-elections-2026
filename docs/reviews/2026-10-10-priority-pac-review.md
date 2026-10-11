# Priority PAC source review — October 10, 2026

This PR addresses missing explicit organization relationships under the owner's policy accepting older endorsements without renewal research. It adds two Hindu American PAC endorsements and one reported United Democracy Project support record, all visibly marked historical. The proposed dataset is schema 1.16 with 389 recommendation records under 199 of 869 printed candidacies. No ballot roster, official party, FEC record, Gaza evidence or election-wide freshness date changes.

## Findings

| Candidate | Current candidacy | Captured relationship | Preserved source context |
| --- | --- | --- | --- |
| Murali Srinivasan | `CA2026-109`, Sunnyvale Council District 3 | Endorsed by Hindu American PAC | Source biography identifies 2022 District 3 candidacy. |
| Yang Shao | `CA2026-181`, Alameda County Water District Ward 3 | Endorsed by Hindu American PAC | Source lists Fremont City Council and links the same verified campaign URL; year unspecified. |
| Kevin Mullin | `CA2026-230`, House CD-15 | Supported by United Democracy Project; reported by AIPAC | AIPAC report explicitly describes UDP help in 2022. Election phase unspecified. |

The [Hindu American PAC list](https://www.hinduamericanpac.com/endorsements) contains 17 current-list and eight previously-endorsed entries. All 25 have dispositions in the [immutable review manifest](../../research/reviews/priority-pac-endorsements-2026-10-10.json): two additions, Melissa Hernandez already published without duplication, and 22 unmatched printed candidates. No new candidates or races were created. Its criticism of Aisha Wahab's caste legislation supplies no explicit opposition recommendation. No candidate-specific Gaza notes were found on this source.

The [AIPAC report about 2022](https://aipac.org/memos/2022-political-success) explicitly names Mullin among congressional candidates helped by United Democracy Project. The seven other people in that UDP list have no printed-roster match in the five-county inventory: Shontel Brown, Robert Garcia, Haley Stevens, Henry Cuellar, Valerie Foushee, Glenn Ivey and Don Davis. AIPAC is the reporting publisher; UDP is the organization providing support. This establishes reported historical campaign support, not an individually stated PAC endorsement or a donation amount.

## AIPAC PAC limitation

The [featured portal](https://candidates.aipacpac.org/page/featured), PAC homepage and candidates redirect exposed navigation, sign-in/register and contribution-processing text, with no individual endorsement assertions. The [official politics page](https://www.aipac.org/politics) describes the portal as a way to contribute to candidates. Bounded official-domain searches and older static-page attempts produced no additional usable candidate-specific endorsement text. No access controls were bypassed.

All 22 printed congressional candidates remain unknown for AIPAC PAC. Failure to retrieve its list does not establish absence of endorsements. Contributions, aggregate caucus statistics and UDP support were not turned into PAC endorsements. This pass did not audit the seven inherited pages or research regional campaign claims.

## Repeatable implementation

The common capture contract feeds `reviewed_updates.py`; every initial draft is held. The manually reviewed manifest records exact identities, source observations, actual October 10 capture dates, content hashes, additions and explicit hold reasons. Source hashes cover the retrieved tool text; raw captures remain outside Git. [publication-reviews.json](../../research/publication-reviews.json) registers the immutable manifest hash.

Schema 1.16 adds optional `historical: true`, requiring verification and a shared context note. Both readers label historical records and preserve the note. The shared summary no longer claims that every observation belongs to the 2026 cycle. Publication and update keys distinguish historical from current records at the same URL, so a later source renewal can coexist with the older observation. No publisher-specific dated importer was added; the same workflow can be used for other county scopes.

```sh
python3 scripts/reviewed_updates.py apply research/reviews/priority-pac-endorsements-2026-10-10.json
python3 scripts/build_site.py
python3 scripts/check_release.py
git diff --check
```

Rerunning apply against this branch is a no-op. Tests cover required historical provenance/context, historical/current coexistence and rerun behavior, and historical labeling/notes in both actual embedded readers. All 16 checks in the full offline gate passed on October 10, 2026. The gate checks internal consistency and regressions; it does not establish source completeness, live address-service availability or browser rendering.

## Hermes review and local testing

Review the three accepted decisions and their notes (`N301`–`N303`), the source limits and all HAP dispositions. Confirm that Yang Shao's current water-district race is not presented as the source's endorsed office, and that Mullin's support is attributed to UDP with AIPAC as reporter. The 159 inherited records remain unaudited.

The generated `index.html` is a standalone preview. For a local HTTP preview of both pages, use an isolated worktree on the machine where Hermes and the browser run:

```sh
git fetch origin priority-pac-endorsements-20261010
git worktree add ../bay-area-pac-preview origin/priority-pac-endorsements-20261010
python3 -m http.server 8000 --bind 127.0.0.1 --directory ../bay-area-pac-preview
```

Open `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/ballot.html`. In the explorer, search Murali Srinivasan, Yang Shao and Kevin Mullin and expand their recommendations. In the ballot page, browse Santa Clara for Murali, Alameda for Yang and San Mateo for Mullin. Confirm historical labels, office/year notes and source links. Address lookup requires separate internet access.

The PR remains unmerged for review. The workspace preview is separate from the live GitHub Pages site; only a main-branch merge publishes there.
