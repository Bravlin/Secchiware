import click
import json
import redis

from flask import current_app, g
from flask.cli import with_appcontext
from test_utils import get_installed_test_sets


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

def clear_environment_cache(environment_key: str) -> None:
    """Clear all cached data of the specified environment from the in-memory
    repository.

    Parameters
    ----------
    environment_key: str
        The key by which the environment is identified in the in-memory
        repository.
    """

    memory_storage = get_memory_storage()
    pipe = memory_storage.pipeline()
    pipe.delete(environment_key)
    pipe.delete(f"{environment_key}:installed_index")
    pipe.execute()