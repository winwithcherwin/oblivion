import click
import uuid
import time
from functools import wraps
from rich import print as rich_print
from rich.text import Text

from oblivion.celery_app import app
from oblivion.core import terraform
from oblivion.control.runtime import (
    assert_equal,
    get_all_queues,
    follow_logs,
    NoQueuesFoundError,
)
from oblivion.settings import ENABLE_CLI_COLOR


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


def task_command(task, timeout=10):
    def decorator(f):
        @click.option("--queue", help="Target queue name")
        @click.option("--all", "fanout", is_flag=True, help="Run on all queues")
        @wraps(f)
        def wrapper(*args, queue=None, fanout=False, **kwargs):
            task_args = f(*args, **kwargs)
            if not fanout and not queue:
                raise click.ClickException("You must provide --queue <name> or use --all.")
            target_queues = (
                assert_equal(get_all_queues, terraform.get_all_hosts)
                if fanout
                else [queue]
            )
            results = []
            for q in target_queues:
                click.echo(f"→ Dispatching to: {q}")
                res = task.apply_async(args=task_args, queue=q)
                results.append((q, res))
            click.echo("\nResults:")
            for q, res in results:
                try:
                    out = res.get(timeout=timeout)
                    click.echo(f"{q}: {out}")
                except Exception as e:
                    click.echo(f"{q}: {e}")
        return wrapper
    return decorator


def streaming_ansible_task_command(task, timeout=5):
    """
    For Ansible-style tasks that return a dict with rc/status/stats/stdout.
    """
    def decorator(f):
        @click.option("--queue", help="Target queue name")
        @click.option("--all", "fanout", is_flag=True, help="Run on all queues")
        @wraps(f)
        def wrapper(*args, queue=None, fanout=False, **kwargs):
            if not fanout and not queue:
                raise click.ClickException("You must provide --queue <name> or use --all.")

            stream_id = str(uuid.uuid4())
            task_args = f(*args, **kwargs)
            task_kwargs = {"stream_id": stream_id}
            try:
                target_queues = (
                    assert_equal(get_all_queues, terraform.get_all_hosts)
                    if fanout
                    else [queue]
                )
            except Exception as e:
                raise click.ClickException(e)
            results = []
            start_time = time.monotonic()
            for q in target_queues:
                click.echo(f"→ Dispatching to: {q}")
                res = task.apply_async(args=task_args, kwargs=task_kwargs, queue=q)
                results.append((q, res))

            # Create an output function that applies host coloring and our formatting logic.
            output_fn = create_log_output_fn()
            follow_logs(stream_id, expected_hosts=target_queues, output_fn=output_fn)

            click.echo("\nSummary:")
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
            click.secho(f"\nTotal duration: {total_time:.2f}s", fg="cyan")
        return wrapper
    return decorator

