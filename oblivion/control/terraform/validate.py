from oblivion import core
import redis

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_sleep_log

retry_connection_errors = (
    AssertionError,
    ConnectionRefusedError,
    redis.exceptions.ConnectionError,
    redis.exceptions.ResponseError,
    redis.exceptions.TimeoutError,
)
@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(retry_connection_errors),
    reraise=True
)
def redis_uri():
    uri = core.terraform.output(key="redis_uri")
    if uri is None:
        raise Exception("redis_uri not found. provision with terraform first")
    core.redis.validate_credentials(uri)

