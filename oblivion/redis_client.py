import os
import redis
from urllib.parse import urlparse

from oblivion.settings import REDIS_URI
from oblivion.core.utils import mask_uri


redis_client = redis.Redis.from_url(
    REDIS_URI,
    decode_responses=False
)

