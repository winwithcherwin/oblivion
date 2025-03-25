#!/usr/bin/env python3
import os
import sys
import time
import redis
import terraform

from urllib.parse import urlparse, urlunparse

MAX_RETRIES = 5
INITIAL_DELAY = 1  # seconds


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


def try_connect(redis_uri: str):
    redis_uri_masked = mask_uri(redis_uri)

    for attempt in range(1, MAX_RETRIES + 5):
        try:
            print(f"Attempt {attempt} to connect to Redis at {redis_uri_masked}...")
            r = redis.Redis.from_url(redis_uri, socket_connect_timeout=2)
            r.ping()
            print("Redis connection successful.")
            return
        except redis.exceptions.ConnectionError as e:
            print(f"Connection failed: {e}")
            if attempt == MAX_RETRIES:
                raise Exception("Max retries reached. Giving up.")
            delay = INITIAL_DELAY * (2 ** (attempt - 1))
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)


def main():
    redis_uri = terraform.output(terraform.TARGET_DIR, "redis_uri")
    if is_invalid_uri(redis_uri):
        print(f"Invalid Redis URI: `{redis_uri}`. Refusing to connect to localhost or empty string.")
        sys.exit(1)

    try_connect(redis_uri)


if __name__ == "__main__":
    main()

