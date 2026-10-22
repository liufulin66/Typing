from typing_app import create_app
from tests.support import AppCase


class HistoryTests(AppCase):
    def complete(self, body, fail=False):
        run = self.client.post("/api/runs", json=body).json["run"]
        text = run["target_text"]
        self.client.post(f'/api/runs/{run["id"]}/result', json={
            "final_input":text, "attempted_chars":len(text),
            "correct_attempts":0 if fail else len(text), "elapsed_ms":60000})
        return run["id"]

    def test_empty_and_invalid_pagination(self):
        response = self.client.get("/api/history")
        self.assertEqual(response.json["results"], [])
        self.assertEqual(response.json["total"], 0)
        self.assertIn("你的第一份练习记录", self.client.get("/history").text)
        for query in ("limit=0", "offset=-1", "limit=no", "limit=101"):
            self.assertEqual(self.client.get("/api/history?" + query).status_code, 400)

    def test_order_units_failed_passed_pagination_and_restart(self):
        self.complete({"mode":"full", "language":"zh", "text":"你好"})
        self.complete({"mode":"timed", "language":"en", "text":"ab", "duration_seconds":60})
        self.complete({"mode":"lesson", "lesson_id":"home-fj"}, fail=True)
        latest = self.complete({"mode":"lesson", "lesson_id":"home-fj"})
        page = self.client.get("/api/history?limit=2").json
        self.assertEqual(page["total"], 4)
        self.assertEqual(page["results"][0]["run_id"], latest)
        self.assertEqual([r["passed"] for r in page["results"]], [True, False])
        older = self.client.get("/api/history?limit=2&offset=2").json["results"]
        self.assertEqual([r["speed_unit"] for r in older], ["WPM", "字符/分钟"])
        restarted = create_app(self.config).test_client()
        self.assertEqual(restarted.get("/api/history").json["total"], 4)
        self.assertTrue(restarted.get("/api/lessons").json["lessons"][1]["unlocked"])
        page = restarted.get("/history").text
        for label in ("中文", "English", "全文练习", "限时挑战", "指法闯关", "已通关", "继续练习", "字符/分钟", "WPM"):
            self.assertIn(label, page)
