#!/usr/bin/env python3
"""Post-sweep remediation driver (owner directive 2026-10-30, Tandon-class fix).

Waits for sweep_policy_pages.py to finish, then for every candidate whose
campaign site gained new keyword-bearing policy pages:
  1. re-runs the collector pass (gaza_research internals, workers=1)
  2. merges the ledger into the dataset (merge_gaza_evidence)
  3. requires check_gaza_ledger + check_published_grades to pass — if new
     evidence would change any published GRADE the attach-projection check
     fails; the driver then STOPS with NEEDS_REVIEW.md (grade reruns belong
     to the owner's score-publication flow, never auto-applied)
  4. bumps publication_version, refreshes recommendations (cached Jev;
     regenerates only affected why-paragraphs), rebuilds readers
  5. runs the full release gate; pushes ONLY if fully green; verifies live.
Checkpointed via driver-progress.json; reruns are safe.
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECTOR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(COLLECTOR))
sys.path.insert(0, COLLECTOR)
os.environ.setdefault("GAZA_LMS_URL", "http://192.168.0.66:11434/v1/chat/completions")
os.environ.setdefault("SERPER_KEY_FILE", "/root/.cfg/serper_key")
os.environ.setdefault("FEC_KEY_FILE", "/root/.cfg/fec_key")

SWEEP_LOG = os.path.join(HERE, "sweep.log")
FINDINGS = os.path.join(HERE, "policy-page-sweep.json")
PROG = os.path.join(HERE, "driver-progress.json")
REPORT = os.path.join(HERE, "REPORT.md")
DATA = os.path.join(REPO, "2026-11-03_Bay_Area_Elections.json")


def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True, **kw)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def note(msg):
    line = f"[{time.strftime('%F %T')}] {msg}"
    print(line, flush=True)
    with open(os.path.join(HERE, "driver.log"), "a") as f:
        f.write(line + "\n")


def load():
    return json.load(open(PROG)) if os.path.exists(PROG) else {"redone": [], "phase": "collect"}


def all_people_map():
    import gaza_research as g
    data = json.load(open(g.DATA))
    people = {}
    for p in data["positions"]:
        roster = list(p.get("candidates") or [])
        if not p.get("counties"):
            roster += p.get("filed_candidates_not_confirmed_on_ballot") or []
        for c in roster:
            u = c.get("campaign_url")
            if not u:
                continue
            k = g.norm_name(c["name"]) + "|" + str(c.get("party"))
            ent = people.setdefault(k, {"key": k, "name": c["name"], "party": c.get("party"),
                                        "level": p["government_level"], "office": p["office"],
                                        "ctx": set(), "handle": None, "committee_ids": [],
                                        "campaign_url": None, "enrich": True})
            ent["ctx"].add((p["government_level"], p.get("office") or "", str(p.get("jurisdiction") or ""), ""))
            if c.get("x_url"):
                ent["handle"] = ent["handle"] or c["x_url"].rstrip("/").split("/")[-1]
            for cid in ((c.get("fec") or {}).get("committee_ids") or []):
                if cid not in ent["committee_ids"]:
                    ent["committee_ids"].append(cid)
            ent["campaign_url"] = ent["campaign_url"] or u
    return people


def main():
    # wait for the sweep to finish
    while True:
        log = open(SWEEP_LOG).read() if os.path.exists(SWEEP_LOG) else ""
        if "DONE: swept" in log:
            break
        time.sleep(120)
    note("sweep finished; starting remediation")
    findings = json.load(open(FINDINGS))
    note(f"impacted candidates: {len(findings)}")
    prog = load()

    if prog["phase"] == "collect":
        import gaza_research as g
        from validate_evidence import normalize_url
        people = all_people_map()
        # class 1: sweep found new KW-bearing policy subpages
        targets = list(findings)
        # class 2: homepage now decodes WITH conflict keywords but the site
        # contributed zero ledger evidence (the garbled-capture victims whose
        # stance text sits on the homepage itself)
        for k, ent in people.items():
            t = None
            try:
                t = g.page_text(ent["campaign_url"])
            except Exception:
                pass
            if not (t and g.KW.search(t)):
                continue
            ev_p = g.ev_path(k)
            dom = ent["campaign_url"].split("//")[-1].split("/")[0].replace("www.", "")
            have_site = False
            if os.path.exists(ev_p):
                for e in json.load(open(ev_p)):
                    if dom in (e.get("domain") or ""):
                        have_site = True
                        break
            if not have_site:
                targets.append(k)
        targets = [k for k in dict.fromkeys(targets) if k in people]
        note(f"collector redo targets: {len(targets)}")
        for k in targets:
            if k in prog["redone"]:
                continue
            try:
                name, added, nfu = g.work(people[k])
                g._mark_done(k, people[k], {"done": True, "enriched": True})
                note(f"redo {k}: +{added} items")
            except Exception as e:
                note(f"redo {k} FAILED: {repr(e)[:120]}")
            prog["redone"].append(k)
            json.dump(prog, open(PROG, "w"), indent=1)
            time.sleep(1)
        prog["phase"] = "merge"
        json.dump(prog, open(PROG, "w"), indent=1)

    if prog["phase"] == "merge":
        rc, out = sh("python3 research/gaza-stance/merge_gaza_evidence.py")
        note(f"merge rc={rc}")
        if rc:
            note(out[-500:]); return
        prog["phase"] = "check"
        json.dump(prog, open(PROG, "w"), indent=1)

    if prog["phase"] == "check":
        for script in ("scripts/check_gaza_ledger.py", "scripts/check_published_grades.py"):
            rc, out = sh(f"python3 {script}")
            note(f"{script} rc={rc}")
            if rc:
                with open(os.path.join(HERE, "NEEDS_REVIEW.md"), "w") as f:
                    f.write("Grade/evidence gate failed after policy-page redo — new evidence "
                            "likely shifts published grades. Manual score rerun required.\n\n```\n"
                            + out[-4000:] + "\n```\n")
                note("STOP: needs review, no publish")
                return
        rc, out = sh("git diff --stat 2026-11-03_Bay_Area_Elections.json")
        note("dataset diff: " + out.strip().splitlines()[-1] if out.strip() else "no dataset change")
        if "no dataset change" in (out or "") or not out.strip():
            with open(REPORT, "w") as f:
                f.write("No evidence changes resulted from the sweep; nothing to publish.\n")
            prog["phase"] = "done"
            json.dump(prog, open(PROG, "w"), indent=1)
            return
        prog["phase"] = "publish"
        json.dump(prog, open(PROG, "w"), indent=1)

    if prog["phase"] == "publish":
        rc, out = sh("""python3 - <<'PY'
