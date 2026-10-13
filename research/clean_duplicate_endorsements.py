"""Remove duplicate endorsement records created by the campaign-site logo scan.

The October 11 site scan wrote one record per endorsement *asset*: a named
record plus, sometimes, an artifact record whose quote is just the logo file
name ("HAPAC.png"). It also left abbreviation/named pairs of the same endorser
("BPOA" vs "BART Police Officers Association", "fiona ma" vs "State Treasurer
Fiona Ma"). This script removes only mechanically provable duplicates:

Rule A  artifact record (quote is a bare filename) whose logo_url matches a
        named sibling -> drop the artifact.
Rule B  artifact record whose endorser normalizes to an abbreviation of a
        named sibling's endorser (POA->Police Officers' Association, plus
        exact word-initial match) -> drop the artifact.
Rule C  two *named* records sharing one logo_url where one endorser name is a
        case/punctuation-insensitive substring of the other or matches its
        word initials -> keep the richer record (endorser_statement beats
        campaign_claim, then longer name), drop the weaker.

Never dropped: artifacts with no sibling (they are the only evidence of that
endorsement) and named pairs needing human judgment ("IAFF Local 1974" vs
"Livermore-Pleasanton Firefighters").

Run from repo root: python3 research/clean_duplicate_endorsements.py [--dry]
"""
import json, re, sys, collections

PATH = "2026-11-03_Bay_Area_Elections.json"
FN = re.compile(r"\.(png|jpe?g|svg|gif)$", re.I)

def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).replace("  ", " ").strip()

def initials(s):
    return "".join(w[0] for w in norm(s).split())

def is_artifact(e):
    q = (e.get("quote") or "").strip()
    return bool(FN.search(q) and "/" not in q)

EXPAND = [  # abbreviation expansions applied before comparing
    ("poa", "police officers association"),
    ("lpc", "league of conservation voters"),
    ("hapac", "hindu american pac"),
]

def canon(s):
    n = norm(s)
    for abbr, full in EXPAND:
        n = re.sub(rf"\b{abbr}\b", full, n)
    return re.sub(r"\s+", " ", n).strip()

def loose_match(a, b):
    """Containment / exact / single-token-abbreviation initials.

    Multi-token names must share a substring; only an unbroken abbreviation
    (NUHW, LCVEB) may match the other name's initials — matching two distinct
    people by shared initials ("Tony Thurmond" vs "Tom Torlakson") is banned.
    """
    ca, cb = canon(a), canon(b)
    if not ca or not cb:
        return False
    if (ca == cb) or (len(ca) >= 4 and ca in cb) or (len(cb) >= 4 and cb in ca):
        return True
    for x, y in ((norm(a), norm(b)), (norm(b), norm(a))):
        if " " not in x and len(x) >= 3 and x == initials(y):
            return True
    return False

def rule_b_match(a, b):
    """Artifact a vs named sibling b: strict enough to trust without logo."""
    ca, cb = canon(a["endorser"]), canon(b["endorser"])
    if ca and ca == cb:                      # exact after expansion (HAPAC)
        return True
    na = norm(a["endorser"])                 # single-token abbreviation (BPOA)
    if " " not in na and len(na) >= 3 and na == initials(cb):
        return True
    nb = norm(b["endorser"])
    if " " not in nb and len(nb) >= 3 and nb == initials(ca):
        return True
    shared_logo = a.get("logo_url") and a.get("logo_url") == b.get("logo_url")
    return bool(shared_logo and loose_match(a["endorser"], b["endorser"]))

def same_org(a, b):
    """Named-vs-named pairs already share a logo — loose match is fine."""
    return loose_match(a, b)

def richer(a, b):
    """Return the record to keep between two named duplicates."""
    rank = {"endorser_statement": 2, "press_report": 1}
    ra, rb = rank.get(a.get("verification"), 0), rank.get(b.get("verification"), 0)
    if ra != rb:
        return a if ra > rb else b
    la, lb = len(a.get("quote") or ""), len(b.get("quote") or "")
    if la != lb:
        return a if la > lb else b
    return a if len(a["endorser"]) >= len(b["endorser"]) else b

def main(dry):
    d = json.load(open(PATH))
    dropped_a = dropped_b = dropped_c = 0
    log = []
    for p in d["positions"]:
        for c in p.get("candidates") or []:
            ents = c.get("endorsements")
            if not ents:
                continue
            arts = [e for e in ents if is_artifact(e)]
            named = [e for e in ents if not is_artifact(e)]
            drop = set()

            named_logos = collections.defaultdict(list)
            for e in named:
                if e.get("logo_url"):
                    named_logos[e["logo_url"]].append(e)

            for a in arts:  # Rule A
                if a.get("logo_url") and named_logos.get(a["logo_url"]) and id(a) not in drop:
                    sib = named_logos[a["logo_url"]][0]
                    drop.add(id(a))
                    dropped_a += 1
                    log.append((p["id"], c["name"], a["endorser"], f"rule A -> {sib['endorser']}"))
                    continue
            for a in arts:  # Rule B
                if id(a) in drop:
                    continue
                hit = next((n for n in named if same_org(a["endorser"], n["endorser"])), None)
                if hit:
                    drop.add(id(a))
                    dropped_b += 1
                    log.append((p["id"], c["name"], a["endorser"], f"rule B -> {hit['endorser']}"))

            bylogo = collections.defaultdict(list)  # Rule C on survivors
            for e in named:
                if id(e) not in drop and e.get("logo_url"):
                    bylogo[e["logo_url"]].append(e)
            for group in bylogo.values():
                keep = []
                for e in group:
                    merged = False
                    for i, k in enumerate(keep):
                        if same_org(e["endorser"], k["endorser"]):
                            winner = richer(k, e)
                            loser = e if winner is k else k
                            drop.add(id(loser))
                            dropped_c += 1
                            log.append((p["id"], c["name"], loser["endorser"], f"rule C -> {winner['endorser']}"))
                            keep[i] = winner
                            merged = True
                            break
                    if not merged:
                        keep.append(e)

            if drop:
                c["endorsements"] = [e for e in ents if id(e) not in drop]
    total_dropped_a, total_dropped_b, total_dropped_c = dropped_a, dropped_b, dropped_c
    print(f"rule A (logo-matched artifacts): {total_dropped_a}")
    print(f"rule B (abbreviation artifacts): {total_dropped_b}")
    print(f"rule C (named-vs-named same logo): {total_dropped_c}")
    print(f"total dropped: {total_dropped_a + total_dropped_b + total_dropped_c}")
    if dry:
        for row in log[:60]:
            print("  ", *row)
        return
    json.dump(d, open(PATH, "w"), indent=1, ensure_ascii=False)
    open(PATH, "a").write("\n")

if __name__ == "__main__":
    main("--dry" in sys.argv)
