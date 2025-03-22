import click
from oblivion.engine.ansible import run_playbook_locally
from oblivion.engine.ansible.utils import list_available_playbooks
from oblivion.cli.shared import streaming_ansible_task_command
from oblivion.cli.shared import task_command


@click.group()
def cli():
    """Run ansible"""
    pass

@cli.command("run")
@streaming_ansible_task_command(task=run_playbook_locally)
@click.argument("playbook_path", type=str)
def run_command(playbook_path):
    return (playbook_path,)

@cli.command("list")
def list_playbooks():
    for pb in list_available_playbooks():
        click.echo(pb)

