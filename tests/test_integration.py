from typing_app import create_app
from tests.support import AppCase


class RestartJourneyTests(AppCase):
    def finish_lesson(self, client, lesson_id, correct=True):
        created = client.post("/api/runs", json={"mode":"lesson", "lesson_id":lesson_id})
        self.assertEqual(created.status_code, 201)
        run = created.json["run"]
        payload = {"final_input":run["target_text"], "attempted_chars":len(run["target_text"]),
                   "correct_attempts":len(run["target_text"]) if correct else 0, "elapsed_ms":60000}
        url = f'/api/runs/{run["id"]}/result'
        self.assertEqual(client.post(url, json=payload).status_code, 201)
        self.assertEqual(client.post(url, json=payload).status_code, 200)

    def test_complete_retry_restart_resume_and_failed_review(self):
        self.finish_lesson(self.client, "home-fj")
        self.finish_lesson(self.client, "home-dk")
        restarted = create_app(self.config).test_client()
        progress = restarted.get("/api/lessons").json
        self.assertEqual(progress["completed"], 2)
        self.assertEqual(progress["next_lesson"]["id"], "home-sl")
        self.assertTrue(progress["lessons"][2]["unlocked"])
        self.assertEqual(restarted.get("/api/history").json["total"], 2)
        self.finish_lesson(restarted, "home-fj", correct=False)
        after = restarted.get("/api/lessons").json
        self.assertEqual(after["completed"], 2)
        self.assertTrue(after["lessons"][0]["passed"])
        self.assertTrue(after["lessons"][2]["unlocked"])
        self.assertEqual(restarted.get("/api/history").json["total"], 3)
