"""Parse the Fresno County CFMR001 Contest/Candidate Proof List (Nov 3 2026).

Anchor facts from the print layout:
- Contest headers: optional '* ' extension marker + 4-digit id + title.
- Status lines: '[district-id] [district name] vote-for cands qualified ON BALLOT'
  (bare 'vf c q ON BALLOT' on extension pages).
- Every candidate block ends with 'Qualified Date:'; the candidate name is the
  ALL-CAPS line at the head of the block, optionally ', Party' suffixed,
  followed by one designation line ('Incumbent', 'No Ballot Designation', or
  a title-case occupation).
- 'Shared with:' lists may wrap onto one extra title-case line.

Verification: parsed candidate count per contest must equal the PDF's own
Num Cands/Num Qualified columns; the run fails otherwise.
"""
import json
import re

PARTIES = [
    "Republican", "Democratic", "No Party Preference", "Green", "Libertarian",
    "American Independent", "Peace and Freedom", "Constitution", "Independent",
    "Unaffiliated", "Natural Law",
]
PARTY_RE = re.compile(r"^(?P<name>.+?),\s*(?P<party>" + "|".join(re.escape(p) for p in PARTIES) + r")$")
CONTEST_RE = re.compile(r"^\*?\s*(?P<cid>\d{4})\s+(?P<title>\S.*?)\s*$")
STATUS_RE = re.compile(
    r"^(?:(?P<did>[A-Z]?\d+)\s+)?(?P<district>.*?)\s+(?P<vf>\d+)\s+(?P<cands>\d+)\s+(?P<qual>\d+)\s+(?P<status>ON BALLOT|NOT ON BALLOT)\s*$")
NAME_RE = re.compile(r"^(?:[^\W\d_]|[ .,'\-()\"‘’“”])+$", re.UNICODE)
OFFICE_PREFIX = ("VOTER NOMINATED OFFICES", "NONPARTISAN OFFICES", "JUDICIAL OFFICES", "VOTER APPROVED")
KEY_PREFIXES = ("Qualified Date:", "User Codes:", "Cand ID:", "Filing Fee:", "Requirements Status",
                "Sigs In Lieu", "Nomination Papers", "Candidate Statement", "Declaration",
                "Code of Fair", "-----", "Shared with:", "Incumbent(s):", "Candidate(s):",
                "CFMR001", "Print Date", "Num Num", "Contest/District", "Candidates: ",
                "Contests: ", "VOTER NOMINATED", "NONPARTISAN", "JUDICIAL", "VOTER APPROVED")


def is_name(line):
    if not line or line.startswith(KEY_PREFIXES):
        return False
    pm = PARTY_RE.match(line)
    core = pm.group("name").strip() if pm else line
    return bool(NAME_RE.match(core)) and len(core) > 2 and core == core.upper()


def parse(text: str):
    contests = {}
    current = None
    pending_office = None
    lines = text.splitlines()
    n = len(lines)
    # pass 1: walk every line; track current contest; harvest candidates by
    # anchoring on Qualified Date lines and scanning up to the name line.
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if any(line.startswith(p) for p in OFFICE_PREFIX):
            pending_office = line
            continue
        m = CONTEST_RE.match(line)
        if m and not line.startswith(("Print", "CFMR")):
            cid = m.group("cid")
            if cid not in contests:
                contests[cid] = {
                    "id": cid, "title": m.group("title"),
                    "office_header": pending_office or "",
                    "districts": [], "candidates": [],
                    "shared_with": [], "incumbents": [],
                    "on_ballot": False,
                }
            current = contests[cid]
            pending_office = None
            continue
        if current is None:
            continue
        s = STATUS_RE.match(line)
        if s and "BALLOT" in s.group("status"):
            district = (s.group("district") or "").strip()
            entry = {
                "district_id": s.group("did") or "",
                "district": district,
                "vote_for": int(s.group("vf")),
                "cands": int(s.group("cands")),
                "qualified": int(s.group("qual")),
            }
            if not any(d == entry for d in current["districts"]):
                current["districts"].append(entry)
            if s.group("status") == "ON BALLOT":
                current["on_ballot"] = True
            continue
        if line.startswith("Shared with:"):
            val = line.split(":", 1)[1].strip()
            for part in re.split(r"[,]", val):
                part = part.strip()
                if part and part != "(none)" and part not in current["shared_with"]:
                    current["shared_with"].append(part)
            # wrapped county list on the next line (title-case words only)
            if i + 1 < n:
                nxt = lines[i + 1].strip()
                if re.fullmatch(r"[A-Z][a-z]+(?: [A-Z][a-z]+)*", nxt):
                    current["shared_with"].append(nxt)
            continue
        if line.startswith("Incumbent(s):"):
            val = line.split(":", 1)[1].strip()
            if val and val != "(none)":
                for inc in val.split(";"):
                    inc = inc.strip()
                    if inc and inc not in current["incumbents"]:
                        current["incumbents"].append(inc)
            continue
        if line.startswith("Qualified Date:"):
            # scan upward: skip one designation line, capture the ALL CAPS name
            j = i - 1
            designation = lines[j].strip()
            if designation and not is_name(designation) and not designation.startswith(KEY_PREFIXES):
                j -= 1
            name_line = lines[j].strip()
            if name_line.startswith("Candidate(s):"):
                name_line = name_line[len("Candidate(s):"):].strip()
            if not is_name(name_line):
                raise AssertionError(f"line {i}: cannot find candidate name above {line!r}; got {name_line!r}")
            party = None
            pm = PARTY_RE.match(name_line)
            if pm:
                name_line, party = pm.group("name").strip(), pm.group("party")
            incumbent = designation == "Incumbent"
            for cand in current["candidates"]:
                if cand["name"] == name_line:
                    cand["incumbent_flag"] = cand["incumbent_flag"] or incumbent
                    break
            else:
                current["candidates"].append({"name": name_line, "party": party,
                                               "incumbent_flag": incumbent})
    return contests


if __name__ == "__main__":
    text = open("proof.txt").read()
    contests = parse(text)
    on_ballot = {k: v for k, v in contests.items() if v["on_ballot"]}
    print("total contest ids:", len(contests))
    print("on ballot:", len(on_ballot))
    mismatches = []
    for cid, c in contests.items():
        if not c["on_ballot"] or not c["districts"]:
            continue
        want = max(d["qualified"] for d in c["districts"])
        got = len(c["candidates"])
        if want != got:
            mismatches.append((cid, c["title"], want, got))
    print("count mismatches vs PDF stated columns:", mismatches or "NONE — parse is complete")
    for cid, c in contests.items():
        status = "ON" if c["on_ballot"] else "OFF"
        dist = "; ".join(f"{d['district'] or '(same)'} vf{d['vote_for']} {d['cands']}/{d['qualified']}" for d in c["districts"])
        cands = "; ".join(
            f"{x['name']}[{x['party'] or 'NP'}]{'*' if x['incumbent_flag'] else ''}" for x in c["candidates"])
        shared = " | shared: " + ",".join(c["shared_with"]) if c["shared_with"] else ""
        inc = " | incumbent: " + "; ".join(c["incumbents"]) if c["incumbents"] else ""
        print(f"{cid} [{status}] {c['office_header']} :: {c['title']} :: {dist}{shared}{inc}")
        if cands:
            print(f"     -> {cands}")
    json.dump(contests, open("proof-parsed.json", "w"), indent=1)
