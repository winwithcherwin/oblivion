import click
import uuid
import redis
import json
import os
from functools import wraps
from rich import print as rich_print
from rich.text import Text

from oblivion.celery_app import app
from oblivion.redis_client import redis_client
from oblivion.settings import ENABLE_CLI_COLOR


def get_all_queues():
    inspect = app.control.inspect()
    queues = inspect.active_queues() or {}
    seen = set()
    for worker_queues in queues.values():
        for q in worker_queues:
            seen.add(q["name"])
    if not seen:
        raise click.ClickException("No active queues found.")
    return sorted(seen)


def follow_logs(stream_id, expected_hosts=None):
    click.echo(f"→ Live logs (stream ID: {stream_id})\n")
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"ansible:{stream_id}")

    seen_eof_hosts = set()
    expected_hosts = set(expected_hosts or [])

    host_colors = {}
    available_colors = ["cyan", "magenta", "green", "yellow", "blue", "bright_black"]
    max_colors = len(available_colors)
    seen_hosts = set()
    use_colors = ENABLE_CLI_COLOR

    try:
        for msg in pubsub.listen():
            if msg["type"] != "message":
                continue
            data = msg["data"].decode()
            try:
                parsed = json.loads(data)
                host = parsed.get("host", "unknown")
                if parsed.get("eof"):
                    seen_eof_hosts.add(host)
                    if expected_hosts and seen_eof_hosts >= expected_hosts:
                        break
                    continue
                line = parsed.get("line", "")
            except json.JSONDecodeError:
                click.echo(data)
                continue

            # Assign color per host unless too many
            if host not in host_colors and use_colors:
                seen_hosts.add(host)
                if len(seen_hosts) > max_colors:
                    use_colors = False
                else:
                    host_colors[host] = available_colors[len(host_colors)]

            color = host_colors.get(host, None) if use_colors else None
            prefix = f"[{host}] "

            for subline in line.splitlines():
                subline = subline.rstrip()
                if not subline:
                    continue

                # Prevent double prefix only if it already starts with [host]
                if subline.startswith(f"ok: [{host}]") or subline.startswith(f"changed: [{host}]"):
                    text = Text(subline)
                elif subline.startswith("ok: [") or subline.startswith("changed: ["):
                    text = Text(subline)
                else:
                    text = Text(f"{prefix}{subline}")

                if color:
                    text.stylize(color)
                rich_print(text)

    except KeyboardInterrupt:
        click.echo("Stopped log stream")
    except redis.exceptions.RedisError as e:
        click.echo(f"Redis error: {e}")
    finally:
        click.echo("")
        pubsub.unsubscribe()


def task_command(task, timeout=10):
    def decorator(f):
        @click.option("--queue", help="Target queue name")
        @click.option("--all", "fanout", is_flag=True, help="Run on all queues")
        @wraps(f)
        def wrapper(*args, queue=None, fanout=False, **kwargs):
            task_args = f(*args, **kwargs)

            if not fanout and not queue:
                raise click.ClickException("You must provide --queue <name> or use --all.")

            target_queues = get_all_queues() if fanout else [queue]
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


def streaming_ansible_task_command(task, timeout=10):
    """
    For Ansible-style tasks that return a dict with rc/status/stats/stdout/duration
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

            target_queues = get_all_queues() if fanout else [queue]
            results = []
            for q in target_queues:
                click.echo(f"→ Dispatching to: {q}")
                res = task.apply_async(args=task_args, kwargs=task_kwargs, queue=q)
                results.append((q, res))

            follow_logs(stream_id, expected_hosts=target_queues)

            # Expect Ansible-style dict result
            click.echo("\nResults:")
            for q, res in results:
                try:
                    result = res.get(timeout=timeout)
                    rc = result.get("rc")
                    status = result.get("status")
                    stats = result.get("stats") or {}
                    duration = result.get("duration")
                    duration_str = f"{duration:.2f}s" if duration is not None else "?"

                    summary = f"ok={stats.get('ok', 0)} changed={stats.get('changed', 0)} " \
                              f"failed={stats.get('failures', 0)} duration={duration_str}"

                    color = "green" if rc == 0 else "red"
                    click.secho(f"{q}: rc={rc} status={status} summary={summary}", fg=color)
                except Exception as e:
                    click.echo(f"{q}: {e}")
        return wrapper
    return decorator

