from celery import Celery
import ssl
import os

from oblivion.settings import REDIS_URI


app = Celery("oblivion",
  broker=REDIS_URI,
  backend=REDIS_URI,
  redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
)

import oblivion.engine.ansible.tasks
import oblivion.engine.wireguard.tasks

app.conf.task_time_limit = 300
app.autodiscover_tasks([
    "oblivion.engine",
    "oblivion.engine.ansible",
    "oblivion.engine.wireguard",
])

