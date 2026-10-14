# Inline research packet — final ballot status, 6 remaining unresolved contests (October 14, 2026)

Researcher: orchestrator (inline, no subagents). All sources retrieved Oct 13–14, 2026.

## Santa Clara County — CA2026-225/226/227/228 (Lion's Gate CSD FT+ST, San Martin CWD, SCVCC GHAD)

**Chain of official registrar documents (County of Santa Clara ROV):**
1. **CFMR001 Contest/Candidate Proof List**, print 8/7/2026 8:44:32 PM (the "Unofficial List of Local Candidates" PDF, contests 3120–6103; totals verified: Total Contests 133 / Total Candidates Filed 283). Each of the four districts appears with **Num Cands 0 / Num Qualified 0**, Status ON BALLOT at close of initial filing. Contest rows:
   - `6042 Lion's Gate Community Services District` — Vote For 1, 0/0; incumbents Andy Pashby + Kevin Stuart flagged "Appointed to Vacancy".
   - `* 6043 Lion's Gate CSD, Director, Short Term` — Vote For 2, 0/0 (asterisk = office goes into extension); incumbent Julie Sattler "Appointed to Vacancy".
   - `6080 San Martin County Water District` — Vote For 2, 0/0; incumbents line: "Alan J. Bahnsen / Vacant" + "Appointed in Lieu / Vacated".
   - `6103 Silver Creek Valley CCGHAD` — (Vote For 3); incumbents Reyad Katwan "Appointed in Lieu", Paul D Hansen "Appointed in Lieu", James Robert "Elected".
2. **Extended filing closed 8/12/2026** (ROV resources page: nomination period 7/13–8/7, extension to 8/12).
3. **Final Qualified List of Local Eligible Candidates**, file dated 9/28/2026 — titled FINAL; linked from the ROV Nov-3 resources page as THE final qualified list. Extraction verified complete (contests 3120–6099, Grand Total: 287). **Zero rows for all four districts** — absent entirely, not even "On Ballot: No" rows (the list uses those for contests with qualified candidates later removed, e.g. codes 3120/3160/3214 pattern).
4. **CFMR028 Unofficial Write-In Candidate List**, print 9/24/2026 2:32:55 PM (range header "Contests: 1030 to 6103"; Total Contests 100, Total Candidates Filed 0). **None of codes 6042/6043/6080/6103 present.**
5. **CVIG/ballot final printing deadline: August 28, 2026** (ROV resources page notice). With zero qualified candidates and zero write-ins after the 8/12 extension close, these contests cannot appear on printed ballots or in the County Voter Information Guide.
6. ROV district pages (current): Lion's Gate — Sattler/Pashby/Stuart marked holdover/appointed "NEXT ELECTION 2026"; San Martin CWD — Norgard short-term + Vacant, next election 2026; SCVCC GHAD — Katwan/Hansen/Roberts holdovers, next election 2026.
7. Same-district historical practice (registrar incumbent columns + Ballotpedia officeholder pages): zero-filing cycles in these districts produced cancelled elections / winners "without appearing on the ballot" / "Appointed in Lieu".

**Note:** CFMR001 status column reads "ON BALLOT" for ALL contests in that print (it is a filing-stage proof, not a ballot-status determination) — so it establishes zero filings at 8/7, not final status. The FINAL-qualified-list omission + write-in-list omission + 8/28 print deadline form the affirmative chain.

## San Mateo County — CA2026-302 (Bayshore ESD Governing Board, short term) & CA2026-308 (Colma Fire PD Director)

**Chain of official county documents (San Mateo ACRE / Mark Church):**
1. **Candidate Guide scheduled-offices table** (Nov 3, 2026 Candidate Guide, mirrored at burlingame.org/DocumentCenter/View/9330): "Bayshore Elementary School District, Governing Board (Full Term) — 1 [seats up]" / "(Short Term) — **2**" / "Colma Fire Protection District, Board of Directors — 1". Both offices also in the July filing-open news release.
2. **Roster of Candidates CFMR009** ("All Contests / Qualified Candidates Only") printed **7/31, 8/4 and 9/3/2026** (all three PDFs downloaded from smcacre.gov and text-searched). Bayshore appears ONLY as contest 3400 Full Term (Vote for 3; Ferrusca/Rudolph/Camarco qualified). **No Bayshore Short Term row in any print. No Colma Fire row in any print** (only "Town of Colma Member, City Council" 5081 — different jurisdiction). Every other Candidate-Guide-scheduled office appears in the 9/3 roster EXCEPT these two.
3. The 9/3 roster is still the only candidate list on the county's Nov-3 election page (re-checked Oct 14, 2026; page HTML links `52_candidateroster0903.pdf` as "Roster of Candidates").
4. **Extended-filing list updated 8/12/26**: includes Bayshore Full Term and Colma Fire Board of Directors; does NOT include Bayshore Short Term. (Extensions occur when an eligible incumbent doesn't file.)
5. **Sample Ballot & Voter Information Pamphlet mailing began 9/25/2026** (county news release) — ballots already in voters' hands cannot contain a contest with zero qualified candidates.
6. Bayshore ESD website board page: Rudolph, Camarco, Marion Brown each "Term: 2026" (consistent with holdover after cancellation). Colma Fire LAFCO profile: Maryanny Hazard term ending 11/2026; she appears in no county candidate document.
7. Ballotpedia SM-2026 page lists November special-district contests (Coastside FPD D/E, Granada CSD, Coastside CWD Zone 5, BOE Area 2, BOS D5 special) — neither Bayshore ST nor Colma Fire listed.

**Seats discrepancy (CA2026-302):** dataset records seats: 1; county Candidate Guide scheduled-offices table says Short Term = **2** seats up. Board math (5 members; Full Term contest elects the 3 whose terms expire 2026) is ambiguous on short-term count. Candidate Guide is the authoritative scheduled-offices source → candidate for correction to 2.

## Jev adjudication
Cloud endpoint `api.typesafe.ai/v1/systemone` accepted one calibration call at ~05:35 UTC Oct 14, then began returning 403 authentication_error for every subsequent request from this egress IP (likely Cloudflare/WAF throttle after retry burst with a corrupted key string). Retries spaced over 60+ min. Fallback adjudicator if still blocked: local `jevify-gemma4-26b-a4b` on LM Studio, clearly labeled as fallback.

## Disposition recommendation (pre-Jev)
All six contests meet or exceed the Alameda/Contra Costa precedent bar: exhaustive filing-stage proof shows 0 filings; the county's FINAL candidate list omits them while printing removal rows for others; write-in list omits them; ballot print deadline passed with ballots mailed. Recommend **excluded — confirmed not on ballot** for all six, with notes recording that the underlying cancellation/appointment resolution was not published online and how each seat is filled is NOT asserted (same wording discipline as Alameda N889).
