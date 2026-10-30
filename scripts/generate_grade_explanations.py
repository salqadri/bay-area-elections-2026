#!/usr/bin/env python3
"""Generate voter explanations for the frozen v7 score publication.

Sub-agent: qwen/qwen3.8-27b on the owner's LM Studio (concurrency 2, medium
reasoning). Each letter-grade candidacy is explained from its exact archived
scoring request, rubric answers and displayed grade under the hash-bound
summary-prompt-v4.txt. Responses bind candidate_id + request_sha256 for
scripts/attach_grade_explanations.py. N/A candidacies need no model call: the
attacher writes the editorial insufficiency note. Resumable: an existing
response is reused only when its complete generation hash and source policy match.

Usage:
  python3 scripts/generate_grade_explanations.py            # all missing
  python3 scripts/generate_grade_explanations.py --limit 5  # smoke batch
"""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from score_grade import row_grade  # noqa: E402
from summary_source_policy import policy_for_state, prose_errors  # noqa: E402

QUEUE = ROOT / "research/gaza-grading/explanation-queue-2026-10-28-latest.json"
PROMPT_PATH = ROOT / "research/gaza-grading/summary-prompt-v4.txt"
LMSTUDIO_URL = "http://192.168.0.66:11434/v1/chat/completions"
LMSTUDIO_MODEL = "qwen/qwen3.8-27b"
REASONING = "medium"
MAX_TOKENS = 12000
CONCURRENCY = 2
# The identity block is context, not evidence: the audit still gets one row per
# field, but the prose rules operate on the substantive fields.
BATCH = 4


def evidence_inventory(state):
    """One inventory ID per top-level candidate_record field."""
    return [f"candidate_record.{k}" for k in state]


def summary_inventory(row, current_state=None):
    inventory = evidence_inventory(row['request']['state'])
    if current_state is not None:
        inventory += ['supplemental_reference.current_research_additions.' + key
                      for key,value in current_state.items() if value != row['request']['state'].get(key)]
    return inventory


def build_input(row, grade, prompt_text, current_state=None):
    payload = {
        "format": "grade-summary-current-research-input/v2",
        "candidate_id": row["id"],
        "candidate": row["candidate"],
        "associated_score_request_sha256": row["request_sha256"],
        "candidate_record": row["request"]["state"],
        "scoring_questions": row["request"]["questions"],
        "recorded_response": row["response"],
        "displayed_grade": grade,
        "evidence_inventory": summary_inventory(row, current_state),
        "summary_source_policy": policy_for_state(current_state or row['request']['state'], row.get('position_id')),
        "note": ("Generate the voter explanation for this saved grade. Return ONLY one JSON object with keys "
                 "candidate_id, request_sha256, evidence_audit, summary. Set candidate_id to the exact candidate_id "
                 "and request_sha256 to the exact associated_score_request_sha256 shown above. evidence_audit has "
                 "exactly one row per evidence_inventory id. Never mention the evidence_audit in the summary."),
    }
    if current_state is not None:
        additions = {key: value for key, value in current_state.items()
                     if value != row['request']['state'].get(key)}
        if additions:
            payload['supplemental_reference'] = {'current_research_additions': additions,
                'note': 'Current source research added since the saved score; explanation context only, not a new evaluation.'}
    return prompt_text + "\n\nSUPPLIED RECORD\n" + json.dumps(payload, ensure_ascii=False)


def call_lmstudio(prompt, sha_to_id=None, max_tries=3):
    """Generate with echo repair: a single flubbed hex character in the
    candidate_id echo is normalized when the request_sha256 echo is exact and
    maps to exactly this row (the sha is the strong binding)."""
    last_err = None
    for _ in range(max_tries):
        raw = _call_lmstudio_once(prompt)
        try:
            result = parse_json(raw)
        except ValueError as e:
            last_err = e
            continue
        echo = str(result.get("candidate_id") or "")
        sha = str(result.get("request_sha256") or "")
        if echo != "" and sha_to_id and sha in sha_to_id and sha_to_id[sha] and echo != sha_to_id[sha]:
            canonical = sha_to_id[sha]
            if len(echo) >= 20 and echo in _subslices(canonical):
                print(f"  [echo-repair] candidate_id {echo} -> {canonical} (sha exact)", flush=True)
                result["candidate_id"] = canonical
        return result
    raise RuntimeError(f"unparseable model output: {last_err}")


def _subslices(s):
    """All strings within edit distance 2 by single char deletion of s."""
    out = {s, ""}
    for i in range(len(s)):
        out.add(s[:i] + s[i + 1:])
    for i in range(len(s)):
        for j in range(i, len(s)):
            out.add(s[:i] + s[j + 1:])
    return out


