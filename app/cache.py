"""Cache and counters, with two interchangeable backends.

- MemoryBackend: lives inside one Python process. No setup needed.
- RedisBackend:  shared by every server process. Used when REDIS_URL is set.

Both have the same four methods, so the rest of the app does not care which one runs.
If Redis is down, RedisBackend logs a warning and the app keeps working without a cache.
"""
import logging
import math
import threading
import time
from typing import Optional, Tuple

import redis

from .config import settings

logger = logging.getLogger(__name__)

LEADERBOARD_KEY = "leaderboard:v1"


class MemoryBackend:
    def __init__(self):
        self._data = {}  # key -> (value, expires_at)
        self._counters = {}  # key -> (count, expires_at)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at <= time.monotonic():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            self._data[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def incr_window(self, key: str, window: int) -> Tuple[int, int]:
        """Count one hit in a fixed time window. Returns (hits so far, seconds left)."""
        now = time.monotonic()
        with self._lock:
            count, expires_at = self._counters.get(key, (0, 0.0))
            if expires_at <= now:
                count, expires_at = 0, now + window
            count += 1
            self._counters[key] = (count, expires_at)
            return count, max(1, math.ceil(expires_at - now))

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._counters.clear()


class RedisBackend:
    def __init__(self, client):
        self.client = client  # must be created with decode_responses=True

    def get(self, key: str) -> Optional[str]:
        try:
            return self.client.get(key)
        except redis.RedisError:
            logger.warning("Redis unavailable: cache get skipped", exc_info=True)
            return None  # behave like a cache miss

    def set(self, key: str, value: str, ttl: int) -> None:
        try:
            self.client.set(key, value, ex=ttl)
        except redis.RedisError:
            logger.warning("Redis unavailable: cache set skipped", exc_info=True)

    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except redis.RedisError:
            logger.warning("Redis unavailable: cache delete skipped", exc_info=True)

    def incr_window(self, key: str, window: int) -> Tuple[int, int]:
        try:
            # One atomic transaction: create the counter with an expiry if it is new,
            # add one, and read the time left. The expiry can never be forgotten.
            pipe = self.client.pipeline()
            pipe.set(key, 0, ex=window, nx=True)
            pipe.incr(key)
            pipe.ttl(key)
            _, count, ttl = pipe.execute()
            return int(count), max(int(ttl), 1)
        except redis.RedisError:
            logger.warning("Redis unavailable: rate limit skipped", exc_info=True)
            return 0, window  # fail open: let the request through


def build_cache():
    if settings.redis_url:
        client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,  # never let a dead Redis hang every request
            socket_timeout=1,
        )
        return RedisBackend(client)
    return MemoryBackend()


cache = build_cache()
