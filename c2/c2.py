import json, os, requests as rq

from datetime import datetime
from flask import abort, Flask, jsonify, request
from test_utils import get_installed_test_sets

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")

with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
    config = json.load(config_file)

environments = {}

app = Flask(__name__)

@app.route("/environments", methods=["GET"])
def list_environments():
    return jsonify(environments)

@app.route("/environments", methods=["POST"])
def add_environment():
    if (not request.json
            or not 'ip' in request.json
            or not 'port' in request.json):
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
        abort(400)
    else:
        return environments[ip][port]['info']
    
@app.route("/environments/<ip>/<port>/installed")
def list_installed_test_sets(ip, port):
    if not (ip in environments and port in environments[ip]):
        abort(400)
    else:
        try:
            resp = rq.get("http://" + ip + ":" + port + "/test_sets")
            return resp.json()
        except rq.exceptions.ConnectionError as e:
            abort(500)

@app.route("/test_sets", methods=["GET"])
def list_available_test_sets():
    return jsonify(avialable)

if __name__ == "__main__":
    if not os.path.isdir(TESTS_PATH):
        os.mkdir(TESTS_PATH)
        open(os.path.join(TESTS_PATH, "__init__.py"), "w").close()
    avialable = get_installed_test_sets("test_sets")
    app.run(host=config['ip'], port=config['port'], debug=True)