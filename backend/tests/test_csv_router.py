"""Tests for the CSV upload router."""
import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.csv import router, MAX_FILE_SIZE
from backend.services.csv_parser import CSVParseError


# ── Test app setup ──────────────────────────────────────────────

FAKE_USER = MagicMock(id=1, username="testuser")


def _override_auth():
    return FAKE_USER


app = FastAPI()
app.include_router(router)

# Override auth dependency
from backend.routers.auth import get_current_user  # noqa: E402

app.dependency_overrides[get_current_user] = _override_auth

client = TestClient(app)


# ── Fixtures ────────────────────────────────────────────────────

VALID_CSV = b"name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\n"
VALID_TSV = b"name\tage\tcity\nAlice\t30\tNYC\nBob\t25\tLA\n"
HEADERS_ONLY = b"name,age,city\n"
EMPTY_FILE = b""
MALFORMED_CSV = b"\x80\x81\x82\x83"


def _upload(filename: str, content: bytes, endpoint: str = "/api/csv/upload", **kwargs):
    """Helper to POST a file upload."""
    files = {"file": (filename, io.BytesIO(content), "text/csv")}
    return client.post(endpoint, files=files, **kwargs)


def _analyze(filename: str, content: bytes, question: str):
    """Helper to POST an analyze request."""
    files = {"file": (filename, io.BytesIO(content), "text/csv")}
    data = {"question": question}
    return client.post("/api/csv/analyze", files=files, data=data)


# ── Upload endpoint tests ──────────────────────────────────────


class TestUploadCSV:
    """Tests for POST /api/csv/upload."""

    def test_upload_valid_csv(self):
        """Successful upload returns chunks and summary."""
        resp = _upload("sales.csv", VALID_CSV)
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == "sales.csv"
        assert len(body["chunks"]) >= 1
        assert body["summary"]["total_rows"] == 3
        assert body["summary"]["total_columns"] == 3
        assert "name" in body["summary"]["columns"]

    def test_upload_valid_tsv(self):
        """TSV files with .tsv extension are accepted."""
        resp = _upload("data.tsv", VALID_TSV)
        assert resp.status_code == 200
        body = resp.json()
        assert body["summary"]["total_rows"] == 2

    def test_upload_valid_txt(self):
        """TXT files with .txt extension are accepted."""
        resp = _upload("data.txt", VALID_CSV)
        assert resp.status_code == 200

    def test_upload_wrong_extension(self):
        """Non-allowed extensions return 400."""
        resp = _upload("data.xlsx", VALID_CSV)
        assert resp.status_code == 400
        assert "Unsupported file extension" in resp.json()["detail"]

    def test_upload_no_extension(self):
        """Files without an extension return 400."""
        resp = _upload("data", VALID_CSV)
        assert resp.status_code == 400

    def test_upload_file_too_large(self):
        """Files exceeding MAX_FILE_SIZE return 413."""
        big_content = b"a,b\n" + b"x,y\n" * (MAX_FILE_SIZE // 4 + 1)
        assert len(big_content) > MAX_FILE_SIZE
        resp = _upload("big.csv", big_content)
        assert resp.status_code == 413
        assert "too large" in resp.json()["detail"]

    def test_upload_empty_file(self):
        """Empty CSV returns 422."""
        resp = _upload("empty.csv", EMPTY_FILE)
        assert resp.status_code == 422

    def test_upload_headers_only(self):
        """CSV with headers but no data rows returns 422."""
        resp = _upload("headers.csv", HEADERS_ONLY)
        assert resp.status_code == 422

    def test_upload_chunk_structure(self):
        """Each chunk contains expected fields."""
        resp = _upload("sales.csv", VALID_CSV)
        assert resp.status_code == 200
        chunk = resp.json()["chunks"][0]
        assert "chunk_index" in chunk
        assert "total_chunks" in chunk
        assert "total_rows" in chunk
        assert "columns" in chunk
        assert "rows" in chunk
        assert "text" in chunk

    def test_upload_numeric_stats(self):
        """Numeric columns get summary statistics."""
        resp = _upload("sales.csv", VALID_CSV)
        assert resp.status_code == 200
        stats = resp.json()["summary"]["numeric_stats"]
        assert "age" in stats
        assert stats["age"]["min"] == 25.0
        assert stats["age"]["max"] == 35.0


# ── Analyze endpoint tests ─────────────────────────────────────


class TestAnalyzeCSV:
    """Tests for POST /api/csv/analyze."""

    def test_analyze_valid(self):
        """Analyze returns chunks, summary, and the question."""
        resp = _analyze("sales.csv", VALID_CSV, "What is the average age?")
        assert resp.status_code == 200
        body = resp.json()
        assert body["question"] == "What is the average age?"
        assert body["filename"] == "sales.csv"
        assert len(body["chunks"]) >= 1
        assert body["summary"]["total_rows"] == 3

    def test_analyze_wrong_extension(self):
        """Analyze rejects wrong extensions."""
        resp = _analyze("data.json", VALID_CSV, "question?")
        assert resp.status_code == 400

    def test_analyze_empty_file(self):
        """Analyze rejects empty files."""
        resp = _analyze("empty.csv", EMPTY_FILE, "question?")
        assert resp.status_code == 422

    def test_analyze_preserves_question(self):
        """The question string is returned verbatim."""
        q = "How many rows have city=NYC?"
        resp = _analyze("data.csv", VALID_CSV, q)
        assert resp.status_code == 200
        assert resp.json()["question"] == q


# ── Auth tests ──────────────────────────────────────────────────


class TestCSVAuth:
    """Tests verifying auth dependency is wired up."""

    def test_upload_requires_auth(self):
        """Without auth override, endpoints would require authentication.

        We verify the dependency is declared by checking the route dependencies.
        """
        from backend.routers.csv import upload_csv, analyze_csv

        # Both endpoints have dependencies (get_current_user is in params)
        import inspect

        upload_sig = inspect.signature(upload_csv)
        assert "user" in upload_sig.parameters

        analyze_sig = inspect.signature(analyze_csv)
        assert "user" in analyze_sig.parameters
