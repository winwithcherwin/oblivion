import ansible_runner
import os

from celery import shared_task


@shared_task
def run_playbook_locally(playbook_path: str):
    private_data_dir = "/tmp/ansible-run"
    os.makedirs(private_data_dir, exist_ok=True)

    runner = ansible_runner.run(
        private_data_dir=private_data_dir,
        playbook=playbook_path,
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
        "stdout": runner.stdout.read(),
        "stats": runner.stats,
    }

