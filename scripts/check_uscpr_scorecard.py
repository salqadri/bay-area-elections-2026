#!/usr/bin/env python3
"""Offline regressions for attributed USCPR Action grade capture."""

from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import uscpr_scorecard as scorecard


def member(chamber="House", grade="F", score="7%", member_id="P000613"):
    return {
        "id": member_id,
        "First Name": "Test",
        "Last Name": "Member",
        "Party": "Democrat",
        "District": "CA-19" if chamber == "House" else "California",
        "state": "CA",
        "119th Congress Grade": grade,
        "Lifetime Grade": "D",
        scorecard.CONGRESS_SCORE_FIELDS[chamber]: score,
        scorecard.LIFETIME_SCORE_FIELD: "25%",
    }


def feed():
    return {"house_representatives": [member()],
            "senate_representatives": [member("Senate", member_id="P000145")]}


def snapshot_inputs():
    return {
        "scorecard": f'<iframe src="{scorecard.APP_URL}"></iframe>'.encode(),
        "app": b'<script type="module" src="/assets/index-test123.js"></script>',
        "bundle": f'fetch("{scorecard.DATA_URL}")'.encode(),
        "data": json.dumps(feed()).encode(),
        "methodology": b"2026 Congress Scorecard Methodology. Members of Congress in the Democratic Caucus. Lifetime grades include actions between 2023 and 2026.",
        "checked_on": "2026-10-14",
    }


