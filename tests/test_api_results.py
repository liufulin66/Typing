from typing_app.db import get_db
from tests.support import AppCase


class ResultApiTests(AppCase):
    def start(self):
        return self.client.post("/api/runs", json={"mode":"lesson", "lesson_id":"home-fj"}).json["run"]

    def score(self, run, **changes):
        length = len(run["target_text"])
        return {"final_input":run["target_text"], "attempted_chars":length,
                "correct_attempts":length, "elapsed_ms":60000, **changes}

    def test_save_retry_and_conflict(self):
        run = self.start()
        url = f'/api/runs/{run["id"]}/result'
        data = self.score(run)
        first = self.client.post(url, json=data)
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.json["result"]["passed"])
        self.assertTrue(first.json["progress"]["lessons"][1]["unlocked"])
        repeated = self.client.post(url, json=data)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(first.json["result"], repeated.json["result"])
        self.assertEqual(self.client.post(url, json=data | {"elapsed_ms":61000}).status_code, 409)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT count(*) FROM practice_results").fetchone()[0], 1)

    def test_client_passed_field_does_not_unlock(self):
        run = self.start()
        response = self.client.post(f'/api/runs/{run["id"]}/result',
                                    json=self.score(run, correct_attempts=0, passed=True))
        self.assertFalse(response.json["result"]["passed"])
        self.assertFalse(response.json["progress"]["lessons"][1]["unlocked"])

    def test_database_failure_leaves_no_score_and_retry_succeeds(self):
        run = self.start()
        url = f'/api/runs/{run["id"]}/result'
        with self.app.app_context():
            connection = get_db()
            connection.execute("PRAGMA query_only=ON")
            self.assertEqual(self.client.post(url, json=self.score(run)).status_code, 503)
            self.assertEqual(connection.execute("SELECT count(*) FROM practice_results").fetchone()[0], 0)
            connection.execute("PRAGMA query_only=OFF")
        self.assertFalse(self.client.get("/api/lessons").json["lessons"][1]["unlocked"])
        self.assertEqual(self.client.post(url, json=self.score(run)).status_code, 201)

    def test_partial_invalid_and_unknown_results(self):
        run = self.start()
        url = f'/api/runs/{run["id"]}/result'
        self.assertEqual(self.client.post(url, json=self.score(run, final_input="f")).status_code, 400)
        self.assertEqual(self.client.post(url, json=self.score(run, correct_attempts=-1)).status_code, 400)
        self.assertEqual(self.client.post("/api/runs/missing/result", json={}).status_code, 404)
