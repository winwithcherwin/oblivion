import ansible_runner

from celery import shared_task


@shared_task
def run_playbook_locally(playbook_path: str):
    runner = ansible_runner.run(
        private_data_dir="/tmp/ansible-run",
        playbook=playbook_path,
        inventory="localhost,",
        limit="localhost",
        quiet=True
    )

    return {
        "status": runner.status,
        "rc": runner.rc,
        "stdout": runner.stdout.read(),
        "stats": runner.stats,
    }

