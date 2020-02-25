import json, os, requests as rq, shutil, tempfile, test_utils

from custom_collections import OrderedListOfDict
from datetime import datetime
from flask import abort, Flask, jsonify, request
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

def client_route(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    return wrapper

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

@app.route("/environments/<ip>/<port>", methods=["DELETE"])
def remove_environment(ip, port):
    global environments

    if not (ip in environments and port in environments[ip]):
        abort(404)
    
    del environments[ip][port]
    if not environments[ip]:
        del environments[ip]
    
    return jsonify(success=True)

@app.route("/environments/<ip>/<port>/info", methods=["GET"])
@client_route
def get_environment_info(ip, port):
    if not (ip in environments and port in environments[ip]):
        abort(404)

    return jsonify(environments[ip][port]['info'])
    
@app.route("/environments/<ip>/<port>/installed", methods=["GET"])
@client_route
def list_installed_test_sets(ip, port):
    if not (ip in environments and port in environments[ip]):
        abort(404)

    try:
        resp = rq.get(f"http://{ip}:{port}/test_sets")
    except rq.exceptions.ConnectionError:
        abort(500)

    return jsonify(resp.json())

@app.route("/environments/<ip>/<port>/installed", methods=["PATCH"])
@client_route
def install_packages(ip, port):
    if not (ip in environments and port in environments[ip]):
        abort(404)
    elif not (request.json and 'packages' in request.json):
        abort(400)

    packages = request.json['packages']
    try:
        with tempfile.SpooledTemporaryFile() as f:
            test_utils.compress_test_packages(f, packages, TESTS_PATH)
            f.seek(0)
            rq.patch(
                f"http://{ip}:{port}/test_sets",
                files={'packages': f}
            )
    except rq.exceptions.ConnectionError:
        abort(500)

    return app.response_class(status=204, mimetype="application/json")

@app.route("/environments/<ip>/<port>/installed/<package>", methods=["DELETE"])
@client_route
def delete_installed_package(ip, port, package):
    if not (ip in environments and port in environments[ip]):
        abort(404)

    try:
        rq.delete(f"http://{ip}:{port}/test_sets/{package}")
    except rq.exceptions.ConnectionError:
        abort(500)

    return app.response_class(status=204, mimetype="application/json")

@app.route("/environments/<ip>/<port>/report", methods=["GET"])
@client_route
def execute_tests(ip, port):
    if not (ip in environments and port in environments[ip]):
        abort(404)
    
    url = f"http://{ip}:{port}/report"
    if request.args:
        valid_keys = {'packages', 'modules', 'test_sets'}
        if set(request.args.keys()) - valid_keys:
            abort(400)
        else:
            url += f"?{request.query_string.decode()}"

    try:
        resp = rq.get(url)
    except rq.exceptions.ConnectionError:
        abort(500)
    return jsonify(resp.json())

@app.route("/test_sets", methods=["GET"])
@client_route
def list_available_test_sets():
    return jsonify(available.content)

@app.route("/test_sets", methods=["PATCH"])
@client_route
def upload_test_sets():
    global available

    if not (request.files and 'packages' in request.files):
        abort(400)
    
    packages = request.files['packages']
    with tempfile.SpooledTemporaryFile() as f:
        packages.save(f)
        f.seek(0)
        try:
            new_packages = test_utils.uncompress_test_packages(f, TESTS_PATH)
        except Exception as e:
            print(str(e))
            abort(400)

    new_info = []
    for new_pack in new_packages:
        new_info.append(
            test_utils.get_installed_package(f"test_sets.{new_pack}"))
    available.batch_insert(new_info)
    return jsonify(success=True)

@app.route("/test_sets/<package>", methods=["DELETE"])
@client_route
def delete_package(package):
    global available

    package_path = os.path.join(TESTS_PATH, package)
    if not os.path.isdir(package_path):
        abort(404)

    shutil.rmtree(package_path)
    available.delete(package)
    return jsonify(success=True)


if __name__ == "__main__":
    app.run(host=config['IP'], port=config['PORT'], debug=True)