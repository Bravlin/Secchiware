import os
import sys

from secchiware_c2 import database, error_handlers, routes, tasks
from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_json("config.json")
    app.config['NODE_SECRET'] = app.config['NODE_SECRET'].encode("utf-8")
    app.config['CLIENT_SECRET'] = app.config['CLIENT_SECRET'].encode("utf-8")
    app.config['DATABASE'] = os.path.join(app.instance_path, "secchiware.db")
    app.config['TESTS_PATH'] = os.path.join(app.instance_path, "test_sets")

    sys.path.append(app.instance_path)

    database.init_app(app)
    tasks.init_app(app)

    app.register_blueprint(error_handlers.bp)
    app.register_blueprint(routes.bp)

    return app