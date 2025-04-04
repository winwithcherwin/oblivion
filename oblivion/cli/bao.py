import json
import click
import hvac

@click.group()
def cli():
    """OpenBao operations"""
    pass

@cli.command("bootstrap")
@click.argument("endpoint", type=str)
def bootstrap_command(endpoint):
    client = hvac.Client(
            url=endpoint,
            verify=False,
    )

    if client.sys.is_initialized():
        click.echo("doing nothing, already initialized.")
        return
    
    result = client.sys.initialize(1, 1)
    with open("secrets.json", "w") as f:
        json.dumps(result, f)

    client.token = result["root_token"]
    unseal_response = client.sys.submit_unseal_keys(result["keys"])
    click.echo(f"unseal response: {unseal_response}")

    if not client.sys.is_sealed():
        click.echo("successfully unsealed bao")
        return

