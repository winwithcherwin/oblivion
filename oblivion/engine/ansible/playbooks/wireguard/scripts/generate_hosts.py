import os
import redis
import json
import sys

REDIS_URI = os.environ.get("REDIS_URI")
if not REDIS_URI:
    raise RuntimeError("REDIS_URI not set")

client = redis.Redis.from_url(REDIS_URI)

PREFIX = "wireguard:public_keys"
keys = client.keys(f"{PREFIX}:*")

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

# Emit as key-value per hostname for --extra-vars usage
hostmap = {host["hostname"]: {"hostname": host["hostname"], "peers": [p for p in hosts if p["hostname"] != host["hostname"]]}}
json.dump(hostmap, sys.stdout)

