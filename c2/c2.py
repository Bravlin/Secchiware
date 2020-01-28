import json, os, requests as rq, tempfile

from datetime import datetime
from flask import abort, Flask, jsonify, request
from test_utils import get_installed_test_sets, compress_test_packages

def setup():
    global SCRIPT_PATH, TESTS_PATH
    global config, avialable, environments

    SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
    TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")

    with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
        config = json.load(config_file)

    if not os.path.isdir(TESTS_PATH):
        os.mkdir(TESTS_PATH)
        open(os.path.join(TESTS_PATH, "__init__.py"), "w").close()

    avialable = get_installed_test_sets("test_sets")
    environments = {}

app = Flask(__name__)

@app.route("/environments", methods=["GET"])
def list_environments():
    return jsonify(environments)

@app.route("/environments", methods=["POST"])
def add_environment():
    if not (request.json
            and 'ip' in request.json
            and 'port' in request.json):
        abort(400)

    ip = request.json['ip']
    port = request.json['port']

    if not ip in environments:
        environments[ip] = {}
    environments[ip][port] = {
        'session_start': datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
    }
    environments[ip][port]['info'] = request.json['platform']

    return jsonify(success=True)

@app.route("/environments/<ip>/<port>/info", methods=["GET"])
def get_environment_info(ip, port):
    if not (ip in environments and port in environments[ip]):
        abort(404)

    return environments[ip][port]['info']
    
@app.route("/environments/<ip>/<port>/installed", methods=["GET"])
def list_installed_test_sets(ip, port):
    if not (ip in environments and port in environments[ip]):
        abort(404)

    try:
        resp = rq.get("http://" + ip + ":" + port + "/test_sets")
    except rq.exceptions.ConnectionError as e:
        abort(500)
    return resp.json()

@app.route("/environments/<ip>/<port>/installed", methods=["POST"])
def install_packages(ip, port):
    if not (ip in environments and port in environments[ip]):
        abort(404)
    elif not (request.json and 'packages' in request.json):
        abort(400)

    packages = request.json['packages']
    try:
        with tempfile.SpooledTemporaryFile() as f:
            compress_test_packages(f, packages, TESTS_PATH)
            f.seek(0)
            resp = rq.post(
                "http://" + ip + ":" + port + "/test_sets",
                files={'packages': f})
    except rq.exceptions.ConnectionError as e:
        abort(500)
    return resp.json()

@app.route("/test_sets", methods=["GET"])
def list_available_test_sets():
    return jsonify(avialable)

if __name__ == "__main__":
    setup()
    app.run(host=config['ip'], port=config['port'], debug=True)