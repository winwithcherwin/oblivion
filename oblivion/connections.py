from oblivion.settings import REDIS_URI


def get_redis_client():
    if not REDIS_URI:
        raise ValueError("REDIS_URI is not configured")
    return redis.Redis.from_url(REDIS_URI)
