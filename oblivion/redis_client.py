import os
import redis
from urllib.parse import urlparse

from oblivion.settings import REDIS_URI

if not REDIS_URI:
    raise RuntimeError("REDIS_URI environment variable not set")

redis_client = redis.Redis.from_url(
    REDIS_URI,
    decode_responses=False
)

