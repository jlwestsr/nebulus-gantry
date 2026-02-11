"""In-memory rate limiter for login attempts.

Provides a FastAPI dependency that blocks IPs exceeding a configurable
number of failed login attempts within a sliding time window. After lockout
expires, subsequent bursts trigger escalating lockout durations.

Note:
    This rate limiter is per-worker. With multiple uvicorn workers, each
    maintains its own counter. This means the effective limit is
    ``max_attempts * num_workers`` in the worst case. This is acceptable
    for the LAN-only threat model of the MVA appliance, where brute-force
    attacks are unlikely and the attacker would need local network access.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Final

from fastapi import HTTPException, Request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_ATTEMPTS: Final[int] = 5
"""Maximum failed attempts before lockout."""

WINDOW_SECONDS: Final[int] = 300
"""Sliding window (seconds) in which attempts are counted."""

LOCKOUT_SECONDS: Final[int] = 900
"""Base lockout duration (seconds) after exceeding max attempts."""

CLEANUP_INTERVAL: Final[int] = 600
"""Minimum seconds between automatic expired-entry cleanup sweeps."""


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass
class _AttemptRecord:
    """Tracks failed attempts and lockout state for a single IP."""

    timestamps: list[float] = field(default_factory=list)
    lockout_until: float = 0.0
    escalation_count: int = 0


_store: dict[str, _AttemptRecord] = {}
_lock: threading.Lock = threading.Lock()
_last_cleanup: float = 0.0


# ---------------------------------------------------------------------------
# Public helpers (for use in login route)
# ---------------------------------------------------------------------------

def record_attempt(ip: str) -> None:
    """Record a failed login attempt for *ip*.

    Args:
        ip: The client IP address.
    """
    now = time.monotonic()
    with _lock:
        rec = _store.setdefault(ip, _AttemptRecord())
        rec.timestamps.append(now)


def reset_attempts(ip: str) -> None:
    """Clear all attempt history for *ip* (e.g. after successful login).

    Args:
        ip: The client IP address.
    """
    with _lock:
        _store.pop(ip, None)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def check_rate_limit(request: Request) -> None:
    """FastAPI dependency that raises HTTP 429 if the client IP is rate-limited.

    Usage::

        @router.post("/login")
        def login(
            ...,
            _rate: None = Depends(check_rate_limit),
        ):
            ...

    Args:
        request: The incoming FastAPI request (injected automatically).

    Raises:
        HTTPException: 429 Too Many Requests with a ``Retry-After`` header
            when the IP has exceeded ``MAX_ATTEMPTS`` within ``WINDOW_SECONDS``.
    """
    ip = _get_client_ip(request)
    now = time.monotonic()

    with _lock:
        _maybe_cleanup(now)
        rec = _store.get(ip)
        if rec is None:
            return

        # Currently locked out?
        if now < rec.lockout_until:
            retry_after = int(rec.lockout_until - now) + 1
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        # Prune timestamps outside the window
        cutoff = now - WINDOW_SECONDS
        rec.timestamps = [t for t in rec.timestamps if t > cutoff]

        # Check if limit exceeded
        if len(rec.timestamps) >= MAX_ATTEMPTS:
            # Escalating lockout: base * 2^escalation_count
            duration = LOCKOUT_SECONDS * (2 ** rec.escalation_count)
            rec.lockout_until = now + duration
            rec.escalation_count += 1
            rec.timestamps.clear()
            retry_after = int(duration) + 1
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client_ip(request: Request) -> str:
    """Extract client IP from the request.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The client IP as a string.
    """
    # Trust X-Forwarded-For only if behind a known reverse proxy;
    # for LAN-only appliance, client.host is sufficient.
    if request.client:
        return request.client.host
    return "unknown"


def _maybe_cleanup(now: float) -> None:
    """Remove expired entries periodically to prevent memory leaks.

    Must be called while holding ``_lock``.

    Args:
        now: Current monotonic timestamp.
    """
    global _last_cleanup
    if now - _last_cleanup < CLEANUP_INTERVAL:
        return
    _last_cleanup = now

    cutoff = now - WINDOW_SECONDS
    to_delete: list[str] = []
    for ip, rec in _store.items():
        # Safe to remove if not locked out and no recent timestamps
        if rec.lockout_until <= now:
            rec.timestamps = [t for t in rec.timestamps if t > cutoff]
            if not rec.timestamps:
                to_delete.append(ip)
    for ip in to_delete:
        del _store[ip]


# ---------------------------------------------------------------------------
# Testing helpers
# ---------------------------------------------------------------------------

def _reset_store() -> None:
    """Clear all rate-limit state. For testing only."""
    global _last_cleanup
    with _lock:
        _store.clear()
        _last_cleanup = 0.0
