"""Tests for the in-memory rate limiter."""

import threading
import time
from unittest.mock import MagicMock

import pytest

from backend.middleware.rate_limit import (
    MAX_ATTEMPTS,
    LOCKOUT_SECONDS,
    WINDOW_SECONDS,
    _reset_store,
    _store,
    check_rate_limit,
    record_attempt,
    reset_attempts,
)
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(ip: str = "192.168.1.10") -> MagicMock:
    """Create a mock FastAPI Request with the given client IP."""
    req = MagicMock()
    req.client.host = ip
    return req


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset rate-limit state before each test."""
    _reset_store()
    yield
    _reset_store()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckRateLimit:
    """Tests for the check_rate_limit dependency."""

    def test_allows_first_request(self):
        """First request from an IP should always pass."""
        check_rate_limit(_make_request())  # no exception

    def test_allows_up_to_max_attempts(self):
        """Requests should be allowed up to MAX_ATTEMPTS - 1 recorded failures."""
        ip = "10.0.0.1"
        req = _make_request(ip)
        for _ in range(MAX_ATTEMPTS - 1):
            record_attempt(ip)
            check_rate_limit(req)  # still allowed

    def test_blocks_after_max_attempts(self):
        """After MAX_ATTEMPTS failures, the next check should raise 429."""
        ip = "10.0.0.2"
        req = _make_request(ip)
        for _ in range(MAX_ATTEMPTS):
            record_attempt(ip)

        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(req)
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers

    def test_different_ips_isolated(self):
        """Rate-limit state for one IP should not affect another."""
        ip_a = "10.0.0.10"
        ip_b = "10.0.0.11"
        for _ in range(MAX_ATTEMPTS):
            record_attempt(ip_a)

        # ip_a is blocked
        with pytest.raises(HTTPException):
            check_rate_limit(_make_request(ip_a))

        # ip_b is fine
        check_rate_limit(_make_request(ip_b))

    def test_reset_clears_attempts(self):
        """reset_attempts should allow the IP to pass again."""
        ip = "10.0.0.3"
        for _ in range(MAX_ATTEMPTS):
            record_attempt(ip)

        reset_attempts(ip)
        check_rate_limit(_make_request(ip))  # no exception

    def test_retry_after_header_value(self):
        """Retry-After header should reflect the lockout duration."""
        ip = "10.0.0.4"
        for _ in range(MAX_ATTEMPTS):
            record_attempt(ip)

        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(_make_request(ip))

        retry_after = int(exc_info.value.headers["Retry-After"])
        # Should be close to LOCKOUT_SECONDS (± a few seconds for timing)
        assert LOCKOUT_SECONDS <= retry_after <= LOCKOUT_SECONDS + 2

    def test_lockout_expires(self, monkeypatch):
        """After lockout duration passes, requests should be allowed again."""
        ip = "10.0.0.5"
        for _ in range(MAX_ATTEMPTS):
            record_attempt(ip)

        # Trigger lockout
        with pytest.raises(HTTPException):
            check_rate_limit(_make_request(ip))

        # Fast-forward past lockout by manipulating the record
        from backend.middleware import rate_limit as rl_mod
        with rl_mod._lock:
            rec = rl_mod._store[ip]
            rec.lockout_until = time.monotonic() - 1  # expired

        check_rate_limit(_make_request(ip))  # should pass

    def test_lockout_escalation(self):
        """Successive lockouts should have increasing duration."""
        ip = "10.0.0.6"
        from backend.middleware import rate_limit as rl_mod

        # First lockout
        for _ in range(MAX_ATTEMPTS):
            record_attempt(ip)
        with pytest.raises(HTTPException) as exc1:
            check_rate_limit(_make_request(ip))
        retry1 = int(exc1.value.headers["Retry-After"])

        # Expire the lockout
        with rl_mod._lock:
            rl_mod._store[ip].lockout_until = time.monotonic() - 1

        # Second burst
        for _ in range(MAX_ATTEMPTS):
            record_attempt(ip)
        with pytest.raises(HTTPException) as exc2:
            check_rate_limit(_make_request(ip))
        retry2 = int(exc2.value.headers["Retry-After"])

        # Second lockout should be longer (2x)
        assert retry2 > retry1

    def test_cleanup_removes_expired_entries(self):
        """Expired entries should be cleaned up to prevent memory leaks."""
        from backend.middleware import rate_limit as rl_mod

        ip = "10.0.0.7"
        record_attempt(ip)

        # Make the timestamp old and force cleanup
        with rl_mod._lock:
            rec = rl_mod._store[ip]
            rec.timestamps = [time.monotonic() - WINDOW_SECONDS - 100]
            rl_mod._last_cleanup = 0  # force cleanup on next check

        check_rate_limit(_make_request(ip))

        # After cleanup, the entry should be gone
        with rl_mod._lock:
            assert ip not in rl_mod._store

    def test_thread_safety(self):
        """Concurrent access from multiple threads should not corrupt state."""
        ip = "10.0.0.8"
        errors: list[Exception] = []

        def _worker():
            try:
                for _ in range(20):
                    record_attempt(ip)
                    try:
                        check_rate_limit(_make_request(ip))
                    except HTTPException:
                        pass  # expected after limit
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety violation: {errors}"

    def test_no_client_ip(self):
        """Request with no client info should not crash."""
        req = MagicMock()
        req.client = None
        check_rate_limit(req)  # should handle gracefully

    def test_record_without_check_does_not_crash(self):
        """Recording attempts without checking should be safe."""
        record_attempt("10.0.0.99")
        record_attempt("10.0.0.99")
        reset_attempts("10.0.0.99")
        reset_attempts("nonexistent")  # no KeyError
