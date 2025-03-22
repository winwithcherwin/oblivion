import json
import os
import subprocess
import socket
import logging

from celery import shared_task
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from oblivion.redis_client import redis_client

# Constants
WIREGUARD_KEY_PREFIX = "wireguard:public_keys"
WG_DIR = "/etc/wireguard"
WG_CONF_PATH = os.path.join(WG_DIR, "wg0.conf")
WG_PRIVATE_KEY_PATH = os.path.join(WG_DIR, "privatekey")
WG_PUBLIC_KEY_PATH = os.path.join(WG_DIR, "publickey")

# Jinja2 setup
env = Environment(
    loader=FileSystemLoader("oblivion/engine/wireguard/templates"),
    autoescape=False,
)

# Logging (optional but encouraged)
logger = logging.getLogger(__name__)


def register_public_key(hostname: str, public_key: str, private_ip: str, public_ip: str):
    """Register a host's WireGuard public key + IP info in Redis."""
    key = f"{WIREGUARD_KEY_PREFIX}:{hostname}"
    data = {
        "hostname": hostname,
        "public_key": public_key.strip(),
        "private_ip": private_ip,
        "public_ip": public_ip,
    }

    try:
        redis_client.set(key, json.dumps(data), ex=300)
        return f"Registered WireGuard key for {hostname}"
    except Exception as e:
        logger.error(f"Redis error while registering key: {e}")
        raise


def render_wireguard_conf(self_meta, peers):
    """Renders a full wg0.conf from the given host + peer metadata."""
    try:
        interface_tpl = env.get_template("interface.tpl")
        peer_tpl = env.get_template("peer.tpl")
    except TemplateNotFound as e:
        raise RuntimeError(f"Missing template: {e}")

    interface = interface_tpl.render(
        PRIVATE_KEY="REPLACE_WITH_YOUR_PRIVATE_KEY",
        PRIVATE_IP=self_meta["private_ip"]
    )

    rendered_peers = []
    for p in peers:
        try:
            rendered_peers.append(peer_tpl.render(
                PUBLIC_KEY=p["public_key"].strip(),
                ALLOWED_IP=p["private_ip"],
                ENDPOINT=p["public_ip"]
            ))
        except KeyError as e:
            logger.warning(f"Missing key in peer metadata: {e}")

    return interface + "\n\n" + "\n".join(rendered_peers)


@shared_task
def generate_wireguard_conf():
    """
    Generates wg0.conf configurations for all registered WireGuard nodes.

    Returns:
        dict: hostname → rendered wg0.conf string
    """
    keys = redis_client.keys(f"{WIREGUARD_KEY_PREFIX}:*")
    hosts = {}

    for key in keys:
        try:
            raw = redis_client.get(key)
            if not raw:
                continue
            hostname = key.decode().split(":")[-1]
            hosts[hostname] = json.loads(raw.decode())
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError) as e:
            logger.warning(f"Skipping malformed entry {key}: {e}")
            continue

    configs = {}
    for hostname, self_meta in hosts.items():
        peers = [meta for peername, meta in hosts.items() if peername != hostname]
        try:
            config = render_wireguard_conf(self_meta, peers)
            configs[hostname] = config
        except Exception as e:
            logger.error(f"Failed to generate config for {hostname}: {e}")
            configs[hostname] = f"# Error generating config for {hostname}: {str(e)}"

    return configs


@shared_task
def generate_and_register_keys(private_ip: str, public_ip: str):
    """
    Generates private/public WireGuard keys (if not already present),
    and registers the public key in Redis.
    """
    hostname = socket.gethostname()
    os.makedirs(WG_DIR, exist_ok=True)

    try:
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
    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"Failed to generate WireGuard keys: {e}")
        raise RuntimeError(f"WireGuard key generation failed: {e}")

    register_public_key(hostname, public_key.decode(), private_ip, public_ip)
    return f"Keys ensured, public key registered for {hostname}"

