import os
import redis
import json
import sys

# Load Redis connection
REDIS_URI = os.environ.get("REDIS_URI")
if not REDIS_URI:
    raise RuntimeError("REDIS_URI not set")

client = redis.Redis.from_url(REDIS_URI)

# Prefix for peer metadata
PREFIX = "wireguard:public_keys"
keys = client.keys(f"{PREFIX}:*")

# Load and decode all hosts
hosts = []
for key in keys:
    raw = client.get(key)
    if not raw:
        continue
    try:
        data = json.loads(raw.decode())
        hosts.append({
            "hostname": data["hostname"],
            "wg_ip": data["wg_ip"]
        })
    except Exception:
        continue

# Sort alphabetically by hostname for deterministic order
hosts = sorted(hosts, key=lambda h: h["hostname"])

# Build hostmap: each host has all others as peers
hostmap = {
    h["hostname"]: {
        "hostname": h["hostname"],
        "peers": [p for p in hosts if p["hostname"] != h["hostname"]]
    }
    for h in hosts
}

# Output as JSON
json.dump(hostmap, sys.stdout)

