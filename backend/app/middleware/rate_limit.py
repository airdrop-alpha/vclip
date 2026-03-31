"""
VClip rate limiting — in-memory token bucket per API key or IP.

Uses slowapi (wraps limits library) for FastAPI. Falls back to a simple
in-memory counter if slowapi is not installed.

Phase 5 feature.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, status

from app.config import settings

logger = logging.getLogger(__name__)


# ── Simple in-memory rate limiter ────────────────────────────────

class _TokenBucket:
    """Thread-safe (enough for asyncio) token bucket per key."""

    def __init__(self, rate: float, burst: int):
        self.rate = rate        # tokens per second
        self.burst = burst      # max tokens (bucket capacity)
        self._buckets: dict[str, tuple[float, float]] = {}

    def _refill(self, key: str) -> float:
        """Return current token count after refill."""
        now = time.monotonic()
        tokens, last = self._buckets.get(key, (float(self.burst), now))
        elapsed = now - last
        tokens = min(self.burst, tokens + elapsed * self.rate)
        self._buckets[key] = (tokens, now)
        return tokens

    def consume(self, key: str, cost: float = 1.0) -> bool:
        """Consume tokens. Returns True if allowed, False if rate-limited."""
        tokens = self._refill(key)
        if tokens >= cost:
            tokens_after = tokens - cost
            self._buckets[key] = (tokens_after, time.monotonic())
            return True
        return False

    def cleanup(self, max_age: float = 3600.0) -> None:
        """Remove stale bucket entries."""
        now = time.monotonic()
        stale = [k for k, (_, ts) in self._buckets.items() if now - ts > max_age]
        for k in stale:
            del self._buckets[k]


# Global rate limiter instance
_limiter = _TokenBucket(
    rate=settings.rate_limit_rpm / 60.0,  # convert RPM → per second
    burst=settings.rate_limit_burst,
)


def _get_client_key(request: Request, api_key_id: Optional[str] = None) -> str:
    """Derive a rate-limit key from API key ID or IP address."""
    if api_key_id:
        return f"key:{api_key_id}"
    # X-Forwarded-For for proxy setups
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = (request.client.host if request.client else "unknown")
    return f"ip:{ip}"


async def check_rate_limit(
    request: Request,
    api_key_id: Optional[str] = None,
    cost: float = 1.0,
) -> None:
    """
    FastAPI dependency: enforce rate limiting.

    Raises HTTP 429 if the client exceeds their rate limit.

    Args:
        request: FastAPI Request object
        api_key_id: Optional API key ID (uses IP-based limiting if None)
        cost: Token cost for this request (default 1.0; expensive ops cost more)
    """
    client_key = _get_client_key(request, api_key_id)
    allowed = _limiter.consume(client_key, cost)

    if not allowed:
        # Calculate retry-after (approximately)
        retry_after = int(cost / _limiter.rate) + 1
        logger.warning(f"Rate limit exceeded for {client_key}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {settings.rate_limit_rpm} requests/minute.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(settings.rate_limit_rpm),
                "X-RateLimit-Reset": str(int(time.time()) + retry_after),
            },
        )
