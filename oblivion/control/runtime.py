import json
import logging
import redis
import kombu
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_sleep_log

from oblivion.celery_app import app
from oblivion.redis_client import redis_client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class NoQueuesFoundError(Exception):
    def __init__(self, message="No active queues found."):
        super().__init__(message)
        self.message = message


retry_connection_errors = (
    ConnectionRefusedError,
    NoQueuesFoundError,
    kombu.exceptions.OperationalError,
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(AssertionError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def assert_equal(func1, func2):
    """
    Retry-safe assertion that the results of two functions are equal.
    """
    value1 = func1()
    value2 = func2()
    logger.info("Asserting equality: %s vs %s", value1, value2)
    assert value1 == value2, f"mismatch:\n{func1.__name__}: {value1}\n{func2.__name__}: {value2}"
    return value1


@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(retry_connection_errors),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def get_all_queues():
    """
    Retrieve and return a sorted list of all active queues.
    Raises NoQueuesFoundError if no queues are found.
    """
    inspect = app.control.inspect()
    queues = inspect.active_queues() or {}
    seen = set()
    for worker_queues in queues.values():
        for q in worker_queues:
            seen.add(q["name"])
    if not seen:
        raise NoQueuesFoundError()
    return sorted(seen)


def follow_logs(stream_id, expected_hosts=None, block_timeout=30000, output_fn=print):
    """
    Consume Ansible logs from a Redis stream in a blocking manner using XREAD.
    
    Args:
        stream_id (str): Identifier for the Redis stream.
        expected_hosts (list, optional): List of hosts to wait for an EOF signal.
        block_timeout (int): Timeout (in milliseconds) for blocking XREAD.
        output_fn (callable): Callback to output each processed log message.
            This callback receives a dict with keys such as:
              - "hostname": the host name (or None for control messages)
              - "line": the log text
              - (additional keys can be added later)
    
    For each incoming log message, we remove extra whitespace and then call the
    output callback with a dictionary that includes the hostname and the log line.
    """
    output_fn({"hostname": None, "line": f"→ Live logs (stream ID: {stream_id})\n"})
    stream_key = f"ansible:{stream_id}"
    last_id = "0-0"
    expected_hosts = set(expected_hosts or [])
    seen_eof_hosts = set()

    try:
        while True:
            result = redis_client.xread({stream_key: last_id}, block=block_timeout, count=1)
            if not result:
                output_fn({"hostname": None, "line": "No messages received within the timeout period. Exiting log stream."})
                break

            for key, messages in result:
                for message_id, message_data in messages:
                    last_id = message_id  # Update last seen message ID.
                    data = message_data.get(b"data")
                    try:
                        parsed = json.loads(data.decode())
                        hostname = parsed.get("hostname", "unknown")
                    except json.JSONDecodeError:
                        output_fn({"hostname": None, "line": f"Error decoding message: {data}"})
                        continue
                    except Exception as e:
                        output_fn({"hostname": None, "line": f"Error processing message: {e}"})
                        continue

                    if parsed.get("eof"):
                        seen_eof_hosts.add(hostname)
                        if expected_hosts and seen_eof_hosts >= expected_hosts:
                            output_fn({"hostname": None, "line": "Received EOF from all expected hosts. Exiting log stream."})
                            return
                        if not expected_hosts:
                            output_fn({"hostname": None, "line": "Received EOF. Exiting log stream."})
                            return
                        continue

                    # Remove extra newlines.
                    line = parsed.get("line", "").strip()
                    if not line:
                        continue

                    # Call the output callback with a dictionary containing the hostname and line.
                    output_fn({"hostname": hostname, "line": line})
    except KeyboardInterrupt:
        output_fn({"hostname": None, "line": "Stopped log stream"})
    except redis.exceptions.RedisError as e:
        output_fn({"hostname": None, "line": f"Redis error: {e}"})
    finally:
        output_fn({"hostname": None, "line": ""})

