import click
import json
import random

from oblivion.cli.shared import get_all_queues
from oblivion.engine.wireguard.tasks import register_wireguard_node, write_wireguard_config, ping, get_wireguard_status
from oblivion.redis_client import redis_client

WIREGUARD_KEY_PREFIX = "wireguard:public_keys"
WIREGUARD_IP_PREFIX = "wireguard:ip"
WIREGUARD_PEERS_PREFIX = "wireguard:peers"

@click.group()
def cli():
    """Manage WireGuard overlay network"""
    pass

@cli.command("status")
@click.option("--all", "fanout", is_flag=True, help="Query all hosts")
@click.option("--queues", help="Comma-separated list of queues")
def get_status(fanout, queues):
    """Show wg0 interface status on all nodes."""
    if not fanout and not queues:
        raise click.ClickException("You must specify --all or --queues")

    target_queues = get_all_queues() if fanout else [q.strip() for q in queues.split(",")]

    for q in target_queues:
        click.echo(f"→ Checking wg0 on: {q}")
        res = get_wireguard_status.apply_async(queue=q)
        result = res.get(timeout=10)
        if 'output' in result:
            click.echo(f"🟢 {result['hostname']}:\n{result['output']}")
        else:
            click.echo(f"🔴 {result['hostname']} error: {result.get('error')}")

@cli.command("register")
@click.option("--all", "fanout", is_flag=True, help="Register all hosts")
@click.option("--queues", help="Comma-separated list of queue names")
def register_nodes(fanout, queues):
    if not fanout and not queues:
        raise click.ClickException("You must specify --all or --queues")

    target_queues = get_all_queues() if fanout else [q.strip() for q in queues.split(",")]

    for q in target_queues:
        click.echo(f"→ Registering on: {q}")
        try:
            res = register_wireguard_node.apply_async(queue=q)
            result = res.get(timeout=10)
            click.echo(f"  {q}: {result}")
        except Exception as e:
            click.echo(f"  ❌ {q}: Failed with error: {e}")

@cli.command("write-config")
@click.option("--all", "fanout", is_flag=True, help="Target all hosts")
@click.option("--queues", help="Comma-separated list of queue names")
def write_configs(fanout, queues):
    if not fanout and not queues:
        raise click.ClickException("You must specify --all or --queues")

    target_queues = get_all_queues() if fanout else [q.strip() for q in queues.split(",")]

    # Load all peer metadata from Redis
    keys = redis_client.keys(f"{WIREGUARD_KEY_PREFIX}:*")
    hosts = {}
    for key in keys:
        try:
            raw = redis_client.get(key)
            if not raw:
                continue
            hostname = key.decode().split(":")[-1]
            hosts[hostname] = json.loads(raw.decode())
        except Exception:
            click.echo(f"Failed to parse metadata for {key.decode()}")
            continue

    if not hosts:
        click.echo("No hosts found.")
        return

    mesh = {hostname: set(hosts.keys() - {hostname}) for hostname in hosts.keys()}
    for hostname in target_queues:
        self_meta = hosts[hostname]
        peers = [hosts[peer] for peer in mesh[hostname]]
        click.echo(f"Writing config on {hostname}")
        try:
            res = write_wireguard_config.apply_async(args=[self_meta, peers], queue=hostname)
            result = res.get(timeout=10)
            click.echo(f"  {hostname}: {result}")
        except Exception as e:
            click.echo(f"  {hostname}: Failed with error: {e}")

@cli.command("sweep")
def do_ping():
    """Sweeps all wireguard hosts via ping. Removes dead ones from Redis."""
    keys = redis_client.keys(f"{WIREGUARD_KEY_PREFIX}:*")
    for key in keys:
        # if there is no endpoint we should skip it, because it is assumed to be a client
        #raw = redis_client.get(key)
        # load json and check for endpoint, skip if no endpoint
        hostname = key.decode().split(":")[-1]
        success = False
        for _ in range(3):
            try:
                res = ping.apply_async(queue=hostname)
                if res.get(timeout=3) == "pong":
                    success = True
                    break
            except Exception:
                continue

        if not success:
            click.echo(f"❌ {hostname} unreachable. Removing from Redis")
            redis_client.delete(f"{WIREGUARD_KEY_PREFIX}:{hostname}")
            redis_client.delete(f"{WIREGUARD_IP_PREFIX}:{hostname}")
        else:
            click.echo(f"✅ {hostname} sent pong")

@cli.command("show-peers")
def do_show_peers():
    """Show registered configs for all nodes"""
    keys = redis_client.keys(f"{WIREGUARD_PEERS_PREFIX}:*")
    hosts = {}
    for key in keys:
        try:
            raw = redis_client.get(key)
            if not raw:
                continue
            hostname = key.decode().split(":")[-1]
            hosts[hostname] = json.loads(raw.decode())
        except Exception:
            click.echo(f"⚠️  Failed to parse metadata for {key.decode()}")
            continue

    print(json.dumps(hosts))

