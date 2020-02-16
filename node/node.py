import json, platform, os, requests as rq, tempfile

from flask import abort, Flask, jsonify, request
from test_utils import get_installed_test_sets, uncompress_test_packages
from test_utils import TestSetCollection

app = Flask(__name__)

@app.route("/test_sets", methods=["GET"])
def list_installed_test_sets():
    return jsonify(installed)

@app.route("/test_sets", methods=["POST"])
def install_test_sets():
    global installed
    
    if not (request.files and 'packages' in request.files):
        abort(400)
    
    packages = request.files['packages']
    with tempfile.SpooledTemporaryFile() as f:
        packages.save(f)
        f.seek(0)
        uncompress_test_packages(f, TESTS_PATH)

    installed = get_installed_test_sets("test_sets")
    return jsonify(success=True)

@app.route("/report", methods=["GET"])
def execute_all_tests():
    tests = TestSetCollection(["test_sets"])
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
            f"{config['c2url']}/environments",
            json={
                'ip': config['ip'],
                'port': config['port'],
                'platform': get_platform_info()
            })
    except rq.exceptions.ConnectionError as e:
        return False      
    return resp.json()['success']

if __name__ == "__main__":
    SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
    TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")

    with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
        config = json.load(config_file)

    if not os.path.isdir(TESTS_PATH):
        os.mkdir(TESTS_PATH)
        open(os.path.join(TESTS_PATH, "__init__.py"), "w").close()

    if connect_to_c2():
        print("Connected successfuly!")
        installed = get_installed_test_sets("test_sets")
        app.run(host=config['ip'], port=config['port'], debug=True)
    else:
        print("Connection refused.")
        tests = TestSetCollection(["test_sets"])
        tests.run_all_tests()