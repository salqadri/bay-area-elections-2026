#!/usr/bin/env python3
"""Capture the grades delivered by USCPR Action's official scorecard.

The spreadsheet is deliberately not an input. Grades are publisher assessments,
not a calculation performed here and not a vote-only score. Network collection
follows the official scorecard's embedded application to its public data feed.
Pass all five --*-file options for a repeatable, completely offline capture.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


SCORECARD_URL = "https://www.uscpraction.org/scorecard"
METHODOLOGY_URL = "https://www.uscpraction.org/methodology"
APP_URL = "https://uscpr-voter-scorecard.web.app/"
DATA_URL = "https://uscpr-voter-scorecard.s3.us-east-1.amazonaws.com/data.json"
PUBLISHER = "US Campaign for Palestinian Rights Action (USCPR Action)"
FORMAT = "uscpr-scorecard-grades/v1"
ROOT = Path(__file__).resolve().parents[1]
MAX_CAPTURE_BYTES = 12_000_000
LIFETIME_SCORE_FIELD = 'Total Palestine Score ("Present" vote = half of "Yes")'
CONGRESS_SCORE_FIELDS = {
    "House": '119th Palestine Score (Weights: 5% "Genocide", 15% Arms Embargo, 40% Sponsors, 40% Voting; "Present" vote = half of "Yea") +10% for introducing legislation',
    "Senate": '119th Palestine Score (Weights: 10% "Genocide", 10% Arms Embargo, 40% Sponsors, 40% Voting; "Present" vote = half of "Yea")',
}


class PageReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.iframes: list[str] = []
        self.scripts: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "iframe" and values.get("src"):
            self.iframes.append(values["src"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def app_bundle_url(scorecard: bytes, app: bytes) -> str:
    """Require the official page -> app -> same-origin JS provenance chain."""
    page = PageReferences()
    page.feed(scorecard.decode("utf-8-sig"))
    if not any(urljoin(SCORECARD_URL, src).rstrip("/") == APP_URL.rstrip("/")
               for src in page.iframes):
        raise ValueError("Official scorecard no longer embeds the expected application; review source delivery")
    embedded = PageReferences()
    embedded.feed(app.decode("utf-8-sig"))
    bundles = [urljoin(APP_URL, src) for src in embedded.scripts
               if re.fullmatch(r"/assets/index-[A-Za-z0-9_-]+\.js", src)]
    if len(bundles) != 1:
        raise ValueError("Expected exactly one application bundle; review source delivery")
    return bundles[0]


def require_text(row: dict, field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid member field: {field}")
    return value.strip()


def percentage(value: object) -> float | int | None:
    if value == "N/A":
        return None
    if not isinstance(value, str) or not re.fullmatch(r"(?:\d+(?:\.\d+)?)%", value):
        raise ValueError(f"Invalid publisher percentage: {value!r}")
    number = float(value[:-1])
    if not 0 <= number <= 100:
        raise ValueError(f"Publisher percentage outside 0–100: {value!r}")
    return int(number) if number.is_integer() else number


def grade_record(row: dict, period: str, grade_field: str, score_field: str) -> dict:
    grade = require_text(row, grade_field)
    if grade not in {"A", "B", "C", "D", "F", "N/A"}:
        raise ValueError(f"Unknown publisher grade: {grade!r}")
    if score_field not in row:
        raise ValueError(f"Missing publisher score field: {score_field}")
    return {
        "period": period,
        "grade": None if grade == "N/A" else grade,
        "source_grade": grade,
        "grade_field": grade_field,
        "score": percentage(row[score_field]),
        "source_score": row[score_field],
        "score_field": score_field,
    }


def normalize_members(data: dict) -> list[dict]:
    if not isinstance(data, dict) or set(data) != {"house_representatives", "senate_representatives"}:
        raise ValueError("Unexpected scorecard data structure; review the official feed")
    members = []
    member_ids: set[str] = set()
    identities: set[tuple] = set()
    for source_key, chamber in (("house_representatives", "House"), ("senate_representatives", "Senate")):
        rows = data[source_key]
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"Missing {chamber} source rows")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Member record must be an object")
            given, family = require_text(row, "First Name"), require_text(row, "Last Name")
            state, district = require_text(row, "state"), require_text(row, "District")
            if not re.fullmatch(r"[A-Z]{2}", state):
                raise ValueError(f"Invalid member state: {state!r}")
            if chamber == "House" and not re.fullmatch(re.escape(state) + r"-(?:\d{2}|AL)", district):
                raise ValueError(f"House district does not match member state: {district!r}")
            member_id = row.get("id") or None
            if member_id is not None:
                if not isinstance(member_id, str) or not re.fullmatch(r"[A-Z]\d{6}", member_id):
                    raise ValueError(f"Invalid source member ID: {member_id!r}")
                if member_id in member_ids:
                    raise ValueError(f"Duplicate source member ID: {member_id}")
                member_ids.add(member_id)
            identity = (chamber, state, district, given, family)
            if identity in identities:
                raise ValueError(f"Duplicate member identity: {identity}")
            identities.add(identity)
            members.append({
                "member_id": member_id,
                "name": f"{given} {family}",
                "given_name": given,
                "family_name": family,
                "chamber": chamber,
                "state": state,
                "district": district,
                "party": require_text(row, "Party"),
                "grades": [
                    grade_record(row, "119th Congress", "119th Congress Grade", CONGRESS_SCORE_FIELDS[chamber]),
                    grade_record(row, "Lifetime", "Lifetime Grade", LIFETIME_SCORE_FIELD),
                ],
            })
    return sorted(members, key=lambda m: (m["chamber"], m["state"], m["district"], m["name"]))


def source_capture(role: str, url: str, body: bytes) -> dict:
    return {"role": role, "url": url, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}


def validate_checked_on(value: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("checked_on must be a full YYYY-MM-DD date")
    parsed = date.fromisoformat(value)
    if parsed > datetime.now(ZoneInfo("America/Los_Angeles")).date():
        raise ValueError("checked_on cannot be in the future (America/Los_Angeles)")
    return parsed


def build_snapshot(*, scorecard: bytes, app: bytes, bundle: bytes, data: bytes,
                   methodology: bytes, checked_on: str) -> dict:
    validate_checked_on(checked_on)
    bundle_url = app_bundle_url(scorecard, app)
    if not re.search(rb'fetch\(\s*(["\'])' + re.escape(DATA_URL.encode()) + rb'\1\s*\)', bundle):
        raise ValueError("Application bundle no longer uses the expected feed; review source delivery")
    method_page = PageReferences()
    method_page.feed(methodology.decode("utf-8-sig"))
    method_text = " ".join(" ".join(method_page.text).split())
    expected_method = ("2026 Congress Scorecard Methodology", "in the Democratic Caucus",
                       "Lifetime grades include", "between 2023 and 2026")
    if not all(text in method_text for text in expected_method):
        raise ValueError("USCPR Action methodology scope changed; review the captured period and coverage before updating")
    members = normalize_members(json.loads(data))
    return {
        "format": FORMAT,
        "checked_on": checked_on,
        "publisher": PUBLISHER,
        "source_url": SCORECARD_URL,
        "data_url": DATA_URL,
        "methodology_url": METHODOLOGY_URL,
        "sources": [
            source_capture("scorecard", SCORECARD_URL, scorecard),
            source_capture("embedded_application", APP_URL, app),
            source_capture("application_bundle", bundle_url, bundle),
            source_capture("grades_feed", DATA_URL, data),
            source_capture("methodology", METHODOLOGY_URL, methodology),
        ],
        "coverage": {
            "member_count": len(members),
            "chambers": {chamber: sum(m["chamber"] == chamber for m in members)
                         for chamber in ("House", "Senate")},
            "publisher_scope": "Members of Congress in the Democratic Caucus; the feed also includes Independent senators.",
            "current_grade_period": "119th Congress (2025–2027)",
            "lifetime_grade_period": "Publisher methodology describes legislative action from 2023–2026, including the 119th Congress.",
            "method": "Publisher grades combine votes, letters, sponsorships and other legislative actions, plus additional factors; they are not vote-only scores. Grades and percentage scores are copied without recalculation.",
            "limits": [
                "Absent members and N/A entries remain ungraded; absence does not mean F or establish a position.",
                "This current feed does not supply grades for every former member or new candidate.",
                "House districts identify the publisher's member record and must not be used to infer a 2026 ballot district.",
                "The publisher's Lifetime label does not certify a complete career voting history; individual feed actions may predate the methodology's stated period.",
                "This capture preserves attributed publisher assessments; it does not independently verify the underlying legislative actions.",
            ],
        },
        "members": members,
    }


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "BayAreaBallotResearch/1.0 (+https://github.com/salqadri/bay-area-elections-2026)"})
    with urlopen(request, timeout=60) as response:
        if urlsplit(response.url).scheme != "https":
            raise ValueError("Refusing a source redirected outside HTTPS")
        body = response.read(MAX_CAPTURE_BYTES + 1)
    if len(body) > MAX_CAPTURE_BYTES:
        raise ValueError(f"Source capture exceeds {MAX_CAPTURE_BYTES} bytes")
    return body


def validate_output_path(path: Path, input_paths=()) -> None:
    target = path.resolve()
    maintained = {(ROOT / name).resolve() for name in ("2026-11-03_Bay_Area_Elections.json", "elections.schema.json",
                                                       "index.html", "ballot.html")}
    if target in maintained or target.is_relative_to((ROOT / "src").resolve()):
        raise ValueError("Grade output cannot overwrite the maintained dataset, schema, pages or src files")
    if target in {source.resolve() for source in input_paths if source is not None}:
        raise ValueError("Grade output cannot overwrite a supplied source input")


def write_snapshot(path: Path, result: dict, input_paths=()) -> None:
    """Replace a capture only after complete validation and a successful write."""
    validate_output_path(path, input_paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".", delete=False) as output:
            temporary = Path(output.name)
            output.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checked-on", default=datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat())
    for name in ("scorecard", "app", "bundle", "data", "methodology"):
        parser.add_argument(f"--{name}-file", type=Path)
    args = parser.parse_args()
    validate_checked_on(args.checked_on)
    paths = [getattr(args, name + "_file") for name in ("scorecard", "app", "bundle", "data", "methodology")]
    if any(paths) and not all(paths):
        parser.error("Offline input requires all five --*-file options; source provenance must be complete")
    validate_output_path(args.output, paths)
    if all(paths):
        scorecard, app, bundle, data, methodology = [path.read_bytes() for path in paths]
    else:
        scorecard, app = fetch(SCORECARD_URL), fetch(APP_URL)
        bundle = fetch(app_bundle_url(scorecard, app))
        data, methodology = fetch(DATA_URL), fetch(METHODOLOGY_URL)
    result = build_snapshot(scorecard=scorecard, app=app, bundle=bundle, data=data,
                            methodology=methodology, checked_on=args.checked_on)
    write_snapshot(args.output, result, paths)
    print(f"Captured {len(result['members'])} USCPR Action member grade records to {args.output}")


if __name__ == "__main__":
    main()
