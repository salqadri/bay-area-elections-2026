"""Build the dependency-free, standalone GitHub Pages entry point."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def render():
    html = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
    for placeholder, filename in (
        ("__ELECTION_DATA_JSON__", "2026-11-03_Bay_Area_Elections.json"),
        ("__ELECTION_SCHEMA_JSON__", "elections.schema.json"),
    ):
        if html.count(placeholder) != 1:
            raise ValueError(f"Expected one {placeholder} in the template")
        data = json.loads((ROOT / filename).read_text(encoding="utf-8"))
        embedded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        html = html.replace(placeholder, embedded)
    if "__ELECTION_" in html:
        raise ValueError("Unresolved election template placeholder")
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify index.html is current without changing it")
    args = parser.parse_args()
    result = render()
    output = ROOT / "index.html"
    if args.check:
        if output.read_text(encoding="utf-8") != result:
            raise SystemExit("index.html is stale; run python3 scripts/build_site.py")
        print("index.html exactly matches the current template, dataset, and schema.")
    else:
        output.write_text(result, encoding="utf-8")
        print(f"Built index.html ({output.stat().st_size:,} bytes); no runtime dependencies.")
