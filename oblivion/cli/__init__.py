import click
#import oblivion.celery_app  # ensure shared_task bindings

from oblivion.cli import ansible
from oblivion.cli import wireguard
from oblivion.cli import terraform
from oblivion.cli import bao

@click.group()
def cli():
    """Oblivion CLI — DevOps and Task Toolkit"""
    pass

cli.add_command(ansible.cli, name="ansible")
cli.add_command(wireguard.cli, name="wireguard")
cli.add_command(terraform.cli, name="terraform")
cli.add_command(bao.cli, name="bao")

