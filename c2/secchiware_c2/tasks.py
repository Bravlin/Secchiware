import click
import json
import os
import requests as rq
import signatures

from flask import Flask, current_app
from flask.cli import with_appcontext
from secchiware_c2.database import get_database
from secchiware_c2.memory_storage import get_memory_storage
from test_utils import get_installed_test_sets


def init_app(app: Flask):
    app.cli.add_command(init_memory_storage_command)
    app.cli.add_command(check_tests_repository_command)
    app.cli.add_command(stop_active_environments_command)
    app.cli.add_command(setup_command)
    app.cli.add_command(cleanup_command)

def init_memory_storage() -> None:
    """Initialize the in-memory storage cleaning any previous data and caching
    the result of the inspection of the available packages in the
    repository."""

    memory_storage = get_memory_storage()
    memory_storage.flushdb()
    pipe = memory_storage.pipeline()
    for p in get_installed_test_sets("test_sets"):
        pipe.set(f"repository:{p['name']}", json.dumps(p))
        pipe.zadd("repository_index", {p['name']: 0})
    pipe.execute()

@click.command("init-memory-storage")
@with_appcontext
def init_memory_storage_command():
    """Clear the memory storage and initialize it with the result of the
    inspection of the available packages in the tests repository."""

    init_memory_storage()
    click.echo("Memory storage initialized.")

def check_tests_repository() -> None:
    """Checks if the root package for test sets already exists. If that's not
    the case, then it gets created."""

    if not os.path.isdir(current_app.config['TESTS_PATH']):
        os.mkdir(current_app.config['TESTS_PATH'])
        open(
            os.path.join(current_app.config['TESTS_PATH'], "__init__.py"),
            "w"
        ).close()

@click.command("check-tests-repository")
@with_appcontext
def check_tests_repository_command():
    """Create the root package for tests sets if it does not exists."""

    check_tests_repository()
    click.echo("Tests repository checked.")

def stop_active_environments() -> None:
    """Tries to shutdown all currently active nodes. It also updates the
    database ending all current sessions."""

    get_memory_storage().flushdb(asynchronous=True)

    db = get_database() 
    cursor = db.execute(
        """SELECT env_ip, env_port
        FROM session
        WHERE session_end IS NULL""")

    environments = cursor.fetchall()
    if environments:
        signature = signatures.new_signature(
            current_app.config['NODE_SECRET'],
            "DELETE",
            "/")
        authorization_content = (
            signatures.new_authorization_header("C2", signature))

        for env in environments:
            ip = env['env_ip']
            port = env['env_port']
            try:
                resp = rq.delete(
                    f"http://{ip}:{port}/",
                    headers={'Authorization': authorization_content})
            except rq.exceptions.ConnectionError:
                click.echo(f"Node at {ip}:{port} could not be reached.")
            else:
                if resp.status_code != 204:
                    click.echo(
                        f"Unexpected response from node at {ip}:{port}.")
                else:
                    click.echo(f"Node at {ip}:{port} reached.")

        cursor.execute(
            """UPDATE session
            SET session_end = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE session_end IS NULL""")
        db.commit()

@click.command("stop-active-environments")
@with_appcontext
def stop_active_environments_command():
    """Turn off all active nodes."""

    click.echo("Stopping process started.")
    stop_active_environments()
    click.echo("Environments stopped.")

def setup() -> None:
    """Executes all the necessary steps before the server starts."""
 
    init_memory_storage()
    check_tests_repository()

@click.command("setup")
@with_appcontext
def setup_command():
    """Execute tasks needed before starting the server."""

    click.echo("Setup started.")
    setup()
    click.echo("Setup finished.")

def cleanup() -> None:
    """Executes all the necessary cleanup tasks after stopping the server."""

    stop_active_environments()

@click.command("cleanup")
@with_appcontext
def cleanup_command():
    """Execute all the necessary cleanup tasks after stopping the server."""

    click.echo("Cleanup started.")
    cleanup()
    click.echo("Cleanup finished.")