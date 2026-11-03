# Legislative summary consistency — November 2, 2026

The owner identified a real reversal in the held Aisha Wahab race paragraph: voting **No** on defunding universities that boycott Israel was described as cutting the other way, even though the source tracker explicitly marks that response **aligned**.

The candidate writer received the exact response and alignment. Its candidate paragraph stated the vote correctly. The race writer instead received a shortened candidate narrative, without the legislative alignment channel. It introduced the erroneous negative interpretation. Source hashes, word counts and endorser-name checks did not check the meaning of that interpretation.

## Corrections held for review

- **Aisha Wahab / CA2026-003:** remove the contrary-item framing and state that she opposed defunding universities that boycott Israel. Retain the separate AB 715 abstention as a fact, without incorrectly grouping the two actions as adverse.
- **Ro Khanna / CA2026-004:** replace “his one contrary vote” with the specific January 2026 vote and his explanation, retaining the later February No. The tracker contains multiple other not-aligned votes, so the exclusive claim was incorrect.

The before/after files retain the original model output and a separate factual editorial correction, with exact text hashes and unchanged candidate evaluation bindings. These are held review outputs used by the local preview; scores and production have not changed.

## Audit scope and limits

The source inventory screened 2,023 paragraph occurrences, including duplicates and N/A notes. Jev audited **249 distinct paragraphs** with legislative mentions and matching legislative context. It initially flagged 21 contradictions and 18 uncertain cases; a sentence-level follow-up and source review did **not** substantiate most of those flags. Different dated votes and non-legislative endorsement claims are not vote-direction contradictions. A deterministic check of exclusive contrary-vote claims caught the Khanna error missed by that follow-up.

**Two errors are confirmed and corrected; this is not a claim that every other sentence is verified.** The audit concerns legislative responses and explicit tracker alignment, not all historical facts, campaign-finance claims, source accuracy or political judgments. No confidence acceptance cutoff was applied. Exact API audit requests/responses remain cached locally; audit.json retains the reviewed identities, paragraph hashes and provider decisions. No candidate was rescored.

## Systematic fix

The race writer now receives the same compact source-evidence projection as Jev, including every dated legislative response with its alignment and qualifications. It no longer uses a shortened LLM candidate summary as the evidence base, and does not clip the candidate evidence to eight records or the opponent evidence to six lines. The prompt explicitly distinguishes an aligned No, a Yes on an adverse bill, neutral/non-votes, sponsorship and future intentions.

The saved old prompts and answers remain immutable. New requests use the new prompt hash. `check_recommendations.py` asserts that the real Aisha record passes No + aligned through to the race prompt. `scripts/audit_summary_alignment.py` is reusable for screening newly generated summaries; its flags require source review and never edit scores or prose automatically.
