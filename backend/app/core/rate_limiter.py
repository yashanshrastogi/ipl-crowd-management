"""
Lightweight, thread-safe, in-memory Token Bucket rate limiter.
Avoids external dependencies like Redis for simple local deployments.

Includes stale key eviction (V-14) and proxy-aware IP extraction (V-15).
"""

from __future__ import annotations

import time
from threading import Lock

from fastapi import HTTPException, Request, status


class TokenBucketLimiter:
    """Thread-safe Token Bucket implementation for request throttling.

    Includes automatic eviction of stale entries to prevent unbounded
    memory growth (V-14).
    """

    def __init__(
        self, rate: float, capacity: float, max_keys: int = 100_000
    ) -> None:
        """Initialize the rate limiter.

        Parameters
        ----------
        rate : float
            Token generation rate (tokens per second).
        capacity : float
            Maximum bucket capacity (burst limit).
        max_keys : int
            Maximum number of tracked keys before forced eviction.
        """
        self.rate = rate
        self.capacity = capacity
        self.max_keys = max_keys
        # key -> (tokens, last_refill_time)
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = Lock()

    def _evict_stale(self, now: float) -> None:
        """Remove entries older than 10 minutes to prevent unbounded growth."""
        if len(self._buckets) <= self.max_keys:
            return
        cutoff = now - 600  # 10 minutes
        self._buckets = {
            k: v for k, v in self._buckets.items() if v[1] > cutoff
        }

    def consume(self, key: str, amount: float = 1.0) -> bool:
        """Attempt to consume tokens from the key's bucket.

        Returns True if successful, False if rate-limited.
        """
        with self._lock:
            now = time.time()
            self._evict_stale(now)

            if key in self._buckets:
                tokens, last_refill = self._buckets[key]
            else:
                tokens, last_refill = self.capacity, now

            elapsed = now - last_refill

            # Refill tokens based on time elapsed
            tokens = min(self.capacity, tokens + elapsed * self.rate)

            if tokens >= amount:
                tokens -= amount
                self._buckets[key] = (tokens, now)
                return True

            self._buckets[key] = (tokens, now)
            return False


# ── Limiter Instantiations ───────────────────────────────────────────────────

# Dispatch endpoint: 10 requests/min (0.1667 tokens/sec, capacity 10)
dispatch_limiter = TokenBucketLimiter(rate=10.0 / 60.0, capacity=10.0)

# Hazard Assessment endpoint: 20 requests/min (0.3333 tokens/sec, capacity 20)
assess_limiter = TokenBucketLimiter(rate=20.0 / 60.0, capacity=20.0)

# General endpoints: 120 requests/min (2.0 tokens/sec, capacity 120)
general_limiter = TokenBucketLimiter(rate=2.0, capacity=120.0)


# ── V-15: Proxy-aware client IP extraction ────────────────────────────────────

def _get_client_ip(request: Request) -> str:
    """Extract client IP respecting trusted proxy headers.

    Cloud Run, nginx, and most reverse proxies set X-Forwarded-For.
    We take the leftmost (client) IP from the header chain.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        # Take the leftmost (client) IP
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── FastAPI Dependencies ──────────────────────────────────────────────────────

async def limit_dispatch_rate(request: Request) -> None:
    """FastAPI dependency to rate limit agent dispatching."""
    ip = _get_client_ip(request)
    if not dispatch_limiter.consume(f"{ip}:dispatch"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for agent dispatch. Capped at 10 requests per minute.",
        )


async def limit_assessment_rate(request: Request) -> None:
    """FastAPI dependency to rate limit EvacuNet sensor assessments."""
    ip = _get_client_ip(request)
    if not assess_limiter.consume(f"{ip}:assess"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for hazard assessment. Capped at 20 requests per minute.",
        )


async def limit_general_rate(request: Request) -> None:
    """FastAPI dependency to rate limit generic API requests."""
    ip = _get_client_ip(request)
    if not general_limiter.consume(f"{ip}:general"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Capped at 120 requests per minute.",
        )
