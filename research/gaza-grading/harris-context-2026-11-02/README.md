# Harris Mojadedi narrative refresh — November 2, 2026

Held for PR #22 review; no production deployment or scoring run.

- `candidate-explanation.json`: refreshed factual candidate context, bound to his existing score request. The grade field is cache metadata, not a new evaluation.
- `race-context.json`: refreshed context for CA2026-120, preserving the publisher's **No recommendation** setting. This is not a model-selected recommendation.
- `source-payload.json`: exact factual input snapshot. Identity flags are omitted from narrative generation and no identity-based policy inference is made.
- `generation-calls/`: exact Qwen requests and responses, with evidence inventories and token usage. Model `qwen/qwen3.8-27b`, medium reasoning, temperature 1; two concurrent calls. Final text was edited for concise wording and attribution; original generated text remains in each output as well as the raw responses.

The source report records owner-reported Muslim American Alliance opposition
without a public source URL. The separate February 2024 Bay Area Reporter article
documents criticism of LGBTQ-related guide criteria; it does not confirm that
opposition, its cause or a Gaza position. CAIR Action's endorsement and Vote for
Peace's Ally rating are preserved without turning them into personal statements.

`scripts/publisher_review_context.py` binds these narratives to the current
candidate factual states, community source report and publisher disposition.
A changed source hash prevents stale race context from replacing the generic
publisher hold text. The optional narrative path is excluded from the hash to
avoid self-reference. The portable review manifest includes both output hashes.
No old Jev requests, answers, questions, scores, thresholds or source evidence
were rewritten. The research readers and local TALL comparison are rebuilt;
production remains unchanged.

Validation: 20 recommendation regression tests pass, including source-change
invalidation, unchanged candidate data and preservation of No recommendation.
Chrome checks pass at desktop and 390px phone widths for both the candidate
page and expanded production comparison; no page errors or horizontal overflow.
The comparison counts remain 123 publisher picks, six changed picks and 37
candidate letter changes versus production. Credential scan passes.
Full offline release gate: **53/53 checks pass**.
