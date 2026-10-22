import os

from . import create_app

create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
