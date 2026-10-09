"""Build the dependency-free, standalone GitHub Pages entry point."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
    endorsement_js = (ROOT / 'src/endorsement-display.js').read_text(encoding='utf-8')
    assert '</script' not in endorsement_js.lower(), 'Unsafe inline endorsement script'
    if html.count('__ENDORSEMENT_DISPLAY_JS__') != 1:
        raise ValueError('Expected one shared endorsement display placeholder')
    html = html.replace('__ENDORSEMENT_DISPLAY_JS__', endorsement_js)
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
