import click, json, os, requests

from typing import List

@click.group()
@click.option("--c2-url", "-u", default="http://127.0.0.1:5000",
    help="URL of the Command and Control server.")
def main(c2_url):
    global C2_URL
    C2_URL = c2_url

@main.command("lsavailable")
def lsavialable():
    """Lists the test sets available at the C&C server."""
    try:
        resp = requests.get(f"{C2_URL}/test_sets")
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        else:
            print("Unexpected response from Command and Control Sever.")

@main.command("upload")
@click.argument("file_path")
def upload_compressed_packages(file_path: str):
    if not os.path.isfile(file_path):
        print("Given path does not exists or is not a file.")
    elif not file_path.endswith(".tar.gz"):
        print("Only .tar.gz extension allowed.")
    else:
        try:
            with open(file_path, "rb") as f:
                resp = requests.patch(
                    f"{C2_URL}/test_sets",
                    files={'packages': f})
        except requests.exceptions.ConnectionError:
            print("Connection refused.")
        else:
            if resp.status_code in [400, 415]:
                print(resp.json()['error'])
            elif resp.status_code != 204:
                print("Unexpected response from Command and Control Sever.")

@main.command("remove")
@click.argument("packages", nargs=-1)
def remove_available_packages(packages: List[str]):
    for pack in packages:
        try:
            resp = requests.delete(f"{C2_URL}/test_sets/{pack}")
        except requests.exceptions.ConnectionError:
            print("Connection refused.")
        else:
            if resp.status_code == 404:
                print(resp.json()['error'])
            elif resp.status_code != 204:
                print("Unexpected response from Command and Control Sever.")

@main.command("lsenv")
def lsenv():
    """Lists the environments currently registered at the C&C server."""
    try:
        resp = requests.get(f"{C2_URL}/environments")
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        envs = resp.json()
        for ip in envs:
            for port in envs[ip]:
                print(ip + ":" + port)

@main.command("info")
@click.argument("ip")
@click.argument("port")
def info(ip, port):
    try:
        resp = requests.get(f"{C2_URL}/environments/{ip}/{port}/info")
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        elif resp.status_code == 404:
            print(resp.json()['error'])
        else:
            print("Unexpected response from Command and Control Sever.")

@main.command("lsinstalled")
@click.argument("ip")
@click.argument("port")
def lsinstalled(ip, port):
    """
    Lists the currently instaled tests sets
    in the environment at IP:PORT.
    """
    try:
        resp = requests.get(f"{C2_URL}/environments/{ip}/{port}/installed")
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    except Exception:
        print(resp.json()['error'])
    else:
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        elif resp.status_code in [404, 502, 504]:
            print(resp.json()['error'])
        else:
            print("Unexpected response from Command and Control Sever.")

@main.command("install")
@click.argument("ip")
@click.argument("port")
@click.argument("packages", nargs=-1)
def install(ip, port, packages):
    """Install the given PACKAGES in the environment at IP:PORT."""
    try:
        resp = requests.patch(
            f"{C2_URL}/environments/{ip}/{port}/installed",
            json=packages)
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        if resp.status_code in [404, 415, 500, 502, 504]:
            print(resp.json()['error'])
        elif resp.status_code != 204:
            print("Unexpected response from Command and Control Sever.")

@main.command("uninstall")
@click.argument("ip")
@click.argument("port")
@click.argument("packages", nargs=-1)
def uninstall(ip, port, packages):
    for pack in packages:
        try:
            resp = requests.delete(
                f"{C2_URL}/environments/{ip}/{port}/installed/{pack}")
        except requests.exceptions.ConnectionError:
            print("Connection refused.")
        else:
            if resp.status_code in [404, 502, 504]:
               print(resp.json()['error'])
            elif resp.status_code != 204:
                print("Unexpected response from Command and Control Sever.")

@main.command("execute_tests")
@click.argument("ip")
@click.argument("port")
@click.option("--package", "-p", multiple=True)
@click.option("--module", "-m", multiple=True)
@click.option("--test_set", "-t", multiple=True)
def execute_tests(ip, port, package, module, test_set):
    query = ""
    if package:
        query += f"&packages={','.join(package)}"
    if module:
        query += f"&modules={','.join(module)}"
    if test_set:
        query += f"&test_sets={','.join(test_set)}"
    query = query.replace("&", "?", 1)

    try:
        resp = requests.get(
            f"{C2_URL}/environments/{ip}/{port}/report{query}")
    except requests.exceptions.ConnectionError:
            print("Connection refused.")
    else:
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        elif resp.status_code in [400, 404, 500, 502, 504]:
            print(resp.json()['error'])
        else:
            print("Unexpected response from Command and Control Sever.")

if __name__ == "__main__":
    main()