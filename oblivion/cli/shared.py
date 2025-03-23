import click
import uuid
import redis
import json

from functools import wraps
from rich.console import Console
from rich.text import Text
from oblivion.celery_app import app
from oblivion.redis_client import redis_client

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

from rich.console import Console
from rich.text import Text
import json
import hashlib

def get_color_for_host(host):
    """Hash hostname to a stable HSL color."""
    hash_val = int(hashlib.md5(host.encode()).hexdigest(), 16)
    hue = hash_val % 360
    return f"hsl({hue}, 70%, 60%)"

def follow_logs(stream_id):
    console = Console()
    console.print(f"[bold cyan]→ Live logs (stream ID: {stream_id})[/bold cyan]\n")

    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"ansible:{stream_id}")

    try:
        for msg in pubsub.listen():
            if msg["type"] != "message":
                continue

            data = msg["data"].decode()
            if data == "__EOF__":
                break

            try:
                payload = json.loads(data)
                host = payload.get("host", "unknown")
                line = payload.get("line", "").rstrip()

                color = get_color_for_host(host)
                prefix = f"[{host}]"
                text = Text.assemble((prefix, color), (" ",), (line, ""))
                console.print(text)
            except json.JSONDecodeError:
                # fallback for old unstructured messages
                console.print(data.rstrip())

    except KeyboardInterrupt:
        console.print("[yellow]Stopped log stream[/yellow]")
    except redis.exceptions.RedisError as e:
        console.print(f"[red]Redis error: {e}[/red]")
    finally:
        console.print()
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
    For Ansible-style tasks that return a dict with rc/status/stats/stdout
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

            follow_logs(stream_id)

            # Expect Ansible-style dict result
            click.echo("\nResults:")
            for q, res in results:
                try:
                    result = res.get(timeout=timeout)
                    rc = result.get("rc")
                    status = result.get("status")
                    color = "green" if rc == 0 else "red"
                    stats = result.get("stats")
                    click.secho(f"{q}: rc={rc} status={status} summary={stats}", fg=color)
                except Exception as e:
                    click.echo(f"{q}: {e}")
        return wrapper
    return decorator

