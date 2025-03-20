from celery import group
from celery.app.control import Inspect
from tasks import add  # Removed aggregate_results since we're handling it manually
from tasks import app

print(app.control.ping())

# Get all workers and their queues
inspect = app.control.inspect()
active_workers = inspect.active_queues()

if not active_workers:
    print("No active workers found!")
    exit()

# Extract unique queues
unique_queues = {queue["name"] for worker, queues in active_workers.items() for queue in queues}

print(f"Unique queues: {unique_queues}")

# 🚀 Create a group of tasks and assign queues dynamically
fanout_tasks = group(add.s(2, 3).set(queue=q) for q in unique_queues)

# 🎉 Execute tasks
result = fanout_tasks.apply_async()

# Collect and process results manually
final_output = sum(result.get(timeout=max(30, len(unique_queues) * 5)))

print(f"Sent fanout tasks to queues: {unique_queues}")
print(f"Final Output (Sum of Results): {final_output}")

