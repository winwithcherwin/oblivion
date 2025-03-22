import json
import os
import subprocess
import socket

from celery import shared_task
from jinja2 import Environment, FileSystemLoader

from oblivion.redis_client import redis_client


WIREGUARD_KEY_PREFIX = "wireguard:public_keys"

WG_DIR = "/etc/wireguard"
WG_PRIVATE_KEY_PATH = os.path.join(WG_DIR, "privatekey")
WG_PUBLIC_KEY_PATH = os.path.join(WG_DIR, "publickey")

env = Environment(
    loader=FileSystemLoader("oblivion/engine/wireguard/templates"),
    autoescape=False,
)

@shared_task
def register_public_key(hostname: str, public_key: str, private_ip: str, public_ip: str):
    """Register a host's WireGuard public key + IP info."""
    data = {
        "hostname": hostname,
        "public_key": public_key,
        "private_ip": private_ip,
        "public_ip": public_ip,
    }
    redis_client.hset(WIREGUARD_KEY_PREFIX, hostname, json.dumps(data), ex=300)

    return f"Registered WireGuard key for {hostname}"

@shared_task
def generate_wireguard_conf():
    """Generates peer configs for all registered hosts."""
    all_keys = redis_client.hgetall(WIREGUARD_KEY_PREFIX)
    hosts = {k.decode(): json.loads(v.decode()) for k, v in all_keys.items()}

    configs = {}
    for hostname, meta in hosts.items():
        peers = [v for k, v in hosts.items() if k != hostname]
        conf = render_wireguard_conf(meta, peers)
        configs[hostname] = conf

    return configs

def render_wireguard_conf(self_meta, peers):
    interface_tpl = env.get_template("interface.tpl")
    peer_tpl = env.get_template("peer.tpl")

    interface = interface_tpl.render(
        PRIVATE_KEY="REPLACE_WITH_YOUR_PRIVATE_KEY",  # for now
        PRIVATE_IP=self_meta["private_ip"]
    )

    rendered_peers = [
        peer_tpl.render(
            PUBLIC_KEY=p["public_key"],
            ALLOWED_IP=p["private_ip"],
            ENDPOINT=p["public_ip"]
        )
        for p in peers
    ]

    return interface + "\n\n" + "\n".join(rendered_peers)

@shared_task
def generate_and_register_keys(private_ip: str, public_ip: str):
    """
    Generates private/public WireGuard keys (if not already generated),
    and registers the public key to Redis with hostname + IP metadata.
    """
    hostname = socket.gethostname()
    os.makedirs(WG_DIR, exist_ok=True)

    if not os.path.exists(WG_PRIVATE_KEY_PATH):
        private_key = subprocess.check_output(["wg", "genkey"]).strip()
        with open(WG_PRIVATE_KEY_PATH, "wb") as f:
            f.write(private_key + b"\n")
        os.chmod(WG_PRIVATE_KEY_PATH, 0o600)

        public_key = subprocess.check_output(["wg", "pubkey"], input=private_key).strip()
        with open(WG_PUBLIC_KEY_PATH, "wb") as f:
            f.write(public_key + b"\n")
    else:
        with open(WG_PUBLIC_KEY_PATH, "rb") as f:
            public_key = f.read().strip()

    register_public_key(hostname, public_key.decode(), private_ip, public_ip)
    return f"Keys ensured, public key registered for {hostname}"

