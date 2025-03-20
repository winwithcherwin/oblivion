from tasks import app

# send to all hosts
result = app.send_task("tasks.add", args=[100, 100], queue="server-1")
print(result.get())

# send to specific host
result = app.send_task("tasks.subtract", args=[4, 5], queue="server-0")
print(result.get())

