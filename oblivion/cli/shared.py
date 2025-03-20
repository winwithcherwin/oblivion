import click
from functools import wraps
from oblivion.celery_app import app

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
                    click.echo(f"{q}: ✅ {out}")
                except Exception as e:
                    click.echo(f"{q}: ❌ {e}")
        return wrapper
    return decorator

