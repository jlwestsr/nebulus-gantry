"""Tests for the email-based rate limiter."""

import threading
import time
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.utils.rate_limit import (
    LOCKOUT_SECONDS,
    MAX_ATTEMPTS,
    MAX_ESCALATION,
    WINDOW_SECONDS,
    CLEANUP_INTERVAL,
    _reset_store,
    _store,
    check_rate_limit_for_email,
    record_attempt,
    reset_attempts,
)


@pytest.fixture(autouse=True)
def _clean_store():
    """Reset rate-limit state before and after every test."""
    _reset_store()
    yield
    _reset_store()


# ── Basic allow / block ─────────────────────────────────────────────

def test_allow_under_limit():
    """Requests below MAX_ATTEMPTS should pass without error."""
    email = "user@example.com"
    for _ in range(MAX_ATTEMPTS - 1):
        record_attempt(email)
    # Should not raise
    check_rate_limit_for_email(email)


def test_block_after_max_attempts():
    """Reaching MAX_ATTEMPTS within the window triggers a 429."""
    email = "user@example.com"
    for _ in range(MAX_ATTEMPTS):
        record_attempt(email)
    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit_for_email(email)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_block_persists_during_lockout():
    """Subsequent checks during lockout keep raising 429."""
    email = "user@example.com"
    for _ in range(MAX_ATTEMPTS):
        record_attempt(email)
    with pytest.raises(HTTPException):
        check_rate_limit_for_email(email)
    # Still locked on next call
    with pytest.raises(HTTPException):
        check_rate_limit_for_email(email)


# ── Email isolation ─────────────────────────────────────────────────

def test_email_isolation():
    """Attempts on one email don't affect another."""
    for _ in range(MAX_ATTEMPTS):
        record_attempt("bad@example.com")
    # Different email should be fine
    check_rate_limit_for_email("good@example.com")


# ── Reset ───────────────────────────────────────────────────────────

def test_reset_clears_attempts():
    """reset_attempts lets the email through again."""
    email = "user@example.com"
    for _ in range(MAX_ATTEMPTS):
        record_attempt(email)
    reset_attempts(email)
    # Should pass now
    check_rate_limit_for_email(email)


# ── Lockout duration & expiry ───────────────────────────────────────

def test_lockout_duration_matches_base():
    """First lockout duration equals LOCKOUT_SECONDS."""
    email = "user@example.com"
    base = 1000.0
    with patch("backend.utils.rate_limit.time.monotonic", return_value=base):
        for _ in range(MAX_ATTEMPTS):
            record_attempt(email)
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit_for_email(email)
    retry = int(exc_info.value.headers["Retry-After"])
    assert retry == LOCKOUT_SECONDS + 1


def test_lockout_expiry():
    """After the lockout window passes, the email is allowed again."""
    email = "user@example.com"
    t = 1000.0

    with patch("backend.utils.rate_limit.time.monotonic", return_value=t):
        for _ in range(MAX_ATTEMPTS):
            record_attempt(email)
        with pytest.raises(HTTPException):
            check_rate_limit_for_email(email)

    # Jump past lockout
    t_after = t + LOCKOUT_SECONDS + 1
    with patch("backend.utils.rate_limit.time.monotonic", return_value=t_after):
        check_rate_limit_for_email(email)  # should not raise


# ── Escalation with cap ─────────────────────────────────────────────

def test_escalating_lockout():
    """Each successive lockout doubles, up to the cap."""
    email = "user@example.com"
    t = 1000.0

    for cycle in range(MAX_ESCALATION + 2):
        with patch("backend.utils.rate_limit.time.monotonic", return_value=t):
            for _ in range(MAX_ATTEMPTS):
                record_attempt(email)
            with pytest.raises(HTTPException) as exc_info:
                check_rate_limit_for_email(email)

        exp = min(cycle, MAX_ESCALATION)
        expected_duration = LOCKOUT_SECONDS * (2 ** exp)
        retry = int(exc_info.value.headers["Retry-After"])
        assert retry == expected_duration + 1, f"cycle {cycle}: expected {expected_duration + 1}, got {retry}"

        # Advance past lockout for next cycle
        t += expected_duration + 1


# ── Cleanup ─────────────────────────────────────────────────────────

def test_cleanup_removes_expired_entries():
    """Expired entries are purged after CLEANUP_INTERVAL."""
    email = "stale@example.com"
    t = 1000.0

    with patch("backend.utils.rate_limit.time.monotonic", return_value=t):
        record_attempt(email)

    # Advance past window + cleanup interval
    t_cleanup = t + WINDOW_SECONDS + CLEANUP_INTERVAL + 1
    with patch("backend.utils.rate_limit.time.monotonic", return_value=t_cleanup):
        check_rate_limit_for_email("trigger@example.com")  # triggers cleanup

    assert email not in _store


def test_cleanup_preserves_locked_entries():
    """Locked-out entries survive cleanup."""
    email = "locked@example.com"
    t = 1000.0

    with patch("backend.utils.rate_limit.time.monotonic", return_value=t):
        for _ in range(MAX_ATTEMPTS):
            record_attempt(email)
        with pytest.raises(HTTPException):
            check_rate_limit_for_email(email)

    # Cleanup fires but entry is still locked
    t_cleanup = t + CLEANUP_INTERVAL + 1
    with patch("backend.utils.rate_limit.time.monotonic", return_value=t_cleanup):
        check_rate_limit_for_email("other@example.com")

    key = email.lower().strip()
    assert key in _store


# ── Thread safety ───────────────────────────────────────────────────

def test_thread_safety():
    """Concurrent attempts from many threads don't corrupt state."""
    email = "race@example.com"
    num_threads = 20
    barrier = threading.Barrier(num_threads)

    def worker():
        barrier.wait()
        record_attempt(email)

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    key = email.lower().strip()
    assert len(_store[key].timestamps) == num_threads


# ── Case-insensitive email handling ─────────────────────────────────

def test_case_insensitive_record():
    """Attempts with different casings count together."""
    variants = ["User@Example.COM", "user@example.com", "USER@EXAMPLE.COM"]
    for v in variants[:MAX_ATTEMPTS]:
        record_attempt(v)
    # Pad remaining
    for _ in range(MAX_ATTEMPTS - len(variants[:MAX_ATTEMPTS])):
        record_attempt("user@example.com")

    with pytest.raises(HTTPException):
        check_rate_limit_for_email("USER@example.com")


def test_case_insensitive_reset():
    """Reset with different casing clears the entry."""
    email = "User@Example.COM"
    for _ in range(MAX_ATTEMPTS):
        record_attempt(email)
    reset_attempts("user@example.com")
    check_rate_limit_for_email(email)  # should not raise


# ── Window expiry (timestamps age out) ──────────────────────────────

def test_old_attempts_expire_outside_window():
    """Attempts older than WINDOW_SECONDS don't count."""
    email = "user@example.com"
    t = 1000.0

    with patch("backend.utils.rate_limit.time.monotonic", return_value=t):
        for _ in range(MAX_ATTEMPTS - 1):
            record_attempt(email)

    # Advance past window, add one more attempt
    t_later = t + WINDOW_SECONDS + 1
    with patch("backend.utils.rate_limit.time.monotonic", return_value=t_later):
        record_attempt(email)
        # Only 1 recent attempt — should pass
        check_rate_limit_for_email(email)
