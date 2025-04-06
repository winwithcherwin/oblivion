import click
from oblivion.engine.ansible import run_playbook_locally
from oblivion.engine.ansible.utils import list_available_playbooks
from oblivion.cli.shared import streaming_ansible_task_command
from oblivion.cli.shared import task_command


def parse_key_value(ctx, param, value):
    result = {}
    for item in value:
        if '=' not in item:
            raise click.BadParameter(f"Invalid format: {item}. Expected key=value")
        key, val = item.split('=', 1)
        result[key] = val
    return result

@click.group()
def cli():
    """Run ansible"""
    pass

@cli.command("run")
@streaming_ansible_task_command(task=run_playbook_locally)
@click.argument("playbook_path", type=str)
@click.option("--extra_vars", "-e", multiple=True, callback=parse_key_value, help="Pass extra vars")
def run_command(playbook_path, extra_vars):
    return (playbook_path, extra_vars)

@cli.command("list")
def list_playbooks():
    for pb in list_available_playbooks():
        click.echo(pb)

