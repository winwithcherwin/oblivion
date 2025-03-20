import click
from oblivion.engine.tasks import add, subtract
from oblivion.cli.shared import task_command

@click.group()
def cli():
    """Calculator operations"""
    pass

@cli.command("add")
@task_command(task=add)
@click.argument("a", type=int)
@click.argument("b", type=int)
def add_command(a, b):
    return (a, b)

@cli.command("subtract")
@task_command(task=subtract)
@click.argument("a", type=int)
@click.argument("b", type=int)
def subtract_command(a, b):
    return (a, b)

