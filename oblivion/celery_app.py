from celery import Celery
import ssl
import os

redis_uri = os.getenv("REDIS_URI")

app = Celery("oblivion",
  broker=redis_uri,
  backend=redis_uri,
  redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
)

app.conf.task_time_limit = 300
app.autodiscover_tasks(["oblivion.engine"])

