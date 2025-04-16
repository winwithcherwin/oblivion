import uuid
import time

from functools import wraps
from rich import print as rich_print
from rich.text import Text

from oblivion.celery_app import app
from oblivion.core import terraform
from oblivion.engine.ansible import run_playbook_locally

from oblivion.control.runtime import (
    assert_equal,
    get_all_queues,
    follow_logs,
    NoQueuesFoundError,
)
from oblivion.settings import ENABLE_CLI_COLOR


def resolve_callback(path, kwargs):
    module_path, func_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    return func(**kwargs)

def create_log_output_fn():
    """
    Returns an output callback that applies host-based color formatting.
    This callback receives a dictionary with keys "hostname" and "line".

    If "hostname" is None, the line is treated as a control message and printed as-is.
    Otherwise, if the line (within its first 30 characters) already contains the hostname
    (in the form "[hostname]"), it is output unchanged; if not, the prefix "[hostname] " is added.
    Finally, a color (if enabled) is applied based on the hostname.
    """
    host_colors = {}
    available_colors = ["cyan", "magenta", "green", "yellow", "blue", "bright_black"]
    max_colors = len(available_colors)
    seen_hosts = set()
    use_colors = ENABLE_CLI_COLOR

    def output_fn(msg):
        hostname = msg.get("hostname")
        line = msg.get("line", "").rstrip()

        if hostname is None:
            rich_print(line)
            return

        # Check if the line already contains the hostname (in brackets)
        # within the first 30 characters.
        if f"[{hostname}]" in line[:30]:
            final_line = line
        else:
            final_line = f"[{hostname}] {line}"

        # Apply host-based color formatting.
        if hostname not in host_colors and use_colors:
            seen_hosts.add(hostname)
            if len(seen_hosts) > max_colors:
                host_colors[hostname] = None
            else:
                host_colors[hostname] = available_colors[len(host_colors)]
        color = host_colors.get(hostname)
        text = Text(final_line)
        if color:
            text.stylize(color)
        rich_print(text)

    return output_fn



def stream_task(*args, queue=None, fanout=False, **kwargs):
    if not fanout and not queue:
        raise Exception("You must provide --queue <name> or use --all.")

    playbook_path = kwargs["playbook_path"]
    base_vars = kwargs.get("extra_vars", {})
    callback_chain = kwargs.get("extra_vars_callback", [])

    target_queues = (
        assert_equal(get_all_queues, terraform.get_all_hosts)
        if fanout else [queue]
    )

    results = []
    stream_id = str(uuid.uuid4())
    start_time = time.monotonic()

    for q in target_queues:
        chained_vars = {}
        for path, cb_kwargs in callback_chain:
            combined_kwargs = {**chained_vars, **cb_kwargs}
            cb_result = resolve_callback(path, combined_kwargs)
            chained_vars.update(cb_result)

        chained_vars.pop("vault_token", None)
        final_vars = {**base_vars, **chained_vars}

        task_kwargs = {
            "playbook_path": playbook_path,
            "extra_vars": final_vars,
            "stream_id": stream_id,
        }

        print(f"→ Dispatching to: {q}")
        res = run_playbook_locally.apply_async(args=(), kwargs=task_kwargs, queue=q)
        results.append((q, res))

    output_fn = create_log_output_fn()
    follow_logs(stream_id, expected_hosts=target_queues, output_fn=output_fn)

    print("\nSummary:")
    timeout = 5
    for q, res in results:
        try:
            result = res.get(timeout=timeout)
            rc = result.get("rc")
            stats = result.get("stats") or {}
            duration = result.get("duration", "?")
            ok = stats.get("ok", 0)
            changed = stats.get("changed", 0)
            failed = stats.get("failures", 0)
            duration_str = (
                f"{duration:.2f}s" if isinstance(duration, (int, float)) else str(duration)
            )
            symbol = "✓" if rc == 0 else "✗"
            color = "green" if rc == 0 else "red"
            rich_print(
                f"[{color}]{symbol} {q} | rc={rc} | {duration_str} | ok={ok} changed={changed} failed={failed}[/{color}]"
            )
        except Exception as e:
            rich_print(f"[red]✗ {q} | error: {e}[/red]")

    total_time = time.monotonic() - start_time
    print(f"\nTotal duration: {total_time:.2f}s")

