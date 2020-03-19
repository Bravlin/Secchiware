import hmac
import json
import platform
import os
import requests as rq
import signal
import signatures
import shutil
import sys
import test_utils

from base64 import b64encode
from custom_collections import OrderedListOfDict
from flask import abort, Flask, jsonify, request, Response
from hashlib import sha256


def check_authorization_header(*mandatory_headers):
    if not 'Authorization' in request.headers:
        abort(401, description="No 'Authorization' header found in request.")
    try:
        is_valid = signatures.verify_authorization_header(
            request.headers['Authorization'],
            lambda keyID: config['C2_SECRET'] if keyID == "C2" else None,   
            lambda h: request.headers.get(h),
            request.method,
            request.path,
            request.query_string.decode(),
            mandatory_headers)
    except ValueError as e:
        abort(401, description=str(e))
    except Exception as e:
        abort(401, description="Invalid 'Authorization' header.")
    if not is_valid:
        abort(401, description="Invalid signature.")


app = Flask(__name__)


@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

@app.errorhandler(401)
def unauthorized(e):
    res = jsonify(error=str(e))
    res.status_code = 401
    res.headers['WWW-Authenticate'] = 'SECCHIWARE-HMAC-256 realm="Access to node"'
    return res

@app.errorhandler(404)
def not_found(e):
    return jsonify(error=str(e)), 404

@app.errorhandler(415)
def unsupported_media_type(e):
    return jsonify(error=str(e)), 415


@app.route("/test_sets", methods=["GET"])
def list_installed_test_sets():
    return jsonify(installed.content)

@app.route("/test_sets", methods=["PATCH"])
def install_test_sets():
    global installed
    
    if not request.mimetype == 'multipart/form-data':
        abort(415, description="Invalid request's content type")

    if not 'Digest' in request.headers:
        abort(400, description="'Digest' header mandatory.")
    if not request.headers['Digest'].startswith("sha-256="):
        abort(400, description="Digest algorithm should be sha-256.")
    digest = b64encode(sha256(request.get_data()).digest()).decode()
    if digest != request.headers['Digest'].split("=", 1)[1]:
        abort(400, description="Given digest does not match content.")

    check_authorization_header("Digest")

    if not (request.files and 'packages' in request.files):
        abort(400, description="Invalid request's content")
    try:
        new_packages = test_utils.uncompress_test_packages(
            request.files['packages'],
            TESTS_PATH)
    except Exception as e:
        print(str(e))
        abort(400, description="Invalid request's content")
    
    new_info = []
    for new_pack in new_packages:
        new_info.append(
            test_utils.get_installed_package(f"test_sets.{new_pack}"))
    installed.batch_insert(new_info)
    return Response(status=204, mimetype="application/json")

@app.route("/test_sets/<package>", methods=["DELETE"])
def delete_package(package):
    global installed

    check_authorization_header()

    package_path = os.path.join(TESTS_PATH, package)
    if not os.path.isdir(package_path):
        abort(404, description="Package not found")

    shutil.rmtree(package_path)
    installed.delete(package)
    return Response(status=204, mimetype="application/json")

@app.route("/report", methods=["GET"])
def execute_tests():
    def split_parameter(x):
        if isinstance(x, str):
            return x.split(",")
        raise ValueError

    if not request.args:
        tests = test_utils.TestSetCollection("test_sets")
    else:
        valid_keys = {'packages', 'modules', 'test_sets'}
        params = request.args
        if {*params.keys()} - valid_keys:
            abort(400, "Invalid query parameters")
        else:
            packages = params.get('packages', [], split_parameter)
            modules = params.get('modules', [], split_parameter)
            test_sets = params.get('test_sets', [], split_parameter)

        tests = test_utils.TestSetCollection(
            "test_sets",
            packages,
            modules,
            test_sets)
    
    return jsonify(tests.run_all_tests())

def get_platform_info():
    os_info = {}
    os_info['system'] = platform.system()
    os_info['release'] = platform.release()
    os_info['version'] = platform.version()

    hw_info = {}
    hw_info['machine'] = platform.machine()
    hw_info['processor'] = platform.processor()

    py_info = {}
    py_info['build'] = platform.python_build()
    py_info['compiler'] = platform.python_compiler()
    py_info['implementation'] = platform.python_implementation()
    py_info['version'] = platform.python_version()

    info = {}
    info['platform'] = platform.platform()
    info['node'] = platform.node()
    info['os'] = os_info
    info['hardware'] = hw_info
    info['python'] = py_info

    return info

def connect_to_c2():
    try:
        resp = rq.post(
            f"{config['C2_URL']}/environments",
            json={
                'ip': config['IP'],
                'port': config['PORT'],
                'platform': get_platform_info()
            }
        )
    except rq.exceptions.ConnectionError:
        return False      
    return resp.status_code == 204

def exit_gracefully(sig, frame):
    print("Exiting...")
    try:
        resp = rq.delete(
            f"{config['C2_URL']}/environments/{config['IP']}/{config['PORT']}")
        resp.raise_for_status()
    except rq.exceptions.ConnectionError:
        print("Could not contact Command and Control server before exiting.")
    except Exception:
        print(resp.json()['error'])
    finally:
        sys.exit()

if __name__ == "__main__":
    SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
    TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")

    with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
        config = json.load(config_file)
    config['C2_SECRET'] = config['C2_SECRET'].encode()

    if not os.path.isdir(TESTS_PATH):
        os.mkdir(TESTS_PATH)
        open(os.path.join(TESTS_PATH, "__init__.py"), "w").close()

    if connect_to_c2():
        signal.signal(signal.SIGTERM, exit_gracefully)
        signal.signal(signal.SIGINT, exit_gracefully)
        print("Connected successfuly!")
        installed = OrderedListOfDict('name', str)
        try:
            installed.content = test_utils.get_installed_test_sets("test_sets")
        except Exception as e:
            print(str(e))
        app.run(host=config['IP'], port=config['PORT'])
    else:
        print("Connection refused.\n\nExecuting installed tests...\n\n")
        tests = test_utils.TestSetCollection("test_sets")
        print(json.dumps(tests.run_all_tests()))