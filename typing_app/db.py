"""Request-scoped SQLite connections; startup never destroys user data."""

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS practice_runs (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL CHECK(mode IN ('full','timed','lesson')),
    language TEXT NOT NULL CHECK(language IN ('zh','en')),
    source_kind TEXT NOT NULL,
    source_id TEXT,
    title TEXT NOT NULL,
    target_text TEXT NOT NULL,
    course_version INTEGER,
    duration_seconds INTEGER,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS practice_results (
    run_id TEXT PRIMARY KEY REFERENCES practice_runs(id),
    attempted_chars INTEGER NOT NULL CHECK(attempted_chars > 0),
    correct_attempts INTEGER NOT NULL CHECK(correct_attempts >= 0 AND correct_attempts <= attempted_chars),
    final_correct_chars INTEGER NOT NULL,
    final_length INTEGER NOT NULL,
    elapsed_ms REAL NOT NULL CHECK(elapsed_ms > 0),
    accuracy REAL NOT NULL,
    speed REAL NOT NULL,
    speed_unit TEXT NOT NULL,
    passed INTEGER,
    finished_at TEXT NOT NULL,
    fingerprint TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS results_finished ON practice_results(finished_at DESC);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=3)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    get_db().executescript(SCHEMA)


def init_app(app):
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
