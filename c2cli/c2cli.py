import click
import json
import os
import signatures
import requests

from base64 import b64encode
from hashlib import sha256
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
@click.option('--password', prompt=True, hide_input=True)
@click.argument("file_path")
def upload_compressed_packages(password: str, file_path: str):
    if not os.path.isfile(file_path):
        print("Given path does not exists or is not a file.")
    elif not file_path.endswith(".tar.gz"):
        print("Only .tar.gz extension allowed.")
    else:
        with open(file_path, "rb") as f:
            prepared = requests.Request(
                "PATCH",
                f"{C2_URL}/test_sets",
                files={'packages': f}).prepare()
        
        digest = b64encode(sha256(prepared.body).digest()).decode()
        prepared.headers['Digest'] = f"sha-256={digest}"

        headers = ['Digest']
        signature = signatures.new_signature(
            password.encode(),
            "PATCH",
            "/test_sets",
            signature_headers=headers,
            header_recoverer=lambda h: prepared.headers.get(h))
        prepared.headers['Authorization'] =\
            signatures.new_authorization_header("Client", signature, headers)

        try:
            resp = requests.Session().send(prepared)
        except requests.exceptions.ConnectionError:
            print("Connection refused.")
        else:
            if resp.status_code in {400, 401, 415}:
                print(resp.json()['error'])
            elif resp.status_code != 204:
                print("Unexpected response from Command and Control Sever.")

@main.command("remove")
@click.option('--password', prompt=True, hide_input=True)
@click.argument("packages", nargs=-1)
def remove_available_packages(password: str, packages: List[str]):
    key = password.encode()
    for pack in packages:
        signature = signatures.new_signature(
            key,
            "DELETE",
            f"/test_sets/{pack}")
        auth_content = signatures.new_authorization_header(
            "Client",
            signature)
        try:
            resp = requests.delete(
                f"{C2_URL}/test_sets/{pack}",
                headers={'Authorization': auth_content})
        except requests.exceptions.ConnectionError:
            print("Connection refused.")
        else:
            if resp.status_code in {401, 404}:
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
        for ip, ports in envs.items():
            for port, content in ports.items():
                print(f"{ip}:{port} {content['session_start']}")

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
        elif resp.status_code in {404, 502, 504}:
            print(resp.json()['error'])
        else:
            print("Unexpected response from Command and Control Sever.")

@main.command("install")
@click.option('--password', prompt=True, hide_input=True)
@click.argument("ip")
@click.argument("port")
@click.argument("packages", nargs=-1)
def install(password, ip, port, packages):
    """Install the given PACKAGES in the environment at IP:PORT."""
    prepared = requests.Request(
        "PATCH",
        f"{C2_URL}/environments/{ip}/{port}/installed",
        json=packages).prepare()

    digest = b64encode(sha256(prepared.body).digest()).decode()
    prepared.headers['Digest'] = f"sha-256={digest}"

    headers = ['Digest']
    signature = signatures.new_signature(
        password.encode(),
        "PATCH",
        f"/environments/{ip}/{port}/installed",
        signature_headers=headers,
        header_recoverer=lambda h: prepared.headers.get(h))
    prepared.headers['Authorization'] =\
        signatures.new_authorization_header("Client", signature, headers)
    
    try:
        resp = requests.Session().send(prepared)
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        if resp.status_code in {401, 404, 415, 500, 502, 504}:
            print(resp.json()['error'])
        elif resp.status_code != 204:
            print("Unexpected response from Command and Control Sever.")

@main.command("uninstall")
@click.option('--password', prompt=True, hide_input=True)
@click.argument("ip")
@click.argument("port")
@click.argument("packages", nargs=-1)
def uninstall(password, ip, port, packages):
    key = password.encode()
    for pack in packages:
        signature = signatures.new_signature(
            key,
            "DELETE",
            f"/environments/{ip}/{port}/installed/{pack}")
        auth_content = signatures.new_authorization_header(
            "Client",
            signature)
        try:
            resp = requests.delete(
                f"{C2_URL}/environments/{ip}/{port}/installed/{pack}",
                headers={'Authorization': auth_content})
        except requests.exceptions.ConnectionError:
            print("Connection refused.")
        else:
            if resp.status_code in {401, 404, 502, 504}:
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
        elif resp.status_code in {400, 404, 500, 502, 504}:
            print(resp.json()['error'])
        else:
            print("Unexpected response from Command and Control Sever.")

if __name__ == "__main__":
    main()