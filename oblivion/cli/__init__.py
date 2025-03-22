import click
import oblivion.celery_app  # ensure shared_task bindings

from oblivion.cli import calc
from oblivion.cli import ansible
from oblivion.cli import wireguard

@click.group()
def cli():
    """Oblivion CLI — DevOps and Task Toolkit"""
    pass

cli.add_command(calc.cli, name="calc")
cli.add_command(ansible.cli, name="ansible")
cli.add_command(wireguard.cli, name="wireguard")
