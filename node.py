import json, requests

from flask import Flask, jsonify
from test_utils import get_installed_test_sets

with open("config.json") as config_file:
    config = json.load(config_file)

installed = get_installed_test_sets()

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
    app.run(config['ip'], config['port'], True)