import time
from celery import group
from celery.app.control import Inspect
from tasks import add
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

# 🚀 Create and execute a group of tasks dynamically
fanout_tasks = group(add.s(2, 3).set(queue=q) for q in unique_queues)
result = fanout_tasks.apply_async()

# 🎉 Stream results as they complete
final_output = []
pending_tasks = result.results  # List of AsyncResult objects

print("Waiting for results...")

while pending_tasks:
    for task in pending_tasks[:]:  # Iterate over a copy to modify the list safely
        if task.ready():  # Check if task is complete
            output = task.get()
            final_output.append(output)
            print(f"Task {task.id} completed with result: {output}")
            pending_tasks.remove(task)  # Remove completed task
    
    time.sleep(1)  # Prevent excessive polling

print(f"Final Output (Sum of Results): {sum(final_output)}")

