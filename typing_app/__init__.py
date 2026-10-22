"""Local typing practice application."""

import os
import mimetypes
from pathlib import Path

from flask import Flask


def create_app(test_config=None):
    # Windows registry associations can otherwise label .mjs as text/plain.
    mimetypes.add_type("text/javascript", ".mjs")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.environ.get("TYPING_DATABASE", str(Path(app.instance_path) / "typing.sqlite3")),
        JSON_AS_ASCII=False,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    app.json.ensure_ascii = False
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    from . import db
    db.init_app(app)

    from .routes import bp
    app.register_blueprint(bp)
    from .api import bp as api_bp
    app.register_blueprint(api_bp)
    return app
