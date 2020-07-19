import click
import json
import os
import signatures
import requests

from base64 import b64encode
from hashlib import sha256
from typing import List


@click.group()
@click.option(
    "--c2-url",
    "-u",
    type=str,
    default="http://127.0.0.1:5000",
    show_default=True,
    help="URL of the Command and Control server.")
def main(c2_url: str):
    global C2_URL
    C2_URL = c2_url

@main.command(
    "lsavailable",
    short_help="List the test sets available at the C&C server.")
def lsavialable():
    """Lists the test sets available at the C&C server."""

    try:
        resp = requests.get(f"{C2_URL}/test_sets")
    except requests.exceptions.ConnectionError:
        click.echo("Connection refused.")
    else:
        if resp.status_code == 200:
            click.echo(json.dumps(resp.json(), indent=2))
        else:
            click.echo("Unexpected response from Command and Control Sever.")

@main.command(
    "upload",
    short_help="Upload a tar.gz file full of packages to the C&C server.")
@click.option(
    "--password",
    type=str,
    help=
        "Key to authenticate with the C&C server as a client. If omitted, it "
        "will be prompted.",
    prompt=True,
    hide_input=True)
@click.argument("file_path", type=click.Path(exists=True))
def upload_compressed_packages(password: str, file_path: click.Path):
    """Uploads a tar.gz file full of packages to the C&C server."""

    if not file_path.endswith(".tar.gz"):
        click.echo("Only .tar.gz extension allowed.")
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
        prepared.headers['Authorization'] = (
            signatures.new_authorization_header("Client", signature, headers))

        try:
            resp = requests.Session().send(prepared)
        except requests.exceptions.ConnectionError:
            click.echo("Connection refused.")
        else:
            if resp.status_code in {400, 401, 415}:
                click.echo(resp.json()['error'])
            elif resp.status_code != 204:
                click.echo(
                    "Unexpected response from Command and Control Sever.")

@main.command(
    "remove",
    short_help="Delete the given top level PACKAGES from the C&C server.")
@click.option(
    "--password",
    help=
        "Key to authenticate with the C&C server as a client. If omitted, it "
        "will be prompted.",
    prompt=True,
    hide_input=True)
@click.argument("packages", nargs=-1)
def remove_available_packages(password: str, packages: List[str]):
    """Delete the given top level PACKAGES from the C&C server."""

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
            click.echo("Connection refused.")
        else:
            if resp.status_code in {401, 404}:
                click.echo(resp.json()['error'])
            elif resp.status_code != 204:
                click.echo(
                    "Unexpected response from Command and Control Sever.")

@main.command(
    "lsenv",
    short_help=
        "List the environments currently registered at the C&C "
        "server.")
def lsenv():
    """List the environments currently registered at the C&C server."""

    try:
        resp = requests.get(f"{C2_URL}/environments")
    except requests.exceptions.ConnectionError:
        click.echo("Connection refused.")
    else:
        if resp.status_code != 200:
            click.echo("Unexpected response from Command and Control Sever.")
        else:
            click.echo(json.dumps(resp.json(), indent=2))

@main.command(
    "sessions_search",
    short_help=
        "Recover information about sessions that match the given criteria.")
@click.option(
    "--session_id",
    type=int,
    multiple=True,
    help="Filters by id. Multiple.")
@click.option(
    "--start_from",
    help="Filters by oldest start timestamp allowed.")
@click.option(
    "--start_to",
    help="Filters by most recent start timestamp allowed.")
@click.option("--end_from", help="Filters by oldest end timestamp allowed.")
@click.option(
    "--end_to",
    help="Filters by most recent end timestamp allowed.")
@click.option("--ip", multiple=True, help="Filters by ip. Multiple.")
@click.option(
    "--port",
    type=int,
    multiple=True,
    help="Filters by port. Multiple.")
@click.option(
    "--system",
    multiple=True,
    help="Filters by operating system. Multiple.")
@click.option(
    "--order_by",
    type=click.Choice(
        ["id", "start", "end", "ip", "port", "system"],
        case_sensitive=False),
    help="Specifies the parameter to sort by.")
@click.option(
    "--arrange",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    help="Ascending or descending sort order.")
@click.option("--limit", type=int, help="Max quantity of allowed results.")
@click.option(
    "--offset",
    type=int,
    help="Used with limit to specify where the result set should start from.")
