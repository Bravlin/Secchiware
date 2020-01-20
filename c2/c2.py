import requests as rq

from datetime import datetime
from flask import abort, Flask, jsonify, request

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

    return jsonify(success=True)
    
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

if __name__ == "__main__":
    app.run(debug=True)