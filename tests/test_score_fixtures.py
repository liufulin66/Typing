import json
import unittest
from pathlib import Path

from typing_app.scoring import calculate_result


class SharedFixtureTests(unittest.TestCase):
    def test_browser_golden_cases_match_backend_definitions(self):
        path = Path(__file__).parents[1] / "typing_app" / "static" / "score-cases.json"
        for case in json.loads(path.read_text(encoding="utf-8")):
            with self.subTest(case=case["name"]):
                expected = case["expected"]
                score = calculate_result(case["run"], {
                    "final_input":case["steps"][-1]["value"],
                    "attempted_chars":expected["attempted_chars"],
                    "correct_attempts":expected["correct_attempts"], "elapsed_ms":case["elapsed_ms"],
                })
                for key, value in expected.items():
                    self.assertAlmostEqual(score[key], value)
