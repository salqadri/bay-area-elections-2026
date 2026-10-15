#!/bin/bash
# Enrich depth passes for the four new counties (SF already enriched; person-keyed skip).
# Sequential county --enrich passes -> merge -> rebuild -> full check suite.
# Resumable: ledger/state.json stages.enriched marks finished people.
set -u
cd "$(dirname "$0")"
LOG=enrich_run.log
say(){ echo "[orch $(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

for C in "Alameda" "Contra Costa" "San Mateo" "Santa Clara"; do
  say "=== enrich pass: $C ==="
  python3 gaza_research.py --county "$C" --enrich --workers 2 >>"$LOG" 2>&1
  RC=$?
  say "county $C exited rc=$RC"
  N=$(grep -c "LMS extraction unavailable" "$LOG")
  if [ "$N" -ge 20 ]; then say "FATAL: $N LMS extraction failures — stopping; resume with same command"; exit 1; fi
done

say "=== collection complete — NOT merging automatically (manual identity audit required first) ==="
say "ENRICH COLLECTION DONE — awaiting revalidate + manual review, then Hermes merges/pushes"
