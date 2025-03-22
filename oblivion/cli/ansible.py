import click
from oblivion.engine.ansible import run_playbook_locally
from oblivion.cli.shared import task_command

@click.group()
def cli():
    """Run ansible"""
    pass

@cli.command("run")
@task_command(task=run_playbook_locally)
@click.argument("playbook_path", type=str)
def run_command(playbook_path):
    return (playbook_path,)

