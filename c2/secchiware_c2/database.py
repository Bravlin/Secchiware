import click
import sqlite3

from flask import current_app, g
from flask.cli import with_appcontext


def init_app(app):
    app.teardown_appcontext(close_database)
    app.cli.add_command(init_database_command)

def get_database() -> sqlite3.Connection:
    """Gets a database connection.

    It starts one if it was not already created.

    Returns
    -------
    sqlite3.Connection
        The open database connection.
    """

    if 'database' not in g:
        g.database = sqlite3.connect(current_app.config['DATABASE'])
        g.database.row_factory = sqlite3.Row
        g.database.execute("PRAGMA foreign_keys = ON")

    return g.database

def close_database(error=None) -> None:
    db = g.pop('database', None)
    if db is not None:
        db.close()

def init_database() -> None:
    """Clears the database and creates the schemas needed for the
    application."""

    db = get_database()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))

@click.command("init-database")
@with_appcontext
def init_database_command():
    """Clear any existing data and create the database from scratch."""

    init_database()
    click.echo("Database initialized.")