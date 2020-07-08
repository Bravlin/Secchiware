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
import time

from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor
from flask import abort, Flask, jsonify, request, Response
from hashlib import sha256


################################ Globals #####################################

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")

with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
    config = json.load(config_file)
config['C2_SECRET'] = config['C2_SECRET'].encode()


######################## Request check functions #############################

def check_authorization_header(*mandatory_headers) -> None:
    """Verifies that the incoming request fulfills the SECCHIWARE-HMAC-256.
    authorization scheme.
    
    The "Authorization" header must be present in the request, it must have
    the proper format and the informed signature must correspond to the
    request's content.

    Parameters
    ----------
    mandatory_headers: *Tuple[str], optional
        A variable amount of header keys that must be present in the incoming
        request.

    Abort
    -----
    401
        The request does not fulfill the described criteria.
    """

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

######################## Flask app initialization ############################

app = Flask(__name__)


############################# Error handlers #################################

@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

@app.errorhandler(401)
def unauthorized(e):
    res = jsonify(error=str(e))
    res.status_code = 401
    res.headers['WWW-Authenticate'] = (
        'SECCHIWARE-HMAC-256 realm="Access to node"')
    return res

@app.errorhandler(404)
def not_found(e):
    return jsonify(error=str(e)), 404

@app.errorhandler(415)
def unsupported_media_type(e):
    return jsonify(error=str(e)), 415


############################### Endpoints ####################################

@app.route("/", methods=["DELETE"])
def stop_node():
    def exit_by_c2_petition():
        time.sleep(1)
        print("Exiting by C2 petition")
        os._exit(0)

    check_authorization_header()

    ThreadPoolExecutor(max_workers=1).submit(exit_by_c2_petition)

    return Response(status=204, mimetype="application/json")

@app.route("/reports", methods=["GET"])
def execute_tests():
    def split_parameter(x):
        if isinstance(x, str):
            return x.split(",")
        raise ValueError

    if not request.args:
        tests = test_utils.TestSetCollection("test_sets")
    else:
        valid_keys = {'packages', 'modules', 'test_sets', 'tests'}
        params = request.args
        if {*params.keys()} - valid_keys:
            abort(400, "Invalid query parameters")
        else:
            packages = params.get('packages', [], split_parameter)
            modules = params.get('modules', [], split_parameter)
            test_sets = params.get('test_sets', [], split_parameter)
            tests = params.get('tests', [], split_parameter)

        try:
            tests = test_utils.TestSetCollection(
                "test_sets",
                packages,
                modules,
                test_sets,
                tests)
        except ModuleNotFoundError:
            abort(404, description="A specified entity was not found")
    
    return jsonify(tests.run_all())

@app.route("/test_sets", methods=["GET"])
def list_installed_test_sets():
    return jsonify(test_utils.get_installed_test_sets("test_sets"))

@app.route("/test_sets", methods=["PATCH"])
def install_test_sets():
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
    
    for new_pack in new_packages:
        # If it is a new version, the next sentence removes the old one.
        test_utils.clean_package(f"test_sets.{new_pack}")

    return Response(status=204, mimetype="application/json")

@app.route("/test_sets/<package>", methods=["DELETE"])
def delete_package(package):
    check_authorization_header()

    package_path = os.path.join(TESTS_PATH, package)
    if not os.path.isdir(package_path):
        abort(404, description="Package not found")

    shutil.rmtree(package_path)
    test_utils.clean_package(package)
    return Response(status=204, mimetype="application/json")


########################## Additional functions ##############################

def get_platform_info() -> dict:
    """Recovers information about the current platform's operating system, its
    processor and its Python interpreter.

    It uses the module platform to obtain that information.

    The returned dictionary contains the following structure:

    1. 'platform':
        A summary of the current platform.
    2. 'node':
        The name of the host machine.
    3. 'os':
        Information about the operating system. It contains the following
        keys:
            3.1. 'system':
                The general name of the operating system. Examples: "Linux",
                "Windows".
            3.2. 'release':
                The general number of release of the operating system.
            3.3. 'version':
                The specific release version of the operating system.
    4. 'hardware':
        Information about the processor. It contains the following keys:
            4.1. 'machine':
                The general architecture of the processor.
            4.2. 'processor:
                The name of the processor. Not all platforms provide it. In
                some cases it may contain the same value as 'machine'.
    5. 'python':
        Information about the Python interpreter. It contains the following
        keys:
            5.1. 'build':
                A tuple of two strings; the first one is the build's number
                and the second one is its date.
            5.2. 'compiler':
                The compiler used to build the interpreter.
            5.3. 'implementation':
                The specific implementation of the interpreter. Example:
                "CPython".
            5.4. 'version': The used version of the language.

    Returns
    -------
    dict
        A dictionary containing the structure previously described.
    """

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

def connect_to_c2() -> bool:
    """Tries to make contact with the C&C server.

    Returns
    -------
    bool
        Wheter the C&C was sucessfully reached and it returned a status code
        of 204.
    """

    prepared = rq.Request(
        "POST",
        f"{config['C2_URL']}/environments",
        json={
            'ip': config.get('NAT_IP', config['IP']),
            'port': config.get('NAT_PORT', config['PORT']),
            'platform_info': get_platform_info()
        }).prepare()

    digest = b64encode(sha256(prepared.body).digest()).decode()
    prepared.headers['Digest'] = f"sha-256={digest}"

    headers = ['Digest']
    signature = signatures.new_signature(
        config['C2_SECRET'],
        "POST",
        "/environments",
        signature_headers=headers,
        header_recoverer=lambda h: prepared.headers.get(h))
    prepared.headers['Authorization'] = (
        signatures.new_authorization_header("Node", signature, headers))

    try:
        resp = rq.Session().send(prepared)
    except rq.exceptions.ConnectionError:
        return False

    return resp.status_code == 204

def exit_gracefully(sig, frame) -> None:
    """Signal handler that tries to warn the C&C server that the node is
    shutting down before it does so."""

    print("Exiting...")

    ip = config.get('NAT_IP', config['IP'])
    port = config.get('NAT_PORT', config['PORT'])

    signature = signatures.new_signature(
        config['C2_SECRET'],
        "DELETE",
        f"/environments/{ip}/{port}")
    authorization_content = (
        signatures.new_authorization_header("Node", signature))

    try:
        resp = rq.delete(
            f"{config['C2_URL']}/environments/{ip}/{port}",
            headers={'Authorization': authorization_content})
        resp.raise_for_status()
    except rq.exceptions.ConnectionError:
        print("Could not contact Command and Control server before exiting.")
    except Exception:
        print(resp.json()['error'])
    finally:
        sys.exit()


############################### Main program #################################

if not os.path.isdir(TESTS_PATH):
    os.mkdir(TESTS_PATH)
    open(os.path.join(TESTS_PATH, "__init__.py"), "w").close()

if connect_to_c2():
    print("Connected successfuly!")

    signal.signal(signal.SIGTERM, exit_gracefully)
    signal.signal(signal.SIGINT, exit_gracefully)

    if __name__ == "__main__":
        app.run(host=config['IP'], port=config['PORT'], threaded=False)
else:
    print("Connection refused.\n\nExecuting installed tests...\n\n")
    tests = test_utils.TestSetCollection("test_sets")
    print(json.dumps(tests.run_all(), indent=2))