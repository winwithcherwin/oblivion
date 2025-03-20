import ssl
import os
from celery import Celery

redis_uri = os.getenv("REDIS_URI")

app = Celery("oblivion",
    broker=redis_uri,
    backend=redis_uri,
    redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
)

app.conf.result_backend_transport_options = {"visibility_timeout": 300}
app.conf.task_time_limit = 300

@app.task
def aggregate_results(results):
    return sum(results)

@app.task
def add(x, y):
  return x + y

@app.task
def subtract(x, y):
  return x - y

