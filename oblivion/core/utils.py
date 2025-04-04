import requests

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

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=3).text.strip()
    except requests.RequestException as e:
        raise RuntimeError(f"Could not determine public IP: {e}")

