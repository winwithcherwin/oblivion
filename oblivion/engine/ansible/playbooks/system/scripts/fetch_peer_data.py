#!/usr/bin/env python3

import os
import socket
import json
import redis
from dotenv import load_dotenv

# Load environment variables from /etc/oblivion.env
load_dotenv("/etc/oblivion.env")

def main():
    redis_uri = os.getenv("REDIS_URI")
    if not redis_uri:
        print("REDIS_URI not found in /etc/oblivion.env", flush=True)
        return 1

    prefix = "wireguard:peers"
    hostname = socket.gethostname()
    self_key = f"{prefix}:{hostname}"

    try:
        r = redis.Redis.from_url(redis_uri, decode_responses=True)
    except Exception as e:
        print(f"Failed to connect to Redis: {e}", flush=True)
        return 1

    raw_self = r.get(self_key)
    if not raw_self:
        print(f"Peer metadata missing for: {self_key}", flush=True)
        return 1

    try:
        self_meta = json.loads(raw_self)
        self_meta["hostname"] = hostname
    except Exception as e:
        print(f"Failed to parse JSON for {self_key}: {e}", flush=True)
        return 1

    # Load the full topology
    topology = {}
    for key in r.scan_iter(f"{prefix}:*"):
        raw = r.get(key)
        if not raw:
            continue
        try:
            peer = json.loads(raw)
            peer["hostname"] = key.split(":", 1)[1]
            peer["private_ip"] = peer.get("private_ip")
            topology[peer["hostname"]] = peer
        except Exception as e:
            print(f"Skipping {key}: {e}", flush=True)

    # Build full peer list
    peers = [v for k, v in topology.items() if k != hostname]

    # Determine which peers we are *actually connected to* via WireGuard
    direct_peer_ips = {
        p["private_ip"]
        for p in self_meta.get("peers", [])
        if "private_ip" in p
    }

    self_meta["direct_peer_ips"] = list(direct_peer_ips)

    print(json.dumps({
        "self": self_meta,
        "peers": peers
    }), flush=True)
    return 0

if __name__ == "__main__":
    exit(main())

