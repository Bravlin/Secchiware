from datetime import datetime
from flask import abort, Flask, jsonify, request

app = Flask(__name__)

environments = {}

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
    
