import click
import subprocess
import json

from oblivion.core import terraform as tf_core
from oblivion.control.terraform import validate as tf_validate


@click.group()
def cli():
    """Run terraform"""
    pass

@cli.command("output")
@click.option("--key", type=str)
def run_command(key):
    if key == "":
        raise click.ClickException("do not pass in empty key, remove --key if you want full output")

    value = tf_core.output(key=key)
    if not value:
        errmsg = f"key `{key}` does not exist"
        raise click.ClickException(errmsg)
    print(value)

@cli.command("all-hosts")
@click.option("--key", type=str)
def run_command(key):
    all_hosts = tf_core.get_all_hosts()
    if all_hosts is None:
        click.echo("no hosts provisioned.")
        return
    click.echo(all_hosts)

@cli.group()
def validate():
    """Validate all things terraform"""
    pass

@validate.command("redis-uri")
def validate_redis_uri():
    try:
        tf_validate.redis_uri()
    except Exception as e:
        click.echo(f"validation failed with: {e}")

