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
                print(
                    f"\n{ip}:{port}\nsession: {content['session_id']}\n"\
                    f"start: {content['session_start']}\n")

@main.command("sessions_search")
@click.option("--session_id", multiple=True)
@click.option("--start_from")
@click.option("--start_to")
@click.option("--end_from")
@click.option("--end_to")
@click.option("--ip", multiple=True)
@click.option("--port", multiple=True)
@click.option("--system", multiple=True)
@click.option("--order_by")
@click.option("--arrange")
@click.option("--limit")
def search_sessions(
        session_id,
        start_from,
        start_to,
        end_from,
        end_to,
        ip,
        port,
        system,
        order_by,
        arrange,
        limit):
    query = ""
    if session_id:
        query = f"{query}&ids={','.join(session_id)}"
    if start_from:
        query = f"{query}&start_from={start_from}"
    if start_to:
        query = f"{query}&start_to={start_to}"
    if end_from:
        query = f"{query}&end_from={end_from}"
    if end_to:
        query = f"{query}&end_to={end_to}"
    if ip:
        query = f"{query}&ips={','.join(ip)}"
    if port:
        query = f"{query}&ports={','.join(port)}"
    if system:
        query = f"{query}&systems={','.join(system)}"
    if order_by:
        query = f"{query}&order_by={order_by}"
    if arrange:
        query = f"{query}&arrange={arrange}"
    if limit:
        query = f"{query}&limit={limit}"
    query = query.replace("&", "?", 1)

    try:
        resp = requests.get(f"{C2_URL}/sessions{query}")
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        elif resp.status_code == 400:
            print(resp.json()['error'])
        else:
            print("Unexpected response from Command and Control Sever.")

@main.command("session_get")
@click.argument("session")
def get_session(session):
    try:
        resp = requests.get(f"{C2_URL}/sessions/{session}")
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        elif resp.status_code == 404:
            print(resp.json()['error'])
        else:
            print("Unexpected response from Command and Control Sever.")

@main.command("session_delete")
@click.option('--password', prompt=True, hide_input=True)
@click.argument("sessions", nargs=-1)
def delete_sessions(password, sessions):
    key = password.encode()
    for session in sessions:
        signature = signatures.new_signature(
            key,
            "DELETE",
            f"/sessions/{session}")
        auth_content = signatures.new_authorization_header(
            "Client",
            signature)
        try:
            resp = requests.delete(
                f"{C2_URL}/sessions/{session}",
                headers={'Authorization': auth_content})
        except requests.exceptions.ConnectionError:
            print("Connection refused.")
        else:
            if resp.status_code in {400, 401, 404}:
                print(resp.json()['error'])
            elif resp.status_code != 204:
                print("Unexpected response from Command and Control Sever.")

@main.command("executions_search")
@click.option("--execution_id", multiple=True)
@click.option("--session", multiple=True)
@click.option("--registered_from")
@click.option("--registered_to")
@click.option("--order_by")
@click.option("--arrange")
@click.option("--limit")
def search_executions(
        execution_id,
        session,
        registered_from,
        registered_to,
        order_by,
        arrange,
        limit):
    query = ""
    if execution_id:
        query = f"{query}&ids={','.join(execution_id)}"
    if session:
        query = f"{query}&sessions={','.join(session)}"
    if registered_from:
        query = f"{query}&registered_from={registered_from}"
    if registered_to:
        query = f"{query}&registered_to={registered_to}"
    if order_by:
        query = f"{query}&order_by={order_by}"
    if arrange:
        query = f"{query}&arrange={arrange}"
    if limit:
        query = f"{query}&limit={limit}"
    query = query.replace("&", "?", 1)

    try:
        resp = requests.get(f"{C2_URL}/executions{query}")
    except requests.exceptions.ConnectionError:
        print("Connection refused.")
    else:
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        elif resp.status_code == 400:
            print(resp.json()['error'])
        else:
            print("Unexpected response from Command and Control Sever.")

@main.command("execution_delete")
@click.option('--password', prompt=True, hide_input=True)
@click.argument("executions", nargs=-1)
def delete_executions(password, executions):
    key = password.encode()
    for execution in executions:
        signature = signatures.new_signature(
            key,
            "DELETE",
            f"/executions/{execution}")
        auth_content = signatures.new_authorization_header(
            "Client",
            signature)
        try:
            resp = requests.delete(
                f"{C2_URL}/executions/{execution}",
                headers={'Authorization': auth_content})
        except requests.exceptions.ConnectionError:
            print("Connection refused.")
        else:
            if resp.status_code in {401, 404}:
                print(resp.json()['error'])
            elif resp.status_code != 204:
                print("Unexpected response from Command and Control Sever.")

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
        if resp.status_code in {400, 401, 404, 415, 500, 502, 504}:
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

@main.command("reports_get")
@click.argument("ip")
@click.argument("port")
@click.option("--package", "-p", multiple=True)
@click.option("--module", "-m", multiple=True)
@click.option("--test_set", "-t", multiple=True)
def get_reports(ip, port, package, module, test_set):
    query = ""
    if package:
        query = f"{query}&packages={','.join(package)}"
    if module:
        query = f"{query}&modules={','.join(module)}"
    if test_set:
        query = f"{query}&test_sets={','.join(test_set)}"
    query = query.replace("&", "?", 1)

    try:
        resp = requests.get(
            f"{C2_URL}/environments/{ip}/{port}/reports{query}")
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