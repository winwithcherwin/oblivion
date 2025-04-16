import click
from pathlib import Path

from lupa import LuaRuntime


def hello_world(name=None):
    name = name or "World"
    print(f"Hello, {name}!")


@click.command("run")
@click.argument("file", type=str, required=True)
def cli(file):
    """Run oblivion scripts"""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().hello_world = hello_world
    lua.execute(Path("dsl.lua").read_text())
    lua.execute(Path(file).read_text())


