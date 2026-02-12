"""Tests for CORS middleware configuration (mva-cors-config spec)."""
from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_cors_allows_listed_origin():
    """Preflight from an allowed origin should succeed."""
    origin = "http://localhost:5173"
    resp = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == origin


def test_cors_blocks_unlisted_origin():
    """Preflight from an unknown origin should not reflect that origin."""
    resp = client.options(
        "/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"


def test_cors_allowed_methods_no_patch():
    """PATCH should not appear in the allowed methods."""
    origin = "http://localhost:5173"
    resp = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    methods = resp.headers.get("access-control-allow-methods", "")
    assert "PATCH" not in methods
    assert "GET" in methods
    assert "POST" in methods


def test_cors_allowed_headers_tight():
    """Only Content-Type and Authorization should be allowed."""
    origin = "http://localhost:5173"
    resp = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    headers_val = resp.headers.get("access-control-allow-headers", "")
    assert "Content-Type" in headers_val or "content-type" in headers_val
    assert "X-Requested-With" not in headers_val


def test_cors_credentials_enabled():
    """allow_credentials should be true."""
    origin = "http://localhost:5173"
    resp = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-credentials") == "true"
