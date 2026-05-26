from __future__ import annotations

from app.core.rate_limiter import TokenBucketLimiter, _get_client_ip


class DummyClient:
    host = "10.0.0.5"


class DummyRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}
        self.client = DummyClient()


def test_token_bucket_blocks_after_capacity_is_consumed():
    limiter = TokenBucketLimiter(rate=0.0, capacity=2.0)

    assert limiter.consume("client") is True
    assert limiter.consume("client") is True
    assert limiter.consume("client") is False


def test_token_bucket_evicts_stale_entries():
    limiter = TokenBucketLimiter(rate=1.0, capacity=1.0, max_keys=1)
    limiter._buckets = {
        "old": (0.0, 1.0),
        "fresh": (1.0, 1_200.0),
    }

    limiter._evict_stale(1_700.0)

    assert "old" not in limiter._buckets
    assert "fresh" in limiter._buckets


def test_client_ip_prefers_leftmost_forwarded_for():
    request = DummyRequest(headers={"X-Forwarded-For": "203.0.113.10, 10.0.0.1"})

    assert _get_client_ip(request) == "203.0.113.10"


def test_client_ip_falls_back_to_socket_client():
    assert _get_client_ip(DummyRequest()) == "10.0.0.5"