def search_sessions(
        session_id: List[int],
        start_from: str,
        start_to: str,
        end_from: str,
        end_to: str,
        ip: List[str],
        port: List[int],
        system: List[str],
        order_by: str,
        arrange: str,
        limit: int,
        offset: int):
    """Recover information about sessions that match the given criteria."""

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
    if offset:
        query = f"{query}&offset={offset}"
    query = query.replace("&", "?", 1)

    try:
        resp = requests.get(f"{C2_URL}/sessions{query}")
    except requests.exceptions.ConnectionError:
        click.echo("Connection refused.")
    else:
        if resp.status_code == 200:
            click.echo(json.dumps(resp.json(), indent=2))
        elif resp.status_code == 400:
            click.echo(resp.json()['error'])
        else:
            click.echo("Unexpected response from Command and Control Sever.")

@main.command(
    "session_get",
    short_help="Get more information about an specific SESSION.")
@click.argument("session")
def get_session(session: int):
    """Get more information about an specific SESSION."""

    try:
        resp = requests.get(f"{C2_URL}/sessions/{session}")
    except requests.exceptions.ConnectionError:
        click.echo("Connection refused.")
    else:
        if resp.status_code == 200:
            click.echo(json.dumps(resp.json(), indent=2))
        elif resp.status_code == 404:
            click.echo(resp.json()['error'])
        else:
            click.echo("Unexpected response from Command and Control Sever.")

@main.command("sessions_delete", short_help="Delete the specified SESSIONS.")
@click.option(
    "--password",
    help=
        "Key to authenticate with the C&C server as a client. If omitted, it "
        "will be prompted.",
    prompt=True,
    hide_input=True)
@click.argument("sessions", nargs=-1)
def delete_sessions(password: str, sessions: List[int]):
    """Delete the specified SESSIONS."""

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
            click.echo("Connection refused.")
        else:
            if resp.status_code in {400, 401, 404}:
                click.echo(resp.json()['error'])
            elif resp.status_code != 204:
                click.echo(
                    "Unexpected response from Command and Control Sever.")

@main.command(
    "executions_search",
    short_help=
        "Recover information about executions that match the given "
        "criteria.")
@click.option(
    "--execution_id",
    type=int,
    multiple=True,
    help="Filters by id. Multiple.")
@click.option(
    "--session",
    type=int,
    multiple=True,
    help="Filters by session. Multiple.")
@click.option(
    "--registered_from",
    type=str,
    help="Filters by oldest register timestamp allowed.")
@click.option(
    "--registered_to",
    type=str,
    help="Filters by most recent register timestamp allowed.")
@click.option(
    "--order_by",
    type=click.Choice(["id", "session", "registered"], case_sensitive=False),
    help="Specifies the parameter to sort by.")
@click.option(
    "--arrange",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    help="Ascending or descending sort order.")
@click.option("--limit", type=int, help="Max quantity of allowed results.")
@click.option(
    "--offset",
    type=int,
    help="Used with limit to specify where the result set should start from.")
def search_executions(
        execution_id: List[int],
        session: List[int],
        registered_from: str,
        registered_to: str,
        order_by: str,
        arrange: str,
        limit: int,
        offset: int):
    """Recover information about executions that match the given criteria."""

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
    if offset:
        query = f"{query}&offset={offset}"
    query = query.replace("&", "?", 1)

    try:
        resp = requests.get(f"{C2_URL}/executions{query}")
    except requests.exceptions.ConnectionError:
        click.echo("Connection refused.")
    else:
        if resp.status_code == 200:
            click.echo(json.dumps(resp.json(), indent=2))
        elif resp.status_code == 400:
            click.echo(resp.json()['error'])
        else:
            click.echo("Unexpected response from Command and Control Sever.")

@main.command(
    "executions_delete",
    short_help="Delete the specified EXECUTIONS.")
@click.option(
    "--password",
    help=
        "Key to authenticate with the C&C server as a client. If omitted, it "
        "will be prompted.",
    prompt=True,
    hide_input=True)
@click.argument("executions", nargs=-1)
def delete_executions(password: str, executions: List[int]):
    """Delete the specified EXECUTIONS."""

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
            click.echo("Connection refused.")
        else:
            if resp.status_code in {401, 404}:
                click.echo(resp.json()['error'])
            elif resp.status_code != 204:
                click.echo(
                    "Unexpected response from Command and Control Sever.")

