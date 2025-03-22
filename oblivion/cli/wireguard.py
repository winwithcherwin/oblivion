import click
import json
import random
from oblivion.cli.shared import get_all_queues
from oblivion.engine.wireguard.tasks import register_wireguard_node, write_wireguard_config, ping
from oblivion.redis_client import redis_client

WIREGUARD_KEY_PREFIX = "wireguard:public_keys"
WIREGUARD_IP_PREFIX = "wireguard:ip"

@click.group()
def cli():
    """Manage WireGuard overlay network"""
    pass

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
    keys = redis_client.keys(f"{WIREGUARD_KEY_PREFIX}:*")
    hosts = {}
    for key in keys:
        try:
            raw = redis_client.get(key)
            hostname = key.decode().split(":")[-1]
            hosts[hostname] = json.loads(raw.decode())
        except Exception:
            continue

    for q in target_queues:
        self_meta = hosts.get(q)
        if not self_meta:
            click.echo(f"⚠️  No registration data found for {q}, skipping")
            continue

        # Select up to 3 random peers excluding self
        peers = [v for k, v in hosts.items() if k != q]
        random.shuffle(peers)
        peers = peers[:3]

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
