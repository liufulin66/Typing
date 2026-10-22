from typing_app.courses import get_lessons, get_progress
from tests.support import AppCase


class ProgressTests(AppCase):
    def test_first_lesson_only_and_sequential_unlock(self):
        with self.app.app_context():
            initial = get_progress()
            self.assertEqual(sum(item["unlocked"] for item in initial["lessons"]), 1)
            self.insert_run("one", "lesson", "home-fj")
            self.insert_score("one")
            after = get_progress()
            self.assertTrue(after["lessons"][1]["unlocked"])
            self.assertFalse(after["lessons"][2]["unlocked"])
            self.assertEqual(after["next_lesson"]["id"], "home-dk")
            self.insert_run("redo", "lesson", "home-fj")
            self.insert_score("redo", False)
            self.assertTrue(get_progress()["lessons"][0]["passed"])
            self.assertTrue(get_progress()["lessons"][1]["unlocked"])

    def test_full_course_has_no_out_of_range_next_lesson(self):
        with self.app.app_context():
            for lesson in get_lessons():
                self.insert_run(lesson["id"], "lesson", lesson["id"])
                self.insert_score(lesson["id"])
            progress = get_progress()
            self.assertTrue(progress["all_done"])
            self.assertEqual(progress["completed"], 16)
            self.assertIsNone(progress["next_lesson"])

    def test_a_later_pass_alone_cannot_unlock_chain(self):
        with self.app.app_context():
            self.insert_run("later", "lesson", "home-dk")
            self.insert_score("later")
            self.assertFalse(get_progress()["lessons"][2]["unlocked"])
