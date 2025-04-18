from rich import print
from datetime import datetime
from oblivion import VERSION
import click


@click.group()
def cli():
    """Start server"""
    pass

@cli.command("ubuild")
def ubuild():
    """Run ubuild"""

    print(f"running ubuild v{VERSION}...")
    while True:
        print(datetime.now())
        import time
        time.sleep(5)

