#!/bin/bash
# Overnight four-county Gaza evidence run (Alameda, Contra Costa, San Mateo, Santa Clara).
# Sequential county passes -> merge -> rebuild -> full check suite -> commit -> push.
# Resumable: gaza_research.py skips people already marked done in ledger/state.json.
set -u
cd "$(dirname "$0")"
LOG=county_run.log
say(){ echo "[orch $(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

for C in "Alameda" "Contra Costa" "San Mateo" "Santa Clara"; do
  say "=== county pass: $C ==="
  python3 gaza_research.py --county "$C" --workers 2 >>"$LOG" 2>&1
  RC=$?
  say "county $C exited rc=$RC"
  # abort early only on a sustained LMS outage (transient failures stay pending for resume)
  N=$(grep -c "LMS extraction unavailable" "$LOG")
  if [ "$N" -ge 20 ]; then say "FATAL: $N LMS extraction failures — stopping for resume later"; exit 1; fi
done

say "=== merge into dataset ==="
python3 merge_gaza_evidence.py >>"$LOG" 2>&1 || { say "FATAL: merge failed"; exit 1; }

say "=== rebuild site ==="
cd ../..
python3 scripts/build_site.py >>"$LOG" 2>&1 || { say "FATAL: build failed"; exit 1; }

say "=== full check suite ==="
{ python3 scripts/build_site.py --check \
  && python3 scripts/check_data.py \
  && python3 scripts/check_schema.py \
  && python3 scripts/prepare_dom_fixture.py \
  && node scripts/check_explorer.cjs \
  && node scripts/check_address_services.cjs \
  && node scripts/check_address_suggestions.cjs \
  && node scripts/check_address_autocomplete.cjs \
  && node scripts/check_address_matcher.cjs \
  && node scripts/check_ballot_page.cjs; } >>"$LOG" 2>&1
RC=$?
say "check suite rc=$RC"
[ "$RC" -eq 0 ] || { say "FATAL: checks failed — NOT pushing"; exit 1; }

say "ORCHESTRATOR DONE — collection, merge, build and checks complete; awaiting doc update + push"
