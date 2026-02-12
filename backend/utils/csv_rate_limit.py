"""Sliding-window rate limiter for CSV endpoints.

Separate from the auth rate limiter (which uses escalating lockouts for
login brute-force protection). This module provides simple per-user,
per-endpoint rate limiting with configurable requests-per-window.

Like the auth rate limiter, this is keyed by email (not IP) since
dealership LAN clients share a NAT IP. State is per-worker/in-memory.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Final

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

UPLOAD_MAX_REQUESTS: Final[int] = 10
"""Max upload requests per user per window."""

UPLOAD_WINDOW_SECONDS: Final[int] = 60
"""Window duration for upload rate limiting."""

ANALYZE_MAX_REQUESTS: Final[int] = 20
"""Max analyze requests per user per window."""

ANALYZE_WINDOW_SECONDS: Final[int] = 60
"""Window duration for analyze rate limiting."""

CLEANUP_INTERVAL: Final[int] = 300
"""Seconds between expired-entry cleanup sweeps."""


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass
class _SlidingWindow:
    """Tracks request timestamps for a single user+endpoint."""
    timestamps: list[float] = field(default_factory=list)


# Separate stores for upload vs analyze
_upload_store: dict[str, _SlidingWindow] = {}
_analyze_store: dict[str, _SlidingWindow] = {}
_lock: threading.Lock = threading.Lock()
_last_cleanup: float = 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_csv_upload_rate_limit(email: str) -> None:
    """Check upload rate limit for the given user email.

    Raises:
        HTTPException: 429 if the user has exceeded the upload rate limit.
    """
    _check_limit(
        email,
        store=_upload_store,
        max_requests=UPLOAD_MAX_REQUESTS,
        window_seconds=UPLOAD_WINDOW_SECONDS,
        action="upload CSV files",
    )


def check_csv_analyze_rate_limit(email: str) -> None:
    """Check analyze rate limit for the given user email.

    Raises:
        HTTPException: 429 if the user has exceeded the analyze rate limit.
    """
    _check_limit(
        email,
        store=_analyze_store,
        max_requests=ANALYZE_MAX_REQUESTS,
        window_seconds=ANALYZE_WINDOW_SECONDS,
        action="analyze CSV files",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_limit(
    email: str,
    *,
    store: dict[str, _SlidingWindow],
    max_requests: int,
    window_seconds: int,
    action: str,
) -> None:
    """Sliding-window rate limit check. Records the request if allowed."""
    key = email.lower().strip()
    now = time.monotonic()

    with _lock:
        _maybe_cleanup(now)
        window = store.setdefault(key, _SlidingWindow())
        cutoff = now - window_seconds
        window.timestamps = [t for t in window.timestamps if t > cutoff]

        if len(window.timestamps) >= max_requests:
            # Find when the earliest request in the window expires
            retry_after = int(window.timestamps[0] - cutoff) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded: max {max_requests} requests per "
                    f"{window_seconds}s to {action}. Try again later."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        window.timestamps.append(now)


def _maybe_cleanup(now: float) -> None:
    """Remove expired entries periodically. Must hold ``_lock``."""
    global _last_cleanup
    if now - _last_cleanup < CLEANUP_INTERVAL:
        return
    _last_cleanup = now

    for store in (_upload_store, _analyze_store):
        to_delete: list[str] = []
        for key, window in store.items():
            # Keep only if there are recent timestamps
            cutoff = now - max(UPLOAD_WINDOW_SECONDS, ANALYZE_WINDOW_SECONDS)
            window.timestamps = [t for t in window.timestamps if t > cutoff]
            if not window.timestamps:
                to_delete.append(key)
        for key in to_delete:
            del store[key]


# ---------------------------------------------------------------------------
# Testing helpers
# ---------------------------------------------------------------------------

def _reset_store() -> None:
    """Clear all CSV rate-limit state. For testing only."""
    global _last_cleanup
    with _lock:
        _upload_store.clear()
        _analyze_store.clear()
        _last_cleanup = 0.0
