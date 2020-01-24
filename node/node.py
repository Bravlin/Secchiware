import json, platform, os, requests as rq

from flask import Flask, jsonify, request
from test_utils import get_installed_test_sets

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")

with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
    config = json.load(config_file)

app = Flask(__name__)

@app.route("/test_sets", methods=["GET"])
def list_installed_test_sets():
    return jsonify(installed)

@app.route("/test_sets", methods=["POST"])
def install_test_sets():
    pass

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
            config['c2url'] + "/environments",
            json={
                "ip": config['ip'],
                "port": config['port'],
                "platform": get_platform_info()
            })
        if resp.json()['success']:
            print("Connected successfuly!")
    except rq.exceptions.ConnectionError as e:
        print("Connection refused.")

if __name__ == "__main__":
    connect_to_c2()
    if not os.path.isdir(TESTS_PATH):
        os.mkdir(TESTS_PATH)
        open(os.path.join(TESTS_PATH, "__init__.py"), "w").close()
    installed = get_installed_test_sets("test_sets")
    app.run(host=config['ip'], port=config['port'], debug=True)