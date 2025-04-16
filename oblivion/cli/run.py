import click
from pathlib import Path
from lupa import LuaRuntime
import lupa
import importlib

from oblivion.core.ansible import stream_task

context = {}

def unseal_vault():
    vault_addr = "https://vault.example.com"
    vault_token = "s.XYZ"
    context["vault_addr"] = vault_addr
    context["vault_token"] = vault_token
    return {"vault_addr": vault_addr, "vault_token": vault_token}

def create_approle(role_name, foo):
    vault_addr = context.get("vault_addr")
    vault_token = context.get("vault_token")
    if not (vault_addr and vault_token):
        raise Exception("Vault not unsealed yet")
    approle_id = f"generated-approle-id-for-{role_name}"
    context["approle_id"] = approle_id
    return {"approle_id": approle_id}

AVAILABLE_FUNCTIONS = {
    "unseal_vault": unseal_vault,
    "create_approle": create_approle,
    "stream_task": stream_task,
}

def resolve_function(func_path):
    module_path, func_name = func_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    return func

def execute_pipeline(steps):
    results = []
    for step in steps.values():
        func_path = step["func"]
        args = step["args"] if "args" in step else {}
        
        func = resolve_function(func_path)
        result = func(**args)
        results.append(result)
    return results


@click.command("run")
@click.argument("file", type=str, required=True)
def cli(file):
    """Run oblivion scripts"""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().unseal_vault = unseal_vault
    lua.globals().create_approle = create_approle
    lua.globals().execute_pipeline = execute_pipeline
    lua.execute(Path("dsl.lua").read_text())

    code = Path(file).read_text()
    try:
        lua.execute(code)
    except lupa.lua54.LuaSyntaxError as e:
        raise click.ClickException(e)


