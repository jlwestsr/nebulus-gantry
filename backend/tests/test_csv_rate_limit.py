"""Tests for CSV endpoint rate limiting."""
import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.csv import router
from backend.routers.auth import get_current_user
from backend.utils.csv_rate_limit import (
    ANALYZE_MAX_REQUESTS,
    ANALYZE_WINDOW_SECONDS,
    UPLOAD_MAX_REQUESTS,
    UPLOAD_WINDOW_SECONDS,
    _reset_store,
    check_csv_analyze_rate_limit,
    check_csv_upload_rate_limit,
)

# ── Test app setup ──────────────────────────────────────────────

FAKE_USER = MagicMock(id=1, email="test@example.com", username="testuser")


def _override_auth():
    return FAKE_USER


app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_current_user] = _override_auth

client = TestClient(app)

VALID_CSV = b"name,age,city\nAlice,30,NYC\nBob,25,LA\n"


@pytest.fixture(autouse=True)
def _clean_rate_limit_state():
    """Reset rate limit state before each test."""
    _reset_store()
    yield
    _reset_store()


# ── Unit tests for the rate limiter itself ──────────────────────


class TestCheckCsvUploadRateLimit:
    """Unit tests for check_csv_upload_rate_limit."""

    def test_allows_requests_under_limit(self):
        for _ in range(UPLOAD_MAX_REQUESTS):
            check_csv_upload_rate_limit("user@example.com")

    def test_blocks_after_limit_exceeded(self):
        from fastapi import HTTPException

        for _ in range(UPLOAD_MAX_REQUESTS):
            check_csv_upload_rate_limit("user@example.com")

        with pytest.raises(HTTPException) as exc_info:
            check_csv_upload_rate_limit("user@example.com")
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
        assert "upload CSV" in exc_info.value.detail

    def test_different_users_have_separate_limits(self):
        for _ in range(UPLOAD_MAX_REQUESTS):
            check_csv_upload_rate_limit("user1@example.com")

        # user2 should still be fine
        check_csv_upload_rate_limit("user2@example.com")

    def test_email_is_case_insensitive(self):
        from fastapi import HTTPException

        for _ in range(UPLOAD_MAX_REQUESTS):
            check_csv_upload_rate_limit("User@Example.COM")

        with pytest.raises(HTTPException) as exc_info:
            check_csv_upload_rate_limit("user@example.com")
        assert exc_info.value.status_code == 429

    def test_retry_after_header_present(self):
        from fastapi import HTTPException

        for _ in range(UPLOAD_MAX_REQUESTS):
            check_csv_upload_rate_limit("user@example.com")

        with pytest.raises(HTTPException) as exc_info:
            check_csv_upload_rate_limit("user@example.com")
        assert "Retry-After" in exc_info.value.headers

    def test_window_expiry_allows_new_requests(self):
        """After the window expires, requests should be allowed again."""
        with patch("backend.utils.csv_rate_limit.time") as mock_time:
            now = 1000.0
            mock_time.monotonic.return_value = now

            for _ in range(UPLOAD_MAX_REQUESTS):
                check_csv_upload_rate_limit("user@example.com")

            # Advance past window
            mock_time.monotonic.return_value = now + UPLOAD_WINDOW_SECONDS + 1
            # Should not raise
            check_csv_upload_rate_limit("user@example.com")


class TestCheckCsvAnalyzeRateLimit:
    """Unit tests for check_csv_analyze_rate_limit."""

    def test_allows_requests_under_limit(self):
        for _ in range(ANALYZE_MAX_REQUESTS):
            check_csv_analyze_rate_limit("user@example.com")

    def test_blocks_after_limit_exceeded(self):
        from fastapi import HTTPException

        for _ in range(ANALYZE_MAX_REQUESTS):
            check_csv_analyze_rate_limit("user@example.com")

        with pytest.raises(HTTPException) as exc_info:
            check_csv_analyze_rate_limit("user@example.com")
        assert exc_info.value.status_code == 429
        assert "analyze CSV" in exc_info.value.detail

    def test_upload_and_analyze_are_independent(self):
        """Exhausting upload limit should NOT affect analyze limit."""
        for _ in range(UPLOAD_MAX_REQUESTS):
            check_csv_upload_rate_limit("user@example.com")

        # Analyze should still work
        check_csv_analyze_rate_limit("user@example.com")


# ── Integration tests via TestClient ────────────────────────────


class TestUploadEndpointRateLimit:
    """Integration tests for POST /api/csv/upload rate limiting."""

    def _upload(self):
        return client.post(
            "/api/csv/upload",
            files={"file": ("data.csv", io.BytesIO(VALID_CSV), "text/csv")},
        )

    @patch("backend.routers.csv.parse_and_summarize")
    def test_upload_returns_429_when_rate_limited(self, mock_parse):
        from backend.services.csv_parser import CSVChunk, CSVSummary

        mock_parse.return_value = (
            [CSVChunk(chunk_index=0, total_chunks=1, total_rows=2, columns=["name", "age", "city"], rows=[["Alice", "30", "NYC"]], text="...")],
            CSVSummary(total_rows=2, total_columns=3, columns=["name", "age", "city"], numeric_stats={}, categorical_counts={}),
        )

        for i in range(UPLOAD_MAX_REQUESTS):
            resp = self._upload()
            assert resp.status_code == 200, f"Request {i+1} failed: {resp.text}"

        resp = self._upload()
        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.json()["detail"]
        assert "Retry-After" in resp.headers


class TestAnalyzeEndpointRateLimit:
    """Integration tests for POST /api/csv/analyze rate limiting."""

    def _analyze(self):
        return client.post(
            "/api/csv/analyze",
            files={"file": ("data.csv", io.BytesIO(VALID_CSV), "text/csv")},
            data={"question": "What is the average age?"},
        )

    @patch("backend.routers.csv.parse_and_summarize")
    def test_analyze_returns_429_when_rate_limited(self, mock_parse):
        from backend.services.csv_parser import CSVChunk, CSVSummary

        mock_parse.return_value = (
            [CSVChunk(chunk_index=0, total_chunks=1, total_rows=2, columns=["name", "age", "city"], rows=[["Alice", "30", "NYC"]], text="...")],
            CSVSummary(total_rows=2, total_columns=3, columns=["name", "age", "city"], numeric_stats={}, categorical_counts={}),
        )

        for i in range(ANALYZE_MAX_REQUESTS):
            resp = self._analyze()
            assert resp.status_code == 200, f"Request {i+1} failed: {resp.text}"

        resp = self._analyze()
        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.json()["detail"]


class TestResetStore:
    """Test the _reset_store helper."""

    def test_reset_clears_all_state(self):
        for _ in range(UPLOAD_MAX_REQUESTS):
            check_csv_upload_rate_limit("user@example.com")

        _reset_store()

        # Should be allowed again
        check_csv_upload_rate_limit("user@example.com")