class GradeCaptureTests(unittest.TestCase):
    def test_separate_publisher_periods_and_scores(self):
        result = scorecard.normalize_members(feed())
        house = next(m for m in result if m["chamber"] == "House")
        self.assertEqual(house["member_id"], "P000613")
        self.assertEqual(house["district"], "CA-19")
        self.assertEqual([(g["period"], g["grade"], g["score"]) for g in house["grades"]],
                         [("119th Congress", "F", 7), ("Lifetime", "D", 25)])
        self.assertIn("119th Palestine Score", house["grades"][0]["score_field"])

    def test_not_available_is_never_f(self):
        data = feed()
        data["house_representatives"] = [member(grade="N/A", score="N/A")]
        grade = scorecard.normalize_members(data)[0]["grades"][0]
        self.assertIsNone(grade["grade"])
        self.assertIsNone(grade["score"])
        self.assertEqual(grade["source_grade"], "N/A")
        self.assertEqual(grade["source_score"], "N/A")

    def test_grade_not_recomputed_from_number(self):
        data = feed()
        data["house_representatives"] = [member(grade="A", score="0%")]
        grade = scorecard.normalize_members(data)[0]["grades"][0]
        self.assertEqual((grade["grade"], grade["score"]), ("A", 0))

    def test_optional_id_is_not_invented(self):
        data = feed()
        del data["house_representatives"][0]["id"]
        self.assertIsNone(scorecard.normalize_members(data)[0]["member_id"])

    def test_invalid_or_duplicate_identity_stops_capture(self):
        cases = []
        data = feed()
        data["house_representatives"][0]["District"] = "NY-19"
        cases.append(data)
        data = feed()
        data["senate_representatives"][0]["id"] = "P000613"
        cases.append(data)
        data = feed()
        data["house_representatives"].append(deepcopy(data["house_representatives"][0]))
        cases.append(data)
        data = feed()
        data["house_representatives"][0]["id"] = "wrong"
        cases.append(data)
        for data in cases:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    scorecard.normalize_members(data)

    def test_missing_grade_not_replaced_by_older_or_sheet_grade(self):
        data = feed()
        row = data["house_representatives"][0]
        del row["119th Congress Grade"]
        row["118th Congress Grade"] = "A"
        row["Column A"] = "A"
        with self.assertRaises(ValueError):
            scorecard.normalize_members(data)

    def test_unknown_grade_and_bad_scores_stop_capture(self):
        for grade, score in [("A+", "100%"), ("", "1%"), ("F", "101%"),
                             ("F", "-1%"), ("F", "NaN%"), ("F", "")]:
            data = feed()
            data["house_representatives"] = [member(grade=grade, score=score)]
            with self.subTest(grade=grade, score=score):
                with self.assertRaises(ValueError):
                    scorecard.normalize_members(data)
        self.assertEqual(scorecard.percentage("89.5%"), 89.5)

    def test_official_source_chain_and_hashes(self):
        result = scorecard.build_snapshot(**snapshot_inputs())
        self.assertEqual(result["format"], "uscpr-scorecard-grades/v1")
        self.assertEqual(result["coverage"]["chambers"], {"House": 1, "Senate": 1})
        self.assertEqual(len(result["sources"]), 5)
        for source in result["sources"]:
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(source["bytes"], 0)
        self.assertEqual(result["sources"][2]["url"],
                         "https://uscpr-voter-scorecard.web.app/assets/index-test123.js")
        for field, body in (("scorecard", b'<iframe src="https://example.org"></iframe>'),
                            ("app", b'<script src="https://example.org/data.js"></script>'),
                            ("bundle", b'fetch("https://example.org/grades")'),
                            ("bundle", f'const oldFeed = "{scorecard.DATA_URL}"; fetch("https://example.org/new");'.encode()),
                            ("methodology", b"2026 Congress Scorecard Methodology. Scope has changed."),
                            ("methodology", b"Not the expected source")):
            inputs = snapshot_inputs()
            inputs[field] = body
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    scorecard.build_snapshot(**inputs)

    def test_future_and_malformed_checked_dates_stop_capture(self):
        tomorrow = (scorecard.datetime.now(scorecard.ZoneInfo("America/Los_Angeles")).date() + timedelta(days=1)).isoformat()
        for value in (tomorrow, "2026-02-30", "20261014", "2026-10"):
            inputs = snapshot_inputs()
            inputs["checked_on"] = value
            with self.subTest(checked_on=value):
                with self.assertRaises(ValueError):
                    scorecard.build_snapshot(**inputs)

    def test_cli_cannot_replace_publication_files_or_source_input(self):
        script = Path(scorecard.__file__)
        root = script.resolve().parents[1]
        for target in (root / "2026-11-03_Bay_Area_Elections.json", root / "elections.schema.json",
                       root / "index.html", root / "ballot.html", root / "src/gaza-evidence-display.js"):
            before = target.read_bytes()
            result = subprocess.run([sys.executable, str(script), "--output", str(target)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Grade output cannot overwrite", result.stderr)
            self.assertEqual(target.read_bytes(), before)
            with patch.object(sys, "argv", [str(script), "--output", str(target)]), \
                 patch.object(scorecard, "fetch", side_effect=AssertionError("Output must be checked before network access")) as fetch:
                with self.assertRaises(ValueError):
                    scorecard.main()
                fetch.assert_not_called()
            with self.assertRaises(ValueError):
                scorecard.write_snapshot(target, {})
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "input.json"
            source.write_text("source must survive")
            # Invalid tiny source content proves destination checks happen before parsing/fetching.
            args = [sys.executable, str(script), "--output", str(source)]
            for name in ("scorecard", "app", "bundle", "data", "methodology"):
                args += [f"--{name}-file", str(source)]
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Grade output cannot overwrite a supplied source input", result.stderr)
            self.assertEqual(source.read_text(), "source must survive")

    def test_committed_capture_keeps_scope_and_na(self):
        path = Path(__file__).resolve().parents[1] / "research/gaza-records/uscpr-grades-2026-10-14.json"
        result = json.loads(path.read_text())
        self.assertEqual(result["format"], scorecard.FORMAT)
        self.assertEqual(result["source_url"], scorecard.SCORECARD_URL)
        self.assertEqual(result["data_url"], scorecard.DATA_URL)
        self.assertEqual(result["methodology_url"], scorecard.METHODOLOGY_URL)
        self.assertEqual(result["coverage"]["member_count"], len(result["members"]))
        for m in result["members"]:
            self.assertEqual([g["period"] for g in m["grades"]], ["119th Congress", "Lifetime"])
            for g in m["grades"]:
                self.assertEqual(g["grade"], None if g["source_grade"] == "N/A" else g["source_grade"])
                self.assertEqual(g["score"], scorecard.percentage(g["source_score"]))
        self.assertTrue(any(g["source_grade"] == "N/A" for m in result["members"] for g in m["grades"]))
        self.assertTrue(any(m["member_id"] is None for m in result["members"]))


if __name__ == "__main__":
    unittest.main()