def _call_lmstudio_once(prompt):
    body = json.dumps({"model": LMSTUDIO_MODEL, "reasoning_effort": REASONING,
                       "max_tokens": MAX_TOKENS,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(LMSTUDIO_URL, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                d = json.load(resp)
            m = d["choices"][0]["message"]
            text = (m.get("content") or "").strip()
            if not text:
                raise RuntimeError("empty content")
            return text
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"LM Studio call failed: {last}")


def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in model output")
    return json.loads(t[start:end + 1])


def validate(result, row, grade, source_policy=None, inventory=None):
    if result.get("request_sha256") != row["request_sha256"]:
        return "request_sha256 echo mismatch"
    # request_sha256 is the strong binding (64 hex chars, verified exact); the
    # 24-char candidate id occasionally loses a character in model echoes.
    if result.get("candidate_id") != row["id"]:
        return "candidate_id echo mismatch"
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return "missing summary"
    violations = prose_errors(summary, source_policy or policy_for_state(row.get('request', {}).get('state', {}), row.get('position_id')))
    if violations:
        return '; '.join(violations)
    words = len(summary.split())
    if not 5 <= words <= 130:
        return f"summary {words} words outside 5-130"
    if "\n" in summary.strip() or "**" in summary or re.search(r"^\s*#", summary, re.M):
        return "markdown or multiline summary"
    if grade != "N/A" and re.search(
            r"supplied record|provided record|available record|single data point|too thin|"
            r"record is (?:limited|sparse|thin)|assessment rests|full stance|"
            r"no other (?:statements|votes|endorsements|actions)", summary, re.I):
        return "missing-record disclaimer padding"
    ids = set(inventory if inventory is not None else evidence_inventory(row["request"]["state"]))
    audit = result.get("evidence_audit")
    if not isinstance(audit, list):
        return "evidence_audit missing"
    if not audit:
        return "evidence_audit empty"
    observed = [entry.get('id') for entry in audit if isinstance(entry, dict)]
    if len(observed) != len(audit) or len(observed) != len(set(observed)) or set(observed) != ids:
        return "evidence_audit does not cover the complete archived and supplemental inventory"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    queue = json.loads(QUEUE.read_text())
    publication_id = queue["publication_id"]
    archive = json.loads((ROOT / queue["archive_path"]).read_text())
    assert archive["id"] == publication_id
    mapping = archive["score_grade_mapping"]
    rows = {r["id"]: r for r in archive["rows"]}
    prompt_text = PROMPT_PATH.read_text()
    outdir = ROOT / "research/gaza-grading/responses-summary-v4"
    outdir.mkdir(parents=True, exist_ok=True)

    from grade_gaza import build_state
    current = json.loads((ROOT / '2026-11-03_Bay_Area_Elections.json').read_text())
    current_people = {c.get('pro_palestine_evaluation', {}).get('candidate_id'): (p, c)
        for p in current['positions'] for roster in ('candidates','filed_candidates_not_confirmed_on_ballot','qualified_write_in_candidates')
        for c in p.get(roster) or [] if c.get('pro_palestine_evaluation')}
    todo = []
    for item in queue["candidates"]:
        row = rows[item["id"]]
        grade = row_grade(row, mapping) or "N/A"
        if grade == "N/A":
            continue  # editorial note at attach time; no model call
        path = outdir / (item["id"] + ".json")
        person = current_people.get(row['id'])
        state = build_state(*person, current) if person else row['request']['state']
        prompt = build_input(row, grade, prompt_text, state)
        generation_hash = hashlib.sha256(prompt.encode()).hexdigest()
        source_policy = policy_for_state(state, row.get('position_id'))
        inventory = summary_inventory(row, state)
        if path.exists():
            cached = json.loads(path.read_text())
            if cached.get('generation_sha256') == generation_hash and not validate(cached, row, grade, source_policy, inventory):
                continue
        todo.append((item, row, grade, prompt, generation_hash, source_policy, inventory))
    if args.limit:
        todo = todo[:args.limit]
    print(f"Explanations: {len(todo)} letter-grade candidacies to generate", flush=True)

    def work(job):
        item, row, grade, prompt, generation_hash, source_policy, inventory = job
        sha_to_id = {row["request_sha256"]: row["id"]}
        result = call_lmstudio(prompt, sha_to_id=sha_to_id)
        err = validate(result, row, grade, source_policy, inventory)
        if err:
            raise ValueError(err)
        final = {"candidate_id": row["id"], "request_sha256": row["request_sha256"],
                 "publication_id": publication_id, "model": LMSTUDIO_MODEL,
                 "summary": result["summary"].strip(),
                 "evidence_audit": result["evidence_audit"],
                 "generation_sha256": generation_hash,
                 "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest(),
                 "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        return item, row, grade, final

    done = failed = 0
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
            futs = {ex.submit(work, j): j for j in batch}
            for fut in as_completed(futs):
                item, row, grade, *_ = futs[fut]
                try:
                    _, _, _, final = fut.result()
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    print(f"  [FAILED] {row['candidate']} ({item['id']}): {e}", flush=True)
                    continue
                (outdir / (item["id"] + ".json")).write_text(
                    json.dumps(final, ensure_ascii=False, indent=1) + "\n")
                done += 1
                print(f"  [{done + failed}/{len(todo)}] {grade} {row['candidate']} "
                      f"({row['position_id']}) -> {len(final['summary'].split())} words", flush=True)
    print(f"Generated {done}, failed {failed}. Remaining letter grades without a response: "
          f"~{len(todo) - done - failed if not args.limit else 'n/a (limited run)'}", flush=True)


if __name__ == "__main__":
    main()
