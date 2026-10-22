import string
import unittest

from typing_app.courses import FINGER_MAP, get_lessons


class CourseDataTests(unittest.TestCase):
    def test_course_is_gradual_and_covers_alphabet(self):
        lessons = get_lessons()
        self.assertEqual(len(lessons), 16)
        self.assertEqual(len({item["id"] for item in lessons}), 16)
        learned = set()
        for lesson in lessons[:14]:
            introduced = set(lesson["new_keys"])
            self.assertIn(len(introduced), (1, 2))
            self.assertFalse(learned & introduced)
            previous = learned.copy()
            learned |= introduced
            used = set(lesson["text"]) - {" "}
            self.assertLessEqual(used, learned, lesson["id"])
            self.assertLessEqual(introduced, used)
            if previous:
                self.assertTrue(previous & used)
            self.assertGreaterEqual(len(lesson["text"]), 30)
        self.assertEqual(learned, set(string.ascii_lowercase))
        self.assertEqual(lessons[0]["new_keys"], "fj")
        for lesson in lessons[14:]:
            self.assertLessEqual(set(lesson["text"]), learned | {" "})

    def test_each_letter_has_correct_standard_finger_group(self):
        self.assertEqual(set(FINGER_MAP), set(string.ascii_lowercase + " "))
        expected = {"f":"左手食指", "j":"右手食指", "q":"左手小指", "p":"右手小指",
                    "c":"左手中指", "x":"左手无名指", "z":"左手小指",
                    "b":"左手食指", "n":"右手食指", " ":"拇指"}
        for key, finger in expected.items():
            self.assertEqual(FINGER_MAP[key], finger)
