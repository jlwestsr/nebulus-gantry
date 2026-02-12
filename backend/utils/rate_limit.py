"""In-memory rate limiter for login attempts.

Provides rate limiting keyed by **email address** (not IP), since a
dealership LAN behind NAT may share a single IP across all clients.
After exceeding a configurable number of failed attempts, the account
is locked out with escalating durations (capped at ~4 hours).

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

from fastapi import HTTPException

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

MAX_ESCALATION: Final[int] = 4
"""Maximum escalation exponent (caps lockout at base * 2^4 = ~4 hours)."""


@dataclass
class _AttemptRecord:
    """Tracks failed attempts and lockout state for a single email."""

    timestamps: list[float] = field(default_factory=list)
    lockout_until: float = 0.0
    escalation_count: int = 0


_store: dict[str, _AttemptRecord] = {}
_lock: threading.Lock = threading.Lock()
_last_cleanup: float = 0.0


# ---------------------------------------------------------------------------
# Public helpers (for use in login route)
# ---------------------------------------------------------------------------

def record_attempt(email: str) -> None:
    """Record a failed login attempt for *email*.

    Args:
        email: The email address used in the login attempt.
    """
    key = email.lower().strip()
    now = time.monotonic()
    with _lock:
        rec = _store.setdefault(key, _AttemptRecord())
        rec.timestamps.append(now)


def reset_attempts(email: str) -> None:
    """Clear all attempt history for *email* (e.g. after successful login).

    Args:
        email: The email address to reset.
    """
    key = email.lower().strip()
    with _lock:
        _store.pop(key, None)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def check_rate_limit_for_email(email: str) -> None:
    """Check if the given email is rate-limited. Raise 429 if so.

    Call this at the start of the login handler, before authentication.

    Usage::

        @router.post("/login")
        def login(credentials: LoginRequest, ...):
            check_rate_limit_for_email(credentials.email)
            ...

    Args:
        email: The email address from the login attempt.

    Raises:
        HTTPException: 429 Too Many Requests with a ``Retry-After`` header
            when the email has exceeded ``MAX_ATTEMPTS`` within ``WINDOW_SECONDS``.
    """
    key = email.lower().strip()
    now = time.monotonic()

    with _lock:
        _maybe_cleanup(now)
        rec = _store.get(key)
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
            # Escalating lockout: base * 2^escalation_count (capped)
            exp = min(rec.escalation_count, MAX_ESCALATION)
            duration = LOCKOUT_SECONDS * (2 ** exp)
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
    for key, rec in _store.items():
        # Safe to remove if not locked out and no recent timestamps
        if rec.lockout_until <= now:
            rec.timestamps = [t for t in rec.timestamps if t > cutoff]
            if not rec.timestamps:
                to_delete.append(key)
    for key in to_delete:
        del _store[key]


# ---------------------------------------------------------------------------
# Testing helpers
# ---------------------------------------------------------------------------

def _reset_store() -> None:
    """Clear all rate-limit state. For testing only."""
    global _last_cleanup
    with _lock:
        _store.clear()
        _last_cleanup = 0.0
