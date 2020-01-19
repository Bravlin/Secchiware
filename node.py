import json, requests

with open("config.json") as config_file:
    config = json.load(config_file)

resp = requests.post(
    config['c2url'] + "/environments",
    json={"ip": config['ip'], "port": config['port']})
if resp.json()['success']:
    print("Connected successfuly!")