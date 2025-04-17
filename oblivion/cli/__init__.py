import click
#import oblivion.celery_app  # ensure shared_task bindings

from oblivion.cli import ansible
from oblivion.cli import wireguard
from oblivion.cli import terraform
from oblivion.cli import bao
from oblivion.cli import pki
from oblivion.cli import run
from oblivion.cli import start

@click.group()
def cli():
    """Oblivion CLI — DevOps and Task Toolkit"""
    pass

cli.add_command(ansible.cli, name="ansible")
cli.add_command(wireguard.cli, name="wireguard")
cli.add_command(terraform.cli, name="terraform")
cli.add_command(bao.cli, name="bao")
cli.add_command(pki.cli, name="pki")
cli.add_command(run.cli, name="run")
cli.add_command(start.cli, name="start")

