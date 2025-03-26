import redis

from urllib.parse import urlparse, urlunparse


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

def validate_credentials(uri: str):
    #uri_masked = mask_uri(uri)
    #print(f"checking {uri_masked}")
    r = redis.Redis.from_url(uri, socket_connect_timeout=2)
    r.ping()
    test_key = "__redis_credentials_check__"
    r.set(test_key, "ok", ex=5)
    value = r.get(test_key)
    assert value == b"ok"

