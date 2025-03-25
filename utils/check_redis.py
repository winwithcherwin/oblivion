#!/usr/bin/env python3
import os
import sys
import time
import redis
import logging

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_sleep_log

import terraform

from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

retry_connection_errors = [
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
    ConnectionRefusedError,
]

def mask_uri(uri: str) -> str:
    parsed = urlparse(uri)

    if parsed.username and parsed.password:
        netloc = f"{parsed.username}:***@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
    else:
        netloc = parsed.netloc

    return urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def is_invalid_uri(uri: str) -> bool:
    return not uri or "localhost" in uri or "127.0.0.1" in uri


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(retry_connection_errors),
    reraise=True
)
def connect(redis_uri: str):
    redis_uri_masked = mask_uri(redis_uri)

    r = redis.Redis.from_url(redis_uri, socket_connect_timeout=2)
    r.ping()

def main():
    redis_uri = terraform.output(terraform.TARGET_DIR, "redis_uri")
    if is_invalid_uri(redis_uri):
        print(f"Invalid Redis URI: `{redis_uri}`. Refusing to connect to localhost or empty string.")
        sys.exit(1)

    connect(redis_uri)


if __name__ == "__main__":
    main()

