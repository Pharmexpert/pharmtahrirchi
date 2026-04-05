"""Tests for rate limiting module."""
from routes.rate_limit import RateLimiter


class TestRateLimiter:
    def test_allows_within_limit(self):
        limiter = RateLimiter(max_calls=3, period=60)
        assert limiter.is_allowed("ip1") is True
        assert limiter.is_allowed("ip1") is True
        assert limiter.is_allowed("ip1") is True

    def test_blocks_over_limit(self):
        limiter = RateLimiter(max_calls=2, period=60)
        assert limiter.is_allowed("ip1") is True
        assert limiter.is_allowed("ip1") is True
        assert limiter.is_allowed("ip1") is False

    def test_different_keys_independent(self):
        limiter = RateLimiter(max_calls=1, period=60)
        assert limiter.is_allowed("ip1") is True
        assert limiter.is_allowed("ip2") is True
        assert limiter.is_allowed("ip1") is False
        assert limiter.is_allowed("ip2") is False

    def test_expired_calls_cleaned(self):
        import time
        limiter = RateLimiter(max_calls=1, period=0.1)  # 100ms period
        assert limiter.is_allowed("ip1") is True
        assert limiter.is_allowed("ip1") is False
        time.sleep(0.15)
        assert limiter.is_allowed("ip1") is True  # Should be allowed after expiry
