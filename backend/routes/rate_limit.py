from collections import defaultdict
import time as _time


class RateLimiter:
    def __init__(self, max_calls: int = 10, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self._calls = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = _time.time()
        self._calls[key] = [t for t in self._calls[key] if now - t < self.period]
        if len(self._calls[key]) >= self.max_calls:
            return False
        self._calls[key].append(now)
        return True


ai_limiter = RateLimiter(max_calls=20, period=60)
upload_limiter = RateLimiter(max_calls=5, period=60)
