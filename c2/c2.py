import json, os, requests as rq, shutil, tempfile, test_utils

from custom_collections import OrderedListOfDict
from datetime import datetime
from flask import abort, Flask, jsonify, request, Response
from functools import wraps

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")

with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
    config = json.load(config_file)

if not os.path.isdir(TESTS_PATH):
    os.mkdir(TESTS_PATH)
    open(os.path.join(TESTS_PATH, "__init__.py"), "w").close()

available = OrderedListOfDict('name', str)
try:
    available.content = test_utils.get_installed_test_sets("test_sets")
except Exception as e:
    print(str(e))
environments = {}

app = Flask(__name__)


def check_registered(ip, port):
    if not (ip in environments and port in environments[ip]):
        abort(404,
            description=f"No environment registered for {ip}:{port}")

def check_is_json():
    if not request.is_json:
        abort(415, description="Content Type is not application/json")


def client_route(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    return wrapper


@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify(error=str(e)), 404

@app.errorhandler(415)
def unsupported_media_type(e):
    return jsonify(error=str(e)), 415

@app.errorhandler(504)
def gateway_timeout(e):
    return jsonify(error=str(e)), 504


@app.route("/", methods=["GET"])
@client_route
def is_up():
    return jsonify(success=True)

@app.route("/environments", methods=["GET"])
@client_route
def list_environments():
    return jsonify(environments)

@app.route("/environments", methods=["POST"])
def add_environment():
    check_is_json()
    if not ('ip' in request.json
            and 'port' in request.json
            and 'platform' in request.json):
        abort(400, description="One or more keys missing in request's body")

    ip = request.json['ip']
    port = request.json['port']

    if not ip in environments:
        environments[ip] = {}
    environments[ip][port] = {
        'session_start': datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
    }
    environments[ip][port]['info'] = request.json['platform']

    return Response(status=204, mimetype="application/json")

@app.route("/environments/<ip>/<port>", methods=["DELETE"])
def remove_environment(ip, port):
    global environments

    check_registered(ip, port)
    
    del environments[ip][port]
    if not environments[ip]:
        del environments[ip]
    
    return Response(status=204, mimetype="application/json")

@app.route("/environments/<ip>/<port>/info", methods=["GET"])
@client_route
def get_environment_info(ip, port):
    check_registered(ip, port)
    return jsonify(environments[ip][port]['info'])
    
@app.route("/environments/<ip>/<port>/installed", methods=["GET"])
@client_route
def list_installed_test_sets(ip, port):
    check_registered(ip, port)

    try:
        resp = rq.get(f"http://{ip}:{port}/test_sets")
    except rq.exceptions.ConnectionError:
        abort(504,
            description="The requested environment could not be reached")

    return jsonify(resp.json())

@app.route("/environments/<ip>/<port>/installed", methods=["PATCH"])
@client_route
def install_packages(ip, port):
    check_registered(ip, port)
    check_is_json()

    packages = request.json
    try:
        with tempfile.SpooledTemporaryFile() as f:
            test_utils.compress_test_packages(f, packages, TESTS_PATH)
            f.seek(0)
            rq.patch(
                f"http://{ip}:{port}/test_sets",
                files={'packages': f})
    except rq.exceptions.ConnectionError:
        abort(504,
            description="The requested environment could not be reached")

    return Response(status=204, mimetype="application/json")

@app.route("/environments/<ip>/<port>/installed/<package>", methods=["DELETE"])
@client_route
def delete_installed_package(ip, port, package):
    check_registered(ip, port)

    try:
        resp = rq.delete(f"http://{ip}:{port}/test_sets/{package}")
    except rq.exceptions.ConnectionError:
        abort(504,
            description="The requested environment could not be reached")

    if resp.status_code == 204:
        return Response(status=204, mimetype="application/json")
    elif resp.status_code == 404:
        return abort(404, description=f"'{package}' not found at {ip}:{port}")

@app.route("/environments/<ip>/<port>/report", methods=["GET"])
@client_route
def execute_tests(ip, port):
    check_registered(ip, port)
    
    url = f"http://{ip}:{port}/report"
    if request.args:
        valid_keys = {'packages', 'modules', 'test_sets'}
        if set(request.args.keys()) - valid_keys:
            abort(400, "One or more invalid keys found in query parameters")
        else:
            url += f"?{request.query_string.decode()}"

    try:
        resp = rq.get(url)
    except rq.exceptions.ConnectionError:
        abort(504,
            description="The requested environment could not be reached")

    return jsonify(resp.json())

@app.route("/test_sets", methods=["GET"])
@client_route
def list_available_test_sets():
    return jsonify(available.content)

@app.route("/test_sets", methods=["PATCH"])
@client_route
def upload_test_sets():
    global available

    if not request.mimetype == 'multipart/form-data':
        abort(415, description="Invalid request's content type")
    if not (request.files and 'packages' in request.files):
        abort(400, description="'packages' key not found in request's body")
    
    packages = request.files['packages']
    with tempfile.SpooledTemporaryFile() as f:
        packages.save(f)
        f.seek(0)
        try:
            new_packages = test_utils.uncompress_test_packages(f, TESTS_PATH)
        except Exception as e:
            print(str(e))
            abort(400, description="Invalid file content")

    new_info = []
    for new_pack in new_packages:
        new_info.append(
            test_utils.get_installed_package(f"test_sets.{new_pack}"))
    available.batch_insert(new_info)
    return Response(status=204, mimetype="application/json")

@app.route("/test_sets/<package>", methods=["DELETE"])
@client_route
def delete_package(package):
    global available

    package_path = os.path.join(TESTS_PATH, package)
    if not os.path.isdir(package_path):
        abort(404, description=f"Package '{package}' not found")

    shutil.rmtree(package_path)
    available.delete(package)
    return Response(status=204, mimetype="application/json")


if __name__ == "__main__":
    app.run(host=config['IP'], port=config['PORT'], debug=True)