import click
import oblivion.celery_app  # ensure shared_task bindings

from oblivion.cli import calc

@click.group()
def cli():
    """Oblivion CLI — DevOps and Task Toolkit"""
    pass

cli.add_command(calc.cli, name="calc")

