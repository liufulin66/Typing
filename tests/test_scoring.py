import math
import unittest

from typing_app.scoring import calculate_result


class ScoringTests(unittest.TestCase):
    def run_config(self, language="en", mode="full", target="a" * 100):
        return {"mode": mode, "language": language, "target_text": target, "duration_seconds": 60}

    def payload(self, text="a" * 100, attempts=100, correct=100, elapsed=60000):
        return {"final_input": text, "attempted_chars": attempts,
                "correct_attempts": correct, "elapsed_ms": elapsed}

    def test_language_speed_units(self):
        en = calculate_result(self.run_config(), self.payload())
        zh = calculate_result(self.run_config("zh"), self.payload())
        self.assertEqual((en["speed"], en["speed_unit"]), (20, "WPM"))
        self.assertEqual((zh["speed"], zh["speed_unit"]), (100, "字符/分钟"))

    def test_corrected_error_is_still_in_accuracy(self):
        result = calculate_result(self.run_config(mode="lesson", target="a" * 19),
                                  self.payload(text="a" * 19, attempts=20, correct=19))
        self.assertEqual(result["accuracy"], 95)
        self.assertEqual(result["passed"], 1)

    def test_rounding_cannot_unlock_and_client_pass_is_ignored(self):
        data = self.payload(attempts=10001, correct=9500)
        data["passed"] = True
        result = calculate_result(self.run_config(mode="lesson"), data)
        self.assertEqual(round(result["accuracy"], 1), 95)
        self.assertEqual(result["passed"], 0)

    def test_invalid_counts_and_zero_attempts(self):
        for changes in ({"attempted_chars": 0}, {"attempted_chars": -1},
                        {"correct_attempts": 101}, {"correct_attempts": True},
                        {"elapsed_ms": -1}, {"elapsed_ms": math.inf},
                        {"elapsed_ms": math.nan}, {"elapsed_ms": 10**1000}, {"attempted_chars": "100"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                calculate_result(self.run_config(), self.payload() | changes)

    def test_partial_and_timed_early_results_rejected(self):
        with self.assertRaises(ValueError):
            calculate_result(self.run_config(), self.payload(text="a"))
        with self.assertRaises(ValueError):
            calculate_result(self.run_config(mode="timed"), self.payload(elapsed=59000))

    def test_timed_target_repeats_and_zero_time_has_finite_speed(self):
        result = calculate_result(self.run_config(mode="timed", target="ab"),
                                  self.payload(text="ababab", attempts=6, correct=6))
        self.assertEqual(result["final_correct_chars"], 6)
        result = calculate_result(self.run_config(target="a"),
                                  self.payload(text="a", attempts=1, correct=1, elapsed=0))
        self.assertTrue(math.isfinite(result["speed"]))

    def test_unicode_codepoints_and_punctuation(self):
        text = "你 好。🌱"
        result = calculate_result(self.run_config("zh", target=text),
                                  self.payload(text=text, attempts=len(text), correct=len(text)))
        self.assertEqual(result["final_correct_chars"], len(text))