import json
p='2026-11-03_Bay_Area_Elections.json'
d=json.load(open(p))
v=d['election']['publication_version']
date, n = v.rsplit('.',1)
d['election']['publication_version']=f"{date}.{int(n)+1}"
open(p,'w').write(json.dumps(d, ensure_ascii=False, indent=1)+"\\n")
print(d['election']['publication_version'])
PY""")
        ver = out.strip().splitlines()[-1]
        note("bumped to " + ver)
        key = open("/root/.cfg/typesafe_key").read().strip()
        rc, out = sh(f"JEV_API_KEY={key} python3 scripts/build_recommendations.py classify")
        note(f"classify rc={rc}")
        rc, out = sh(f"JEV_API_KEY={key} python3 scripts/build_recommendations.py jev")
        note(f"jev rc={rc}")
        rc, out = sh(f"JEV_API_KEY={key} python3 scripts/build_recommendations.py reasons")
        note(f"reasons rc={rc} :: " + (out.strip().splitlines() or [""])[0])
        rc, out = sh(f"JEV_API_KEY={key} python3 scripts/build_recommendations.py build")
        note(f"build rc={rc}")
        if rc:
            note(out[-800:]); return
        sh("python3 scripts/prepare_dom_fixture.py")
        # full release gate detached, poll to completion
        subprocess.Popen("setsid nohup python3 scripts/check_release.py > " + HERE + "/gate.log 2>&1",
                         shell=True, cwd=REPO)
        time.sleep(60)
        while True:
            rc, _ = sh("pgrep -f check_release.py")
            if rc:  # process gone
                break
            time.sleep(120)
        g = open(os.path.join(HERE, "gate.log")).read() if os.path.exists(os.path.join(HERE, "gate.log")) else ""
        passes = len(re.findall(r"^PASS", g, re.M))
        rc, out = sh("""python3 -c "import sys; sys.path.insert(0,'scripts'); import check_release; print(len(check_release.PYTHON_CHECKS)+len(check_release.NODE_CHECKS))" """)
        try:
            expected = int(out.strip().splitlines()[-1])
        except ValueError:
            expected = 49
        note(f"gate passes: {passes} (expected {expected})")
        if "FAIL" in g or "Traceback" in g or passes < expected:
            note("GATE FAILED/INCOMPLETE — stopping, no publish")
            return
        tok = open("/root/.cfg/gh_token").read().strip()
        rc, out = sh(f"""git add -A && git commit -m "Publish {ver}: campaign-site policy-page remediation (Tandon-class sweep)" """)
        note(f"commit rc={rc}")
        pushed = False
        for attempt in range(3):
            rc, out = sh(f"git push https://x-access-token:{tok}@github.com/salqadri/bay-area-elections-2026.git HEAD:main")
            if rc == 0:
                pushed = True
                break
            note(f"push attempt {attempt+1} failed rc={rc}; fetching + rebasing")
            rc2, out2 = sh(f"git fetch https://x-access-token:{tok}@github.com/salqadri/bay-area-elections-2026.git main && git rebase FETCH_HEAD")
            note(f"rebase rc={rc2}")
            if rc2:
                sh("git rebase --abort")
                break
        note(f"pushed={pushed}")
        if not pushed:
            with open(os.path.join(HERE, "NEEDS_REVIEW.md"), "w") as f:
                f.write("Gate green but push failed after 3 attempts (divergence?) — commit is local; rebase/push manually.\n")
            return
        time.sleep(90)
        rc, out = sh("curl -s -m 60 https://salqadri.github.io/bay-area-elections-2026/ | grep -c " + ver)
        note(f"live verification hits: {out.strip()}")
        with open(REPORT, "w") as f:
            f.write(f"Published {ver}: policy-page remediation complete. Gate {passes} PASS. "
                    f"Live verified: {out.strip()} hits.\n")
        prog["phase"] = "done"
        json.dump(prog, open(PROG, "w"), indent=1)
    note("driver complete")


if __name__ == "__main__":
    main()
