from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = 60.0
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > window:
                bucket.popleft()
            if len(bucket) >= self.per_minute:
                return False
            bucket.append(now)
            return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > 60.0:
                bucket.popleft()
            return max(0, self.per_minute - len(bucket))
