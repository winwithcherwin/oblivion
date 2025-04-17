from rich import print
from datetime import datetime
import click


@click.group()
def cli():
    """Start server"""
    pass

@cli.command("ubuild")
def ubuild():
    """Run ubuild"""

    print("running ubuild...")
    while True:
        print(datetime.now())
        import time
        time.sleep(5)

