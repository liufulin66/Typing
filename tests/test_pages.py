from tests.support import AppCase
from typing_app.courses import get_lessons


class PageTests(AppCase):
    def test_course_list_has_locked_states_and_final_completion_entry(self):
        response = self.client.get("/lessons")
        self.assertEqual(response.status_code, 200)
        self.assertIn("尚未解锁", response.text)
        self.assertNotIn('href="/practice?lesson=home-dk"', response.text)
        with self.app.app_context():
            for lesson in get_lessons():
                self.insert_run(lesson["id"], "lesson", lesson["id"])
                self.insert_score(lesson["id"])
        completed = self.client.get("/lessons").text
        self.assertIn("整套课程已完成", completed)
        self.assertIn("试试文章练习", completed)

    def test_home_and_setup_pages_render(self):
        for path in ("/", "/practice", "/practice?mode=timed&language=en"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("KEYJOURNEY", response.text)

    def test_locked_and_unknown_session_pages(self):
        self.assertEqual(self.client.get("/practice?lesson=home-dk").status_code, 403)
        self.assertEqual(self.client.get("/practice?run=unknown").status_code, 404)

    def test_custom_source_cannot_escape_embedded_json(self):
        text = '</script><script>alert("x")</script>'
        run = self.client.post("/api/runs", json={"mode":"full", "text":text}).json["run"]
        page = self.client.get(f'/practice?run={run["id"]}').text
        self.assertNotIn(text, page)
        self.assertIn("\\u003c/script\\u003e", page)

    def test_javascript_module_has_executable_mime_type(self):
        response = self.client.get("/static/engine.mjs")
        self.assertEqual(response.mimetype, "text/javascript")
        response.close()
