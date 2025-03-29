import os
import json
import socket
import redis
from dotenv import load_dotenv

load_dotenv("/etc/oblivion.env")

def main():
    redis_uri = os.getenv("REDIS_URI")
    if not redis_uri:
        print("REDIS_URI not found in /etc/oblivion.env", flush=True)
        return 1

    hostname = socket.gethostname()
    prefix = "wireguard:peers"
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

    # Only return the directly peered nodes
    peers = self_meta.get("peers", [])
    for p in peers:
        if "hostname" not in p:
            p["hostname"] = "<unknown>"

    print(json.dumps({
        "self": self_meta,
        "peers": peers
    }), flush=True)

    return 0

if __name__ == "__main__":
    exit(main())

