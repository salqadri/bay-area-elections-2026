"""Build the standalone GitHub Pages readers with optional remote analytics."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RECOMMENDATION_PLAN = ROOT / "research/candidate-recommendations/recommendations-2026-10-28-latest.json"


def recommendations_map_json():
    """Compact per-race recommendation map embedded in both readers. Only the
    fields the display needs; decisions stay in the archived plan."""
    plan = json.loads(RECOMMENDATION_PLAN.read_text(encoding="utf-8"))
    by_position = {}
    for r in plan["races"]:
        entry = {"category": r["category"], "recommended": r.get("recommended"),
                 "recommend_reason": r.get("recommend_reason")}
        why = r.get("recommend_reason_text") or r.get("summary")
        if r.get("recommended") and isinstance(why, dict) and why.get("text"):
            entry["why"] = {"text": why["text"], "model": why.get("model", "")}
        by_position[r["position_id"]] = entry
    from datetime import datetime, timezone, timedelta
    gen = plan.get("generated_on", "")
    try:  # archive timestamps are UTC; readers display Pacific dates
        gen = datetime.fromisoformat(gen).astimezone(timezone(timedelta(hours=-7))).date().isoformat()
    except ValueError:
        gen = gen[:10]
    payload = {"generated_on": gen,
               "plan_sha256": hashlib.sha256(RECOMMENDATION_PLAN.read_bytes()).hexdigest(),
               "byPosition": by_position}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def render(page="index"):
    html = (ROOT / f"src/{page}.template.html").read_text(encoding="utf-8")
    resources = {"__ELECTION_DATA_JSON__": "2026-11-03_Bay_Area_Elections.json"}
    if page == "index":
        resources["__ELECTION_SCHEMA_JSON__"] = "elections.schema.json"
    for placeholder, filename in resources.items():
        if html.count(placeholder) != 1:
            raise ValueError(f"Expected one {placeholder} in the template")
        data = json.loads((ROOT / filename).read_text(encoding="utf-8"))
        embedded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        html = html.replace(placeholder, embedded)
    analytics_js = (ROOT / 'src/analytics.js').read_text(encoding='utf-8')
    assert '</script' not in analytics_js.lower(), 'Unsafe inline analytics script'
    if html.count('__ANALYTICS_JS__') != 1:
        raise ValueError('Expected one shared analytics placeholder')
    html = html.replace('__ANALYTICS_JS__', analytics_js)
    endorsement_js = (ROOT / 'src/endorsement-display.js').read_text(encoding='utf-8')
    assert '</script' not in endorsement_js.lower(), 'Unsafe inline endorsement script'
    if html.count('__ENDORSEMENT_DISPLAY_JS__') != 1:
        raise ValueError('Expected one shared endorsement display placeholder')
    html = html.replace('__ENDORSEMENT_DISPLAY_JS__', endorsement_js)
    finance_js = (ROOT / 'src/finance-display.js').read_text(encoding='utf-8')
    assert '</script' not in finance_js.lower(), 'Unsafe inline finance script'
    if html.count('__FINANCE_DISPLAY_JS__') != 1:
        raise ValueError('Expected one shared finance display placeholder')
    html = html.replace('__FINANCE_DISPLAY_JS__', finance_js)
    gaza_js = (ROOT / 'src/gaza-evidence-display.js').read_text(encoding='utf-8')
    assert '</script' not in gaza_js.lower(), 'Unsafe inline Gaza evidence script'
    if html.count('__GAZA_EVIDENCE_DISPLAY_JS__') != 1:
        raise ValueError('Expected one shared Gaza evidence display placeholder')
    html = html.replace('__GAZA_EVIDENCE_DISPLAY_JS__', gaza_js)
    grade_js = (ROOT / 'src/pro-palestine-grade-display.js').read_text(encoding='utf-8')
    assert '</script' not in grade_js.lower(), 'Unsafe inline grade script'
    if html.count('__PRO_PALESTINE_GRADE_JS__') != 1:
        raise ValueError('Expected one shared model-grade placeholder')
    html = html.replace('__PRO_PALESTINE_GRADE_JS__', grade_js)
    rec_display_js = (ROOT / 'src/recommendation-display.js').read_text(encoding='utf-8')
    assert '</script' not in rec_display_js.lower(), 'Unsafe inline recommendation display script'
    if html.count('__RECOMMENDATION_DISPLAY_JS__') != 1:
        raise ValueError('Expected one shared recommendation display placeholder')
    html = html.replace('__RECOMMENDATION_DISPLAY_JS__', rec_display_js)
    if html.count('__RECOMMENDATIONS_MAP_JSON__') != 1:
        raise ValueError('Expected one recommendations map placeholder')
    html = html.replace('__RECOMMENDATIONS_MAP_JSON__', recommendations_map_json())
    platform_js = (ROOT / 'src/platform-display.js').read_text(encoding='utf-8')
    assert '</script' not in platform_js.lower(), 'Unsafe inline platform display script'
    if html.count('__PLATFORM_DISPLAY_JS__') != 1:
        raise ValueError('Expected one shared platform display placeholder')
    html = html.replace('__PLATFORM_DISPLAY_JS__', platform_js)
    sort_js = (ROOT / 'src/candidate-sort.js').read_text(encoding='utf-8')
    assert '</script' not in sort_js.lower(), 'Unsafe inline candidate sort script'
    if html.count('__CANDIDATE_SORT_JS__') != 1:
        raise ValueError('Expected one shared candidate sort placeholder')
    html = html.replace('__CANDIDATE_SORT_JS__', sort_js)
    label_js = (ROOT / 'src/contest-label.js').read_text(encoding='utf-8')
    assert '</script' not in label_js.lower(), 'Unsafe inline contest label script'
    if html.count('__CONTEST_LABEL_JS__') != 1:
        raise ValueError('Expected one shared contest label placeholder')
    html = html.replace('__CONTEST_LABEL_JS__', label_js)
    if page == "ballot":
        source = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        css = re.search(r"<style>(.*?)</style>", source, re.S).group(1)
        replacements = {"__BALLOT_SHARED_CSS__": css}
        for placeholder, filename in {
            "__ADDRESS_SERVICE_JS__": "address-services.js",
            "__ADDRESS_MATCHER_JS__": "address-matcher.js",
            "__ADDRESS_SUGGESTIONS_JS__": "address-suggestions.js",
            "__ADDRESS_AUTOCOMPLETE_JS__": "address-autocomplete.js",
            "__BALLOT_PAGE_JS__": "ballot-page.js",
        }.items():
            javascript = (ROOT / "src" / filename).read_text(encoding="utf-8")
            if filename == 'address-matcher.js':
                registry = json.loads((ROOT / 'research/california-counties.json').read_text())
                javascript = javascript.replace('__CALIFORNIA_COUNTY_FIPS_JSON__', json.dumps({c['fips']: c['name'] for c in registry['counties']}, ensure_ascii=False))
            assert "</script" not in javascript.lower(), f"Unsafe inline script in {filename}"
            replacements[placeholder] = javascript
        for placeholder, content in replacements.items():
            if html.count(placeholder) != 1:
                raise ValueError(f"Expected one {placeholder} in {page} template")
            html = html.replace(placeholder, content)
    if re.search(r"__[A-Z_]+__", html):
        raise ValueError("Unresolved template placeholder")
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify index.html is current without changing it")
    args = parser.parse_args()
    for page in ["index", "ballot"]:
        result = render(page)
        output = ROOT / f"{page}.html"
        if args.check:
            if output.read_text(encoding="utf-8") != result:
                raise SystemExit(f"{page}.html is stale; run python3 scripts/build_site.py")
            print(f"{page}.html exactly matches its source files and embedded data.")
        else:
            output.write_text(result, encoding="utf-8")
            print(f"Built {page}.html ({output.stat().st_size:,} bytes).")