@main.command(
    "info",
    short_help=
        "Recover information about the platform where the node at IP:PORT is "
        "installed.")
@click.argument("ip")
@click.argument("port", type=int)
def info(ip: str, port: int):
    """Recover information about the platform where the node at IP:PORT is
    installed."""

    try:
        resp = requests.get(f"{C2_URL}/environments/{ip}/{port}/info")
    except requests.exceptions.ConnectionError:
        click.echo("Connection refused.")
    else:
        if resp.status_code == 200:
            click.echo(json.dumps(resp.json(), indent=2))
        elif resp.status_code == 404:
            click.echo(resp.json()['error'])
        else:
            click.echo("Unexpected response from Command and Control Sever.")

@main.command(
    "lsinstalled",
    short_help=
        "List the currently instaled tests sets in the environment at "
        "IP:PORT.")
@click.argument("ip")
@click.argument("port", type=int)
def lsinstalled(ip: str, port: int):
    """List the currently instaled tests sets in the environment at
    IP:PORT."""

    try:
        resp = requests.get(f"{C2_URL}/environments/{ip}/{port}/installed")
    except requests.exceptions.ConnectionError:
        click.echo("Connection refused.")
    except Exception:
        click.echo(resp.json()['error'])
    else:
        if resp.status_code == 200:
            click.echo(json.dumps(resp.json(), indent=2))
        elif resp.status_code in {404, 502, 504}:
            click.echo(resp.json()['error'])
        else:
            click.echo("Unexpected response from Command and Control Sever.")

@main.command(
    "install",
    short_help="Install the given PACKAGES in the environment at IP:PORT.")
@click.option(
    "--password",
    help=
        "Key to authenticate with the C&C server as a client. If omitted, it "
        "will be prompted.",
    prompt=True,
    hide_input=True)
@click.argument("ip")
@click.argument("port", type=int)
@click.argument("packages", nargs=-1)
def install(password: str, ip: str, port: int, packages: List[str]):
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
        click.echo("Connection refused.")
    else:
        if resp.status_code in {400, 401, 404, 415, 500, 502, 504}:
            click.echo(resp.json()['error'])
        elif resp.status_code != 204:
            click.echo("Unexpected response from Command and Control Sever.")

@main.command(
    "uninstall",
    short_help="Remove the specified PACKAGES from the node at IP:PORT.")
@click.option(
    "--password",
    help=
        "Key to authenticate with the C&C server as a client. If omitted, it "
        "will be prompted.",
    prompt=True,
    hide_input=True)
@click.argument("ip")
@click.argument("port", type=int)
@click.argument("packages", nargs=-1)
def uninstall(password: str, ip: str, port: int, packages: List[str]):
    """Remove the specified PACKAGES from the node at IP:PORT."""

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
            click.echo("Connection refused.")
        else:
            if resp.status_code in {401, 404, 502, 504}:
               click.echo(resp.json()['error'])
            elif resp.status_code != 204:
                click.echo(
                    "Unexpected response from Command and Control Sever.")

@main.command(
    "reports_get",
    short_help=
        "Execute and recover the reports of the tests installed in the "
        "environment at IP:PORT.")
@click.argument("ip")
@click.argument("port", type=int)
@click.option("--package", "-p", multiple=True)
@click.option("--module", "-m", multiple=True)
@click.option("--test_set", "-t", multiple=True)
@click.option("--test", "-t", multiple=True)
def get_reports(
        ip: str,
        port: int,
        package: str,
        module: str,
        test_set: str,
        test: str):
    """Execute and recover the reports of the tests installed in the
    environment at IP:PORT."""

    query = ""
    if package:
        query = f"{query}&packages={','.join(package)}"
    if module:
        query = f"{query}&modules={','.join(module)}"
    if test_set:
        query = f"{query}&test_sets={','.join(test_set)}"
    if test:
        query = f"{query}&tests={','.join(test)}"
    query = query.replace("&", "?", 1)

    try:
        resp = requests.get(
            f"{C2_URL}/environments/{ip}/{port}/reports{query}")
    except requests.exceptions.ConnectionError:
        click.echo("Connection refused.")
    else:
        if resp.status_code == 200:
            click.echo(json.dumps(resp.json(), indent=2))
        elif resp.status_code in {400, 404, 500, 502, 504}:
            click.echo(resp.json()['error'])
        else:
            click.echo("Unexpected response from Command and Control Sever.")

if __name__ == "__main__":
    main()