"""Tests for the /api/health endpoints."""

from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import health

# Register the health router for testing
app.include_router(health.router)

client = TestClient(app)

LLM_URL = "http://localhost:5000"


def _mock_llm_ok(*args, **kwargs):
    """Return a successful httpx response."""
    resp = httpx.Response(200, json={"status": "ok"})
    return resp


def _mock_llm_fail(*args, **kwargs):
    """Raise a connection error."""
    raise httpx.ConnectError("connection refused")


def _mock_chroma_settings_http():
    return {"mode": "http", "host": "localhost", "port": 8001}


def _mock_chroma_settings_embedded():
    return {"mode": "embedded", "path": "/tmp/chroma"}


class TestHealthEndpoint:
    """Tests for GET /api/health."""

    @patch("backend.routers.health.get_chroma_settings", return_value=_mock_chroma_settings_http())
    @patch("backend.routers.health.httpx.get", side_effect=_mock_llm_ok)
    @patch("backend.routers.health.get_llm_base_url", return_value=LLM_URL)
    def test_health_all_ok(self, mock_llm_url, mock_get, mock_chroma):
        """All services reachable returns status ok."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["llm_reachable"] is True
        assert data["services"]["llm"] == "ok"
        assert data["services"]["chromadb"] == "ok"
        assert data["version"] == "0.1.0-mva"
        assert "uptime_seconds" in data

    @patch("backend.routers.health.get_chroma_settings", return_value=_mock_chroma_settings_http())
    @patch("backend.routers.health.httpx.get", side_effect=_mock_llm_fail)
    @patch("backend.routers.health.get_llm_base_url", return_value=LLM_URL)
    def test_health_all_down(self, mock_llm_url, mock_get, mock_chroma):
        """All services unreachable returns degraded."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["llm_reachable"] is False
        assert data["services"]["llm"] == "unreachable"
        assert data["services"]["chromadb"] == "unreachable"

    @patch("backend.routers.health.get_chroma_settings", return_value=_mock_chroma_settings_http())
    @patch("backend.routers.health.get_llm_base_url", return_value=LLM_URL)
    def test_health_llm_down_chroma_up(self, mock_llm_url, mock_chroma):
        """LLM down but ChromaDB up returns degraded."""
        def selective_get(url, **kwargs):
            if "health" in url and "heartbeat" not in url:
                raise httpx.ConnectError("refused")
            return _mock_llm_ok(url, **kwargs)

        with patch("backend.routers.health.httpx.get", side_effect=selective_get):
            resp = client.get("/api/health")
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["services"]["llm"] == "unreachable"
        assert data["services"]["chromadb"] == "ok"

    @patch("backend.routers.health.settings")
    @patch("backend.routers.health.get_chroma_settings", return_value=_mock_chroma_settings_http())
    @patch("backend.routers.health.httpx.get", side_effect=_mock_llm_ok)
    @patch("backend.routers.health.get_llm_base_url", return_value=LLM_URL)
    def test_health_mode_overlord(self, mock_llm_url, mock_get, mock_chroma, mock_settings):
        """Mode is overlord when overlord_routing_enabled is True."""
        mock_settings.overlord_routing_enabled = True
        resp = client.get("/api/health")
        assert resp.json()["mode"] == "overlord"

    @patch("backend.routers.health.settings")
    @patch("backend.routers.health.get_chroma_settings", return_value=_mock_chroma_settings_http())
    @patch("backend.routers.health.httpx.get", side_effect=_mock_llm_ok)
    @patch("backend.routers.health.get_llm_base_url", return_value=LLM_URL)
    def test_health_mode_standalone(self, mock_llm_url, mock_get, mock_chroma, mock_settings):
        """Mode is standalone when overlord_routing_enabled is False."""
        mock_settings.overlord_routing_enabled = False
        resp = client.get("/api/health")
        assert resp.json()["mode"] == "standalone"

    @patch("backend.routers.health.get_chroma_settings", return_value=_mock_chroma_settings_embedded())
    @patch("backend.routers.health.httpx.get", side_effect=_mock_llm_ok)
    @patch("backend.routers.health.get_llm_base_url", return_value=LLM_URL)
    def test_health_chromadb_embedded_always_ok(self, mock_llm_url, mock_get, mock_chroma):
        """Embedded ChromaDB is always reported as ok."""
        resp = client.get("/api/health")
        data = resp.json()
        assert data["services"]["chromadb"] == "ok"

    def test_health_returns_llm_url(self):
        """Response includes the resolved LLM URL."""
        with patch("backend.routers.health.get_llm_base_url", return_value="http://my-llm:8080"), \
             patch("backend.routers.health.httpx.get", side_effect=_mock_llm_fail), \
             patch("backend.routers.health.get_chroma_settings", return_value=_mock_chroma_settings_http()):
            resp = client.get("/api/health")
        assert resp.json()["llm_url"] == "http://my-llm:8080"


class TestReadyEndpoint:
    """Tests for GET /api/health/ready."""

    @patch("backend.routers.health.httpx.get", side_effect=_mock_llm_ok)
    @patch("backend.routers.health.get_llm_base_url", return_value=LLM_URL)
    def test_ready_when_llm_reachable(self, mock_llm_url, mock_get):
        """Returns 200 and ready=true when LLM is reachable."""
        resp = client.get("/api/health/ready")
        assert resp.status_code == 200
        assert resp.json()["ready"] is True

    @patch("backend.routers.health.httpx.get", side_effect=_mock_llm_fail)
    @patch("backend.routers.health.get_llm_base_url", return_value=LLM_URL)
    def test_not_ready_when_llm_unreachable(self, mock_llm_url, mock_get):
        """Returns 503 and ready=false when LLM is unreachable."""
        resp = client.get("/api/health/ready")
        assert resp.status_code == 503
        assert resp.json()["ready"] is False
