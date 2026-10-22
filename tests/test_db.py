import sqlite3

from typing_app import create_app
from typing_app.db import get_db, init_db
from tests.support import AppCase


class DatabaseTests(AppCase):
    def test_initialization_and_restart_preserve_rows(self):
        with self.app.app_context():
            self.insert_run()
            init_db()
        restarted = create_app(self.config)
        with restarted.app_context():
            self.assertEqual(get_db().execute("SELECT count(*) FROM practice_runs").fetchone()[0], 1)

    def test_connection_closes_at_context_exit(self):
        with self.app.app_context():
            connection = get_db()
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")

    def test_run_ids_are_unique(self):
        with self.app.app_context():
            self.insert_run()
            with self.assertRaises(sqlite3.IntegrityError):
                self.insert_run()
