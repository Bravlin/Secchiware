import click
import json
import redis

from flask import current_app, g
from flask.cli import with_appcontext
from test_utils import get_installed_test_sets


def init_app(app):
    app.cli.add_command(init_memory_storage_command)

def get_memory_storage() -> redis.StrictRedis:
    """Gets a connection to the in-memory storage.

    It starts one if it was not already created.

    Returns
    -------
    redis.StrictRedis
        The connection to the in-memory storage.
    """

    if 'memory_storage' not in g:
        g.memory_storage = redis.StrictRedis(
            host=current_app.config['REDIS']['HOST'],
            port=current_app.config['REDIS']['PORT'],
            db=current_app.config['REDIS']['DB'],
            password=current_app.config['REDIS']['PASSWORD'],
            decode_responses=True,
            charset="utf-8")
    
    return g.memory_storage

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