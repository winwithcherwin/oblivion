from celery import group, chord
from celery.app.control import Inspect
from tasks import add, aggregate_results  # Import the new function
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

# 🎉 Use chord() with the aggregator function
result = chord(fanout_tasks)(aggregate_results.s())

# Get results
final_output = result.get()

print(f"Sent fanout tasks to queues: {unique_queues}")
print(f"Final Output: {final_output}")
