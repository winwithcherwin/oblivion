import os

import json
import subprocess

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from oblivion.connections import get_redis_client
from oblivion.core.utils import get_public_ip

WG_DIR = "/etc/wireguard"
WIREGUARD_KEY_PREFIX = "wireguard:public_keys"
WIREGUARD_IP_PREFIX = "wireguard:ip"
WIREGUARD_PEERS_PREFIX = "wireguard:peers"
SUBNET_BASE = "10.8.0."
TEMPLATE_DIR = "oblivion/core/templates/wireguard"


class WireGuardConfig:
    def __init__(self, root=None, template_dir=None):
        if root is None:
            root = WG_DIR

        if template_dir is None:
            template_dir = TEMPLATE_DIR

        self.root = root
        self.template_dir = template_dir
        self.redis_key_prefix = WIREGUARD_KEY_PREFIX
        self.redis_ip_prefix = WIREGUARD_IP_PREFIX
        self.redis_peers_prefix = WIREGUARD_PEERS_PREFIX
        self.subnet_base = SUBNET_BASE

    @property
    def path(self):
        return os.path.join(self.root, "wg0.conf")

    @property
    def private_key_path(self):
        return os.path.join(self.root, "privatekey")

    @property
    def public_key_path(self):
        return os.path.join(self.root, "publickey")

    @property
    def env(self):
        env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=False,
        )
        return env

def register_node(hostname, wg_dir=None, with_endpoint=False):
    wg_conf = WireGuardConfig(root=wg_dir)
    redis_client = get_redis_client()
    public_ip = None
    if with_endpoint:
        public_ip = get_public_ip()

    keyfile_exists = Path(wg_conf.private_key_path).exists()
    redis_exists = redis_client.get(f"{wg_conf.redis_key_prefix}:{hostname}")

    if not keyfile_exists and redis_exists:
        public_key = ensure_keys(wg_dir=wg_dir, force_regen=True)
    else:
        public_key = ensure_keys(wg_dir=wg_dir)

    private_ip = allocate_private_ip(hostname)

    redis_client.set(f"{wg_conf.redis_key_prefix}:{hostname}", json.dumps({
        "hostname": hostname,
        "public_key": public_key,
        "private_ip": private_ip,
        "public_ip": public_ip,
    }))

def ensure_keys(wg_dir=None, force_regen=False):
    wg_conf = WireGuardConfig(root=wg_dir)

    os.makedirs(wg_conf.root, exist_ok=True)
    try:
        if force_regen or not Path(wg_conf.private_key_path).exists():
            private_key = subprocess.check_output(["wg", "genkey"]).strip()
            Path(wg_conf.private_key_path).write_bytes(private_key + b"\n")
            os.chmod(wg_conf.private_key_path, 0o600)

            public_key = subprocess.check_output(["wg", "pubkey"], input=private_key).strip()
            Path(wg_conf.public_key_path).write_bytes(public_key + b"\n")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error generating keys: {e}")

    return Path(wg_conf.public_key_path).read_text().strip()

def allocate_private_ip(hostname, wg_dir=None):
    wg_conf = WireGuardConfig(root=wg_dir)
    redis_client = get_redis_client()
    existing = redis_client.get(f"{wg_conf.redis_ip_prefix}:{hostname}")
    if existing:
        return existing.decode()

    for i in range(2, 255):
        candidate = f"{wg_conf.subnet_base}{i}"
        in_use = [redis_client.get(k).decode() for k in redis_client.keys(f"{wg_conf.redis_ip_prefix}:*") if redis_client.get(k)]
        if candidate not in in_use:
            redis_client.set(f"{wg_conf.redis_ip_prefix}:{hostname}", candidate)
            return candidate

    raise RuntimeError(f"No available IPs left in {wg_conf.subnet_base}")

def render_wireguard_config(self_meta, peer_list, wg_dir=None):
    wg_conf = WireGuardConfig(root=wg_dir)
    
    interface_tpl = wg_conf.env.get_template("interface.tpl")
    peer_tpl = wg_conf.env.get_template("peer.tpl")

    try:
        private_key = Path(wg_conf.private_key_path).read_text().strip()
    except FileNotFoundError:
        raise RuntimeError(f"Missing private key at {wg_conf.private_key_path}")

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

def get_peers(hostname):
    wg_conf = WireGuardConfig()
    redis_client = get_redis_client()
    keys = redis_client.keys(f"{wg_conf.redis_key_prefix}:*")
    hosts = {}
    for key in keys:
        try:
            raw = redis_client.get(key)
            if not raw:
                continue
            peer_hostname = key.decode().split(":")[-1]
            hosts[peer_hostname] = json.loads(raw.decode())
        except Exception as e:
            raise Exception(f"Failed to parse metadata for {peer_hostname}: {e}")
    if not hosts:
        raise Exception("No hosts found.")

    self_meta = hosts[hostname]
    peer_list = [h for h in hosts.keys() if h != hostname]
    peers = [hosts[peer] for peer in peer_list]
    return self_meta, peers

def write_config(hostname, wg_dir=None):
    wg_conf = WireGuardConfig(root=wg_dir)
    redis_client = get_redis_client()
    self_meta, peers = get_peers(hostname)
    config = render_wireguard_config(self_meta, peers, wg_dir=wg_conf.root)
    Path(wg_conf.path).write_text(config)
    redis_client.set(f"{wg_conf.redis_peers_prefix}:{hostname}", json.dumps({
        "private_ip": self_meta["private_ip"],
        "peers": peers
    }))

