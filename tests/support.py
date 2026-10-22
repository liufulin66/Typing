import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from typing_app import create_app
from typing_app.db import get_db


class AppCase(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(__file__).resolve().parents[1] / ".tmp" / "tests"
        self.test_dir = self.temp_root / uuid4().hex
        self.test_dir.mkdir(parents=True)
        self.config = {"TESTING": True, "DATABASE": str(self.test_dir / "test.sqlite3")}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def tearDown(self):
        # Only recursively remove the disposable directory created by this test.
        target = self.test_dir.resolve()
        if target.parent != self.temp_root.resolve():
            raise RuntimeError("Refusing to clean outside the test workspace")
        shutil.rmtree(target)

    def insert_run(self, run_id="run-1", mode="full", source_id=None):
        get_db().execute(
            "INSERT INTO practice_runs VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, mode, "en", "lesson" if mode == "lesson" else "custom", source_id,
             "Test", "fj", 1 if mode == "lesson" else None, None, "2026-10-21T00:00:00+00:00"),
        )
        get_db().commit()

    def insert_score(self, run_id, passed=True, finished_at="2026-10-21T00:00:00+00:00"):
        get_db().execute(
            "INSERT INTO practice_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, 20, 19 if passed else 10, 2, 2, 60000, 95 if passed else 50,
             0.4, "WPM", int(passed), finished_at, run_id),
        )
        get_db().commit()
