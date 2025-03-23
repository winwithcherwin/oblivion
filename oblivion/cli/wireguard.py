import click
import json
import random

from oblivion.cli.shared import get_all_queues
from oblivion.engine.wireguard.tasks import register_wireguard_node, write_wireguard_config, ping, get_wireguard_status
from oblivion.redis_client import redis_client

WIREGUARD_KEY_PREFIX = "wireguard:public_keys"
WIREGUARD_IP_PREFIX = "wireguard:ip"

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

    # Load registered nodes from Redis
    keys = redis_client.keys(f"{WIREGUARD_KEY_PREFIX}:*")
    hosts = {}
    for key in keys:
        try:
            raw = redis_client.get(key)
            hostname = key.decode().split(":")[-1]
            hosts[hostname] = json.loads(raw.decode())
        except Exception:
            continue

    hostnames = sorted(hosts.keys())  # Deterministic ring
    total_hosts = len(hostnames)

    for q in target_queues:
        self_meta = hosts.get(q)
        if not self_meta:
            click.echo(f"⚠️  No registration data found for {q}, skipping")
            continue

        if q not in hostnames:
            click.echo(f"⚠️  Queue '{q}' is not a registered host, skipping.")
            continue

        if total_hosts <= 1:
            peers = []
        else:
            index_in_ring = hostnames.index(q)

            # Dynamically scale peer count based on cluster size
            K = max(1, min(3, total_hosts // 4))

            # Select next K nodes in the ring
            peer_names = [
                hostnames[(index_in_ring + i + 1) % total_hosts]
                for i in range(K)
            ]
            peers = [hosts[p] for p in peer_names if p in hosts]

            if len(peers) < K:
                click.echo(f"⚠️  Only found {len(peers)} of {K} intended peers for {q}")

        click.echo(f"→ Writing config on: {q} with {len(peers)} peers")
        try:
            res = write_wireguard_config.apply_async(args=[self_meta, peers], queue=q)
            result = res.get(timeout=10)
            click.echo(f"  {q}: {result}")
        except Exception as e:
            click.echo(f"  ❌ {q}: Failed with error: {e}")

@cli.command("check-liveness")
def check_liveness():
    """Pings all known hosts. Removes dead ones from Redis."""
    keys = redis_client.keys(f"{WIREGUARD_KEY_PREFIX}:*")
    for key in keys:
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
            click.echo(f"✅ {hostname} is alive")
