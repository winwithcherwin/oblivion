import json
import os
import subprocess
import socket
from pathlib import Path
from celery import shared_task
from jinja2 import Environment, FileSystemLoader
import requests
from oblivion.redis_client import redis_client

WG_DIR = "/etc/wireguard"
WG_CONF_PATH = os.path.join(WG_DIR, "wg0.conf")
WG_PRIVATE_KEY_PATH = os.path.join(WG_DIR, "privatekey")
WG_PUBLIC_KEY_PATH = os.path.join(WG_DIR, "publickey")
WIREGUARD_KEY_PREFIX = "wireguard:public_keys"
WIREGUARD_IP_PREFIX = "wireguard:ip"
WIREGUARD_PEERS_PREFIX = "wireguard:peers"
SUBNET_BASE = "10.8.0."

env = Environment(
    loader=FileSystemLoader("oblivion/engine/wireguard/templates"),
    autoescape=False,
)

def get_hostname():
    return socket.gethostname()

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=3).text.strip()
    except requests.RequestException as e:
        raise RuntimeError(f"Could not determine public IP: {e}")

def ensure_keys(force_regen=False):
    os.makedirs(WG_DIR, exist_ok=True)
    try:
        if force_regen or not Path(WG_PRIVATE_KEY_PATH).exists():
            private_key = subprocess.check_output(["wg", "genkey"]).strip()
            Path(WG_PRIVATE_KEY_PATH).write_bytes(private_key + b"\n")
            os.chmod(WG_PRIVATE_KEY_PATH, 0o600)

            public_key = subprocess.check_output(["wg", "pubkey"], input=private_key).strip()
            Path(WG_PUBLIC_KEY_PATH).write_bytes(public_key + b"\n")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error generating keys: {e}")

    return Path(WG_PUBLIC_KEY_PATH).read_text().strip()

def allocate_private_ip(hostname):
    existing = redis_client.get(f"{WIREGUARD_IP_PREFIX}:{hostname}")
    if existing:
        return existing.decode()

    for i in range(2, 255):
        candidate = f"{SUBNET_BASE}{i}"
        in_use = [redis_client.get(k).decode() for k in redis_client.keys(f"{WIREGUARD_IP_PREFIX}:*") if redis_client.get(k)]
        if candidate not in in_use:
            redis_client.set(f"{WIREGUARD_IP_PREFIX}:{hostname}", candidate)
            return candidate

    raise RuntimeError("No available IPs in 10.8.0.0/24")

@shared_task
def ping():
    return "pong"

@shared_task
def get_wireguard_status():
    import socket
    hostname = socket.gethostname()
    try:
        output = subprocess.check_output(["wg", "show", "wg0"]).decode()
        return {"hostname": hostname, "output": output}
    except subprocess.CalledProcessError as e:
        return {"hostname": hostname, "error": str(e)}

@shared_task
def register_wireguard_node():
    try:
        hostname = get_hostname()
        public_ip = get_public_ip()
        keyfile_exists = Path(WG_PRIVATE_KEY_PATH).exists()
        redis_exists = redis_client.get(f"{WIREGUARD_KEY_PREFIX}:{hostname}")

        if not keyfile_exists and redis_exists:
            public_key = ensure_keys(force_regen=True)
        else:
            public_key = ensure_keys()

        private_ip = allocate_private_ip(hostname)

        redis_client.set(f"{WIREGUARD_KEY_PREFIX}:{hostname}", json.dumps({
            "hostname": hostname,
            "public_key": public_key,
            "private_ip": private_ip,
            "public_ip": public_ip,
        }))

        return f"✅ Registered {hostname} with {private_ip}"
    except Exception as e:
        return f"❌ Registration failed: {e}"

def render_wireguard_config(self_meta, peer_list):
    interface_tpl = env.get_template("interface.tpl")
    peer_tpl = env.get_template("peer.tpl")

    try:
        private_key = Path(WG_PRIVATE_KEY_PATH).read_text().strip()
    except FileNotFoundError:
        raise RuntimeError("Missing private key at /etc/wireguard/privatekey")

    interface = interface_tpl.render(
        PRIVATE_KEY=private_key,
        PRIVATE_IP=self_meta["private_ip"]
    )

    rendered_peers = [
        peer_tpl.render(
            PUBLIC_KEY=peer["public_key"].strip(),
            ALLOWED_IP=peer["private_ip"],
            ENDPOINT=peer["public_ip"]
        ) for peer in peer_list
    ]

    return interface + "\n\n" + "\n".join(rendered_peers)

@shared_task
def write_wireguard_config(self_meta, peer_list):
    try:
        hostname = get_hostname()
        config = render_wireguard_config(self_meta, peer_list)
        Path(WG_CONF_PATH).write_text(config)
        redis_client.set(f"{WIREGUARD_PEERS_PREFIX}:{hostname}", json.dumps({
            "private_ip": self_meta["private_ip"],
            "peers": peer_list
        }))
        return f"✅ Wrote {WG_CONF_PATH} with {len(peer_list)} peers"
    except Exception as e:
        return f"❌ Failed to write config: {e}"

