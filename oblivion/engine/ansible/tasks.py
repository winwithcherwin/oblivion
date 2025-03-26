import os
import socket
import json
import time
import ansible_runner
from dotenv import load_dotenv

from celery import shared_task
from oblivion.redis_client import redis_client

PLAYBOOK_ROOT = os.path.abspath("oblivion/engine/ansible/playbooks")
ENV_FILE = "/etc/oblivion.env"
VENV_BIN = "/opt/oblivion-venv/bin"

# Load environment file if it exists
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE, override=True)

@shared_task
def run_playbook_locally(playbook_path: str, stream_id: str = None):
    base_path = os.path.join(PLAYBOOK_ROOT, playbook_path)
    abs_path = os.path.abspath(base_path)

    if os.path.isdir(abs_path):
        abs_path = os.path.join(abs_path, "site.yaml")
    elif not abs_path.endswith((".yaml", ".yml")):
        abs_path += ".yaml"

    if not abs_path.startswith(PLAYBOOK_ROOT + os.sep):
        raise ValueError(f"Invalid playbook path {abs_path}, must be inside {PLAYBOOK_ROOT}")

    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"Playbook not found: {abs_path}")

    private_data_dir = "/tmp/ansible-run"
    os.makedirs(private_data_dir, exist_ok=True)

    hostname = socket.gethostname()
    def stream_event(event):
        if stream_id and "stdout" in event and event["stdout"]:
            line = event["stdout"]
            if not line.endswith("\n"):
                line += "\n"
            data = {"data": json.dumps({"hostname": hostname, "line": line})}
            redis_client.xadd(f"ansible:{stream_id}", data)

    # Merge in the virtualenv path and env file vars
    envvars = dict(os.environ)
    envvars["PATH"] = f"{VENV_BIN}:{envvars.get('PATH', '')}"
    envvars["ANSIBLE_STDOUT_CALLBACK"] = "yaml"
    envvars["PYTHONPATH"] = "/opt/oblivion"

    start_time = time.time()
    runner = ansible_runner.run(
        private_data_dir=private_data_dir,
        playbook=abs_path,
        inventory={
            "all": {
                "hosts": {
                    hostname: {
                        "ansible_connection": "local"
                    }
                }
            }
        },
        limit=hostname,
        envvars=envvars,
        quiet=True,
        event_handler=stream_event,
    )
    end_time = time.time()

    if stream_id:
        data = {"data": json.dumps({"hostname": hostname, "eof": True})}
        redis_client.xadd(f"ansible:{stream_id}", data)

    return {
        "status": runner.status,
        "rc": runner.rc,
        "stdout": runner.stdout.read() if runner.stdout else None,
        "stats": runner.stats,
        "duration": end_time - start_time,
    }

