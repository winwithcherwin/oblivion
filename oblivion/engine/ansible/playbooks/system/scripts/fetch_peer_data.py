#!/usr/bin/env python3

import os
import json
import socket
import redis
import sys
from dotenv import load_dotenv

load_dotenv("/etc/oblivion.env")

def fail(msg):
    print(f"{msg}", file=sys.stderr, flush=True)
    sys.exit(1)

def main():
    redis_uri = os.getenv("REDIS_URI")
    if not redis_uri:
        fail("REDIS_URI not found in /etc/oblivion.env")

    hostname = socket.gethostname()
    prefix = "wireguard:peers"
    self_key = f"{prefix}:{hostname}"

    try:
        r = redis.Redis.from_url(redis_uri, decode_responses=True)
    except Exception as e:
        fail(f"Failed to connect to Redis: {e}")

    raw_self = r.get(self_key)
    if not raw_self:
        fail(f"Peer metadata missing for: {self_key}")

    try:
        self_meta = json.loads(raw_self)
        self_meta["hostname"] = hostname
    except Exception as e:
        fail(f"Failed to parse self peer data: {e}")

    # Only return directly connected peers
    peers = self_meta.get("peers", [])
    for peer in peers:
        peer.setdefault("hostname", "<unknown>")

    output = {
        "self": self_meta,
        "peers": peers
    }

    try:
        print(json.dumps(output), flush=True)
    except Exception as e:
        fail(f"Failed to serialize output: {e}")

    sys.exit(0)

if __name__ == "__main__":
    main()

