import click
import re
from rich import print
from rich.pretty import pretty_repr
import inspect
from pathlib import Path
from lupa import LuaRuntime
import lupa
import importlib

from oblivion.core.ansible import stream_task

context = {}

interpolation_pattern = re.compile(r"\$\{([a-zA-Z0-9_]+)\}")

def resolve_args(args, context):
    resolved = {}
    for k, v in args.items():
        if callable(v):
            resolved[k] = v()  # <-- deferred
        elif isinstance(v, str) and interpolation_pattern.fullmatch(v.strip()):
            var_name = interpolation_pattern.fullmatch(v.strip()).group(1)
            resolved[k] = context[var_name]
        else:
            resolved[k] = v
    return resolved

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
    global lua_globals
    global lua_runtime

    def lua_table_to_dict(lua_table):
        return {k: lua_table[k] for k in lua_table.keys()}

    for i in range(1, len(steps) +1):
        raw_step = steps[i]
        if not raw_step:
            raise ValueError(f"Missing step at index {i}")

        step = lua_table_to_dict(raw_step)

        func_path = step["func"]

        if step.get("enabled") is False:
            print(f"[yellow][SKIP][/yellow] Skipping step {func_path}: disabled via `enabled = false`")
            continue

        explicit_args = resolve_args(step.get("args", {}), context)
        register = step.get("register")

        func = resolve_function(func_path)
        kwargs = extract_args(func, context, explicit_args)

        print(f"[bold green]{func_path}[/bold green]: [bold magenta]{kwargs}[/bold magenta]")
        result = func(**kwargs)

        if register:
            register = lua_table_to_dict(register)
            if isinstance(register, str):
                context[register] = result
                lua_globals[register] = result
            elif isinstance(register, dict):
                name = register.get("name")
                transform = register.get("transform")
                value = result
                if transform:
                    value = transform(result)
                print(value)
                context[name] = value
                lua_globals[name] = value
                print(f"[DEBUG] registered {name} with {value}")
        else:
            if isinstance(result, dict):
                context.update(result)

        results.append(result)

    return results

@click.command("run")
@click.argument("file", type=str, required=True)
def cli(file):
    """Run oblivion scripts"""
    global lua_globals
    global lua_runtime

    lua_runtime = LuaRuntime(unpack_returned_tuples=True)
    lua_globals = lua_runtime.globals()

    lua_runtime.globals().execute_pipeline = execute_pipeline_with_context
    lua_runtime.execute(Path("dsl.lua").read_text())

    code = Path(file).read_text()
    try:
        lua_runtime.execute(code)
    except lupa.lua54.LuaSyntaxError as e:
        raise click.ClickException(e)

