import click
import sqlite3

from flask import current_app, g
from flask.cli import with_appcontext
from typing import Dict, Tuple


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
    """Closes a lingering database connection."""

    db = g.pop('database', None)
    if db is not None:
        db.close()

def api_parametrized_search(
        table: str,
        order_by_api_to_db: Dict[str, str],
        where_api_to_db: Dict[str, Tuple[str, str]],
        parameters: dict,
        select_columns: tuple = None) -> sqlite3.Cursor:
    """Converts the recieved parameters into a SQL SELECT statement, executes
    it and returns the corresponding cursor.

    Parameters
    ----------
    table: str
        The database table to look into.
    order_by_api_to_db: Dict[str, str]
        A dictionary where each key is one of the accepted parameters to sort
        by of the external API and its value is the corresponding column name.
    where_api_to_db: Dict[str, Tuple[str, str]]
        A dictionary where each key is one of the accepted parameters to
        filter by of the external API and its values is a tuple where the
        first member is the corresponding column name and the second one is
        the associated operator.
    parameters: dict
        A dictionary where each key-value pair is the name of an argument
        recieved by the external API and its corresponding value.
    select_columns: tuple
        The columns that the developer wants to return with the generated
        query.

    Exceptions
    ----------
    ValueError
        There is content present in the "parameters" argument that is not
        valid.

    Returns
    -------
    sqlite3.Cursor
        A cursor to the formulated query.
    """

    if not select_columns:
        query = f"SELECT * FROM {table}"
    else:
        query = f"SELECT {', '.join(select_columns)} FROM {table}"

    param_keys = {*parameters.keys()}
    if not 'order_by' in param_keys:
        if 'arrange' in param_keys:
            raise ValueError("arrange key present when no order is specified")
        order_by_clause = ""
    else:
        if not parameters['order_by'] in order_by_api_to_db:
            raise ValueError("Invalid order key")
        order_by_clause = (
            f"ORDER BY {order_by_api_to_db[parameters['order_by']]}")
        param_keys.remove('order_by')

        if 'arrange' in param_keys:
            if parameters['arrange'] not in {'asc', 'desc'}:
                raise ValueError("Invalid arrange value")
            order_by_clause = f"{order_by_clause} {parameters['arrange']}"
            param_keys.remove('arrange')
    
    if not 'limit' in param_keys:
        if 'offset' in param_keys:
            raise ValueError("offset key present when no limit is specified")
        limit_clause = ""
    else:
        if int(parameters['limit']) <= 0:
            raise ValueError("Invalid limit value")
        limit_clause = f"LIMIT {parameters['limit']}"
        param_keys.remove('limit')

        if 'offset' in param_keys:
            if int(parameters['offset']) < 0:
                raise ValueError("Invalid offset value")
            limit_clause = f"{limit_clause} OFFSET {parameters['offset']}"
            param_keys.remove('offset')

    where_clause = ""
    placeholders_values = {}
    for key in param_keys:
        if key not in where_api_to_db:
            raise ValueError("Invalid query parameter found")
        where_filter = ""
        column = where_api_to_db[key][0]
        operator = where_api_to_db[key][1]
        i = 0
        for value in parameters[key].split(","):
            placeholder_key = f"{key}{i}"
            placeholders_values[placeholder_key] = value
            where_filter = (
                f"{where_filter} OR {column}{operator}:{placeholder_key}")
            i += 1

        where_filter = where_filter.replace(" OR ", "", 1)
        where_clause = f"{where_clause} AND ({where_filter})"
    where_clause = where_clause.replace(" AND", "WHERE", 1)

    query = f"{query} {where_clause} {order_by_clause} {limit_clause}"
    return get_database().execute(query, placeholders_values)

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
