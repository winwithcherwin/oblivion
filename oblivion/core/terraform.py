import json
import subprocess


TARGET_DIR = "terraform"

def output(target_dir=None, key=None):
    if not target_dir:
        target_dir = TARGET_DIR
    try:
        result = subprocess.run(
                ["terraform", f"-chdir={target_dir}", "output", "-json"],
                check=True,
                capture_output=True,
                text=True,
        )
        outputs = json.loads(result.stdout)
        if not key:
            return outputs
        return outputs.get(key, {}).get("value")
    except subprocess.CalledProcessError as e:
        print(f"Error calling terraform: {e}")

def get_all_hosts():
    hosts = output(key="all_hosts")
    return list(hosts.keys())
