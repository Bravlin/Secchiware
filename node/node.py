import json, platform, os, requests as rq
import signal, shutil, sys, tempfile, test_utils

from custom_collections import OrderedListOfDict
from flask import abort, Flask, jsonify, request

app = Flask(__name__)

@app.route("/test_sets", methods=["GET"])
def list_installed_test_sets():
    return jsonify(installed.content)

@app.route("/test_sets", methods=["PATCH"])
def install_test_sets():
    global installed
    
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
    installed.batch_insert(new_info)
    return jsonify(success=True)

@app.route("/test_sets/<package>", methods=["DELETE"])
def delete_package(package):
    global installed

    package_path = os.path.join(TESTS_PATH, package)
    if not os.path.isdir(package_path):
        abort(404)

    shutil.rmtree(package_path)
    installed.delete(package)
    return jsonify(success=True)

@app.route("/report", methods=["GET"])
def execute_all_tests():
    tests = test_utils.TestSetCollection(["test_sets"])
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
            }
        )
    except rq.exceptions.ConnectionError:
        return False      
    return resp.json()['success']

def exit_gracefully(sig, frame):
    print("Exiting...")
    try:
        resp = rq.delete(
            f"{config['c2url']}/environments/{config['ip']}/{config['port']}")
        resp.raise_for_status()
    except rq.exceptions.ConnectionError:
        print("Could not contact Command and Control server before exiting.")
    except Exception as e:
        print(str(e))
    finally:
        sys.exit()

if __name__ == "__main__":
    SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
    TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")

    with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
        config = json.load(config_file)

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
        app.run(host=config['ip'], port=config['port'], debug=False)
    else:
        print("Connection refused.")
        tests = test_utils.TestSetCollection(["test_sets"])
        tests.run_all_tests()