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

def parse_callback(value):
    """
    Parses strings in the format:
        module.function:arg1=val,arg2=val
    Returns:
        (callback_path, kwargs_dict)
    """
    try:
        if ":" in value:
            path, arg_str = value.split(":", 1)
            arg_str = arg_str.strip()
            args = (
                parse_key_value(None, None, arg_str.split(",")) if arg_str else {}
            )
        else:
            path = value
            args = {}

        return (path, args)
    except Exception as e:
        raise click.BadParameter(
            f"Expected format 'module.function:arg1=val,arg2=val', got: {value}"
        ) from e

@click.group()
def cli():
    """Run ansible"""
    pass

@cli.command("run")
@streaming_ansible_task_command(task=run_playbook_locally)
@click.argument("playbook_path", type=str)
@click.option("--extra_vars", "-e", multiple=True, callback=parse_key_value, help="Pass extra vars")
@click.option("--extra-vars-callback", multiple=True, callback=lambda c, p, v: [parse_callback(x) for x in v])
def run_command(playbook_path, extra_vars, extra_vars_callback):
    base_vars = dict(extra_vars or {})
    return {
        "playbook_path": playbook_path,
        "extra_vars": base_vars,
        "extra_vars_callback": extra_vars_callback,
    }

@cli.command("list")
def list_playbooks():
    for pb in list_available_playbooks():
        click.echo(pb)

