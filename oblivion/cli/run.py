import click
from rich import print
from rich.pretty import pretty_repr
import inspect
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

def extract_args(func, previous_output, explicit_args=None):
    sig = inspect.signature(func)
    kwargs = {}

    # Start with explicit args
    if explicit_args:
        kwargs.update(explicit_args)

    # Fill in missing kwargs from previous output
    for name in sig.parameters:
        if name not in kwargs and previous_output and name in previous_output:
            kwargs[name] = previous_output[name]

    return kwargs

def execute_pipeline_with_context(steps):
    results = []
    global context

    for step in steps.values():
        func_path = step["func"]
        explicit_args = step["args"] if "args" in step else {}

        func = resolve_function(func_path)
        kwargs = extract_args(func, context, explicit_args)
        print(f"[bold green]{func_path}[/bold green]:[bold magenta]{kwargs}")

        result = func(**kwargs)

        # Save output for next step
        if isinstance(result, dict):
            context.update(result)
        results.append(result)

    return results

def execute_pipeline(steps):
    results = []
    previous_output = {}

    for step in steps.values():
        func_path = step["func"]
        explicit_args = step["args"] if "args" in step else {}

        func = resolve_function(func_path)
        kwargs = extract_args(func, previous_output, explicit_args)
        result = func(**kwargs)

        # Save output for next step
        if isinstance(result, dict):
            previous_output.update(result)
        results.append(result)
    print(previous_output)

    return results

def unset(key):
    global context
    print(context)

@click.command("run")
@click.argument("file", type=str, required=True)
def cli(file):
    """Run oblivion scripts"""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().unseal_vault = unseal_vault
    lua.globals().create_approle = create_approle
    lua.globals().execute_pipeline = execute_pipeline_with_context
    lua.globals().unset = unset
    lua.execute(Path("dsl.lua").read_text())

    code = Path(file).read_text()
    try:
        lua.execute(code)
    except lupa.lua54.LuaSyntaxError as e:
        raise click.ClickException(e)


