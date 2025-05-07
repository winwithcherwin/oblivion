import click
import threading
import uvicorn
import subprocess

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

@cli.command("mcp")
def run_mcp():
    """Run MCP server"""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("kubernetes")

    @mcp.tool()
    async def kubectl_get_pods(namespace):
        """Get all pods in a kubernetes namespace"""
        return subprocess.check_output(["kubectl", "get", "pods", "-n", namespace])

    @mcp.tool()
    async def kubectl_delete_pod(name, namespace):
        """Delete pod in namespace"""
        return subprocess.check_output(["kubectl", "delete", "pod", "-n", namespace, name])

    mcp.run(transport="sse")

