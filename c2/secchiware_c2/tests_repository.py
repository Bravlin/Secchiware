import click
import os
import shutil

from flask import current_app
from flask.cli import with_appcontext


def init_app(app):
    app.cli.add_command(init_tests_repository_command)

def init_tests_repository() -> None:
    if os.path.isdir(current_app.config['TESTS_PATH']):
        shutil.rmtree(current_app.config['TESTS_PATH'])

    os.mkdir(current_app.config['TESTS_PATH'])
    open(
        os.path.join(current_app.config['TESTS_PATH'], "__init__.py"),
        "w"
    ).close()

@click.command("init-tests-repository")
@with_appcontext
def init_tests_repository_command():
    init_tests_repository()
    click.echo("Tests repository initialized.")