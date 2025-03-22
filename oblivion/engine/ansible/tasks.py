import ansible_runner
import os

from celery import shared_task


PLAYBOOK_ROOT = os.path.abspath("oblivion/engine/ansible/playbooks")


@shared_task
def run_playbook_locally(playbook_path: str):
    abs_playbook_path = os.path.abspath(os.path.join(PLAYBOOK_ROOT, playbook_path))

    if not abs_playbook_path.startswith(PLAYBOOK_ROOT + os.sep):
        raise ValueError(f"Invalid playbook path {abs_playbook_path}, must be inside {PLAYBOOK_ROOT}")

    if not os.path.isfile(abs_playbook_path):
        raise FileNotFoundError(f"Playbook not found: {abs_playbook_path}")

    private_data_dir = "/tmp/ansible-run"
    os.makedirs(private_data_dir, exist_ok=True)

    runner = ansible_runner.run(
        private_data_dir=private_data_dir,
        playbook=abs_playbook_path,
        inventory={
            "all": {
                "hosts": {
                    "localhost": {
                        "ansible_connection": "local"
                    }
                  }
                }
              },
        limit="localhost",
        quiet=True,
    )

    return {
        "status": runner.status,
        "rc": runner.rc,
        "stdout": runner.stdout.read() if runner.stdout else None,
        "stats": runner.stats,
    }

