#!/bin/sh
# Full campaign-site endorsement scan: crawl all pending sites, then run the
# bounded model extraction pass. Resumable; safe to re-run after interruption.
cd "$(dirname "$0")/.." || exit 1
echo "== crawl $(date -Is)"
python3 scripts/campaign_endorsements.py crawl --workers 4 --limit 500
echo "== extract-llm $(date -Is)"
while :; do
  out=$(python3 scripts/campaign_endorsements.py extract-llm --workers 2 --limit 100)
  echo "$out"
  echo "$out" | grep -q '"processed": 0' && break
done
echo "== done $(date -Is)"
