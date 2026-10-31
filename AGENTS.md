# Continuing PR #22

When working on PR #22, read [docs/PR22_HANDOFF.md](docs/PR22_HANDOFF.md) first.
It identifies the latest saved owner prompt, thresholds, portable evaluation
history and commands to restore the Jev playground in a fresh checkout.

Working defaults and held review results differ from the older frozen public
publication. Preserve exact archived request/response hashes and their prompts;
do not relabel old results as evaluations of a new prompt. Do not merge,
publish or start model batches merely to resume review; follow the user's scope.

Keep API keys and ignored `.research` histories out of commits. Only explicitly
selected, credential-free review snapshots belong under `research/`. Use
Serper.dev for any web searches. The separate local-only TALL Firebase guide
does not belong in this repo.
