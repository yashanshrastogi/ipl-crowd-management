"""
Lightweight, thread-safe, in-memory Token Bucket rate limiter.
Avoids external dependencies like Redis for simple local deployments.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status


class TokenBucketLimiter:
    """Thread-safe Token Bucket implementation for request throttling."""

    def __init__(self, rate: float, capacity: float) -> None:
        """Initialize the rate limiter.

        Parameters
        ----------
        rate : float
            Token generation rate (tokens per second).
        capacity : float
            Maximum bucket capacity (burst limit).
        """
        self.rate = rate
        self.capacity = capacity
        self._tokens: dict[str, float] = defaultdict(lambda: capacity)
        self._last_refill: dict[str, float] = defaultdict(time.time)
        self._lock = Lock()

    def consume(self, key: str, amount: float = 1.0) -> bool:
        """Attempt to consume tokens from the key's bucket.

        Returns True if successful, False if rate-limited.
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_refill[key]
            self._last_refill[key] = now

            # Refill tokens based on time elapsed
            self._tokens[key] = min(
                self.capacity,
                self._tokens[key] + elapsed * self.rate,
            )

            if self._tokens[key] >= amount:
                self._tokens[key] -= amount
                return True
            return False


# ── Limiter Instantiations ───────────────────────────────────────────────────

# Dispatch endpoint: 10 requests/min (0.1667 tokens/sec, capacity 10)
dispatch_limiter = TokenBucketLimiter(rate=10.0 / 60.0, capacity=10.0)

# Hazard Assessment endpoint: 20 requests/min (0.3333 tokens/sec, capacity 20)
assess_limiter = TokenBucketLimiter(rate=20.0 / 60.0, capacity=20.0)

# General endpoints: 120 requests/min (2.0 tokens/sec, capacity 120)
general_limiter = TokenBucketLimiter(rate=2.0, capacity=120.0)


# ── FastAPI Dependencies ──────────────────────────────────────────────────────

async def limit_dispatch_rate(request: Request) -> None:
    """FastAPI dependency to rate limit agent dispatching."""
    ip = request.client.host if request.client else "unknown"
    if not dispatch_limiter.consume(f"{ip}:dispatch"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for agent dispatch. Capped at 10 requests per minute.",
        )


async def limit_assessment_rate(request: Request) -> None:
    """FastAPI dependency to rate limit EvacuNet sensor assessments."""
    ip = request.client.host if request.client else "unknown"
    if not assess_limiter.consume(f"{ip}:assess"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for hazard assessment. Capped at 20 requests per minute.",
        )


async def limit_general_rate(request: Request) -> None:
    """FastAPI dependency to rate limit generic API requests."""
    ip = request.client.host if request.client else "unknown"
    if not general_limiter.consume(f"{ip}:general"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Capped at 120 requests per minute.",
        )
