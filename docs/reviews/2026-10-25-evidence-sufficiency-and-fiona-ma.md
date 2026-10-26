# Evidence sufficiency and Fiona Ma divestment gap

## Display correction

Charles A. Smiley's latest saved state is identity-only. Jev returned
`evidence_score: 0.0 / 1` but a `pro_palestine_score` of 1.77 / 5; the previous
mapping blindly converted that to D. The derived grade now shows **Insufficient
Info** whenever the exact saved two-criterion `evidence_score` is below 0.10.
At inspection, this covered 807 of the 1,042 latest evaluations, including Fiona
Ma (0.05 / 1). Counts describe saved inputs, not current research completeness.
No saved request, provider answer, confidence or run file is rewritten; no new
candidate grading calls were made. The threshold is on evidence, not confidence.

## Why Fiona Ma was missed

Her canonical record had neither `gaza_evidence` nor a reviewed Gaza campaign
statement. The compact-state builder therefore had no such evidence to include;
this was not truncation of a populated dossier. Historical collector artifacts:

- `research/gaza-stance/sf_run.log` records a web timeout for Fiona Ma and zero items.
- `sf_run2.log` and `sf_enrich.log` record zero items with three follow-ups each.
- `ledger/state.json` nevertheless marks her done/enriched on October 8.

These logs do not preserve enough detail to prove that a particular query caused
an individual source to be missed. The legacy fixed/enrichment templates have no
dedicated divestment search. The newer gap collector included divestment only in
an overconstrained query with jurisdiction, Gaza, ceasefire and resolution, and
its result filter did not accept divestment/BDS-only snippets. Discovery now
separates those queries and recognizes those terms. Its version enters the plan
fingerprint so changed discovery is distinguishable. This improves future bounded
research; it is not a claim that all candidates have been refreshed.

## Recovered evidence

A name + Israel + divestment search through Serper immediately located
[POLITICO's May 16, 2024 interview](https://www.politico.com/newsletters/california-playbook/2024/05/16/on-the-record-with-fiona-ma-00158305).
It identifies the California treasurer and 2026 lieutenant governor candidacy,
and explicitly attributes opposition to divestment from Israel to Ma in response
to UC student demands. The original HTML contains a May 16 publication timestamp.
Direct retrieval returned HTTP 403; Serper's scrape API returned the full public
HTML, which was captured and hashed. Exact excerpts, publication date and
candidate identity passed actual Jev source review in the immutable
`fiona-divestment-2026-10-25` review/audit. This is a historical statement, not an
assertion of her current position or a replacement for CAIR Action's preference.

The registered review adds one dated canonical evidence item, synchronizes it to
the research ledger, updates coverage and rebuilds both readers. Reapplying the
review is a no-op. The new evidence enters Fiona Ma's next generated state. Her
previous evaluation continues to show exactly the old submitted input; rerunning
her with the desired questions is required to obtain a new Jev answer.
