import click
import threading
import uvicorn

from datetime import datetime
from rich import print

from oblivion import VERSION
from oblivion.control.ubuild.webhook import app as ubuild_webhook
from oblivion.control.ubuild import runner as ubuild


def run_ubuild_webhook():
    uvicorn.run(ubuild_webhook, host="0.0.0.0", port=8080, log_level="info")

@click.group()
def cli():
    """Start server"""
    pass

@cli.command("ubuild")
@click.option("--enable-webhook", is_flag=True, required=False, default=True)
def run_ubuild(enable_webhook):
    """Run ubuild"""

    print(f"running ubuild v{VERSION}...")

    if enable_webhook:
        webhook = threading.Thread(target=run_ubuild_webhook, daemon=True)
        webhook.start()

    ubuild.run()

