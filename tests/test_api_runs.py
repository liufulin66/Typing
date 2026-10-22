from tests.support import AppCase


class RunApiTests(AppCase):
    def test_materials_and_courses(self):
        self.assertTrue(self.client.get("/api/articles?language=zh").json["articles"])
        self.assertTrue(self.client.get("/api/articles?language=en").json["articles"])
        self.assertEqual(len(self.client.get("/api/lessons").json["lessons"]), 16)

    def test_all_three_modes_can_start(self):
        bodies = [
            {"mode":"full", "language":"zh", "article_id":"zh-morning"},
            {"mode":"timed", "language":"en", "text":"ab", "duration_seconds":60},
            {"mode":"lesson", "lesson_id":"home-fj"},
        ]
        for body in bodies:
            with self.subTest(body=body):
                response = self.client.post("/api/runs", json=body)
                self.assertEqual(response.status_code, 201)
                self.assertTrue(response.json["run"]["target_text"])

    def test_invalid_source_and_duration(self):
        for body, status in [
            ({"mode":"full", "text":"  "}, 400),
            ({"mode":"full", "article_id":"missing"}, 404),
            ({"mode":"lesson", "lesson_id":"missing"}, 404),
            ({"mode":"lesson", "lesson_id":"home-dk"}, 403),
            ({"mode":"timed", "text":"a", "duration_seconds":12}, 400),
            ({"mode":"full", "language":"en", "article_id":"zh-morning"}, 400),
            ({"mode":"full", "text":"a", "article_id":"zh-morning"}, 400),
        ]:
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/api/runs", json=body).status_code, status)

    def test_custom_text_snapshot_and_non_object_json(self):
        response = self.client.post("/api/runs", json={"mode":"full", "text":"<b>hi</b>\r\nnext"})
        self.assertEqual(response.json["run"]["target_text"], "<b>hi</b>\nnext")
        self.assertEqual(self.client.post("/api/runs", json=[]).status_code, 400)
