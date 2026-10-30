#!/usr/bin/env python3
"""Owner-ordered v8 rerun (2026-10-30): CJD-as-Zionist-signal + endorsement-only A cap.

Runs the playground RunManager directly against the current dataset with
criteria-pro-palestine-v8 questions over ALL tracked candidacies (same mechanism
as run 20261029T043045Z-42f63b2f for publication 2026-10-28.4), then saves the
/api/bootstrap-equivalent snapshot that scripts/publish_jev_grades.py freezes.
Starts only when LM Studio (192.168.0.66) is otherwise idle. Resumable:
RunManager persists every row; rerunning this driver re-attaches or restarts.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from serve_jev_playground import RunManager  # noqa: E402
from grade_gaza import DATASET  # noqa: E402

KEY_FILE = "/root/.cfg/typesafe_key"
CRITERIA = ROOT / "research/gaza-grading/criteria-pro-palestine-v8.json"
WORK = ROOT / ".research/jev-playground-v8"
OUT = ROOT / ".research/jev-playground-v8/bootstrap-v8.json"
LMS = "http://192.168.0.66:11434"


def wait_idle():
    # Jev calls go to the TypeSafe API, not LM Studio; no wait required.
    return


def main():
    key = Path(KEY_FILE).read_text().strip()
    manager = RunManager(dataset_path=DATASET, work=WORK, key=key, workers=3)
    questions = json.loads(CRITERIA.read_text())["questions"]
    run_id = None
    for path in sorted((WORK / "runs").glob("*/run.json")):
        run = json.loads(path.read_text())
        if run["questions"] == questions and len(run["rows"]) > 1000:
            run_id = run["id"]
    if run_id and manager.get(run_id)["status"] == "complete":
        run = manager.get(run_id)
    elif run_id and manager.get(run_id)["status"] in {"running", "cancelling"}:
        run = manager.get(run_id)
        print("monitoring existing run", run_id, flush=True)
    else:
        wait_idle()
        run = manager.start(questions, scope="all")
        run_id = run["id"]
        print("started run", run_id, flush=True)
    while True:
        current = manager.get(run_id)
        print(f"{current['status']} {current['completed']}/{len(current['rows'])} errors={current['errors']}", flush=True)
        if current["status"] not in {"running", "cancelling"}:
            break
        time.sleep(30)
    if current["status"] != "complete" or current["errors"]:
        print("RUN NOT CLEAN:", current["status"], "errors", current["errors"], flush=True)
        sys.exit(1)
    # bootstrap-equivalent snapshot for publish_jev_grades --snapshot
    boot = manager.bootstrap()
    OUT.write_text(json.dumps(boot))
    print("bootstrap snapshot saved:", OUT, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
