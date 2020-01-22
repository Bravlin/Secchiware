import json, os, requests

from flask import Flask, jsonify
from test_utils import get_installed_test_sets

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
TESTS_PATH = os.path.join(SCRIPT_PATH, "test_sets")

with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as config_file:
    config = json.load(config_file)

app = Flask(__name__)

@app.route("/test_sets", methods=["GET"])
def list_installed_test_sets():
    return jsonify(installed)

def connect_to_c2():
    try:
        resp = requests.post(
            config['c2url'] + "/environments",
            json={"ip": config['ip'], "port": config['port']})
        if resp.json()['success']:
            print("Connected successfuly!")
    except requests.exceptions.ConnectionError as e:
        print("Connection refused.")

if __name__ == "__main__":
    connect_to_c2()
    if not os.path.isdir(TESTS_PATH):
        os.mkdir(TESTS_PATH)
        open(os.path.join(TESTS_PATH, "__init__.py"), "w").close()
    installed = get_installed_test_sets("test_sets")
    app.run(config['ip'], config['port'], True)