"""Tests for MCPClient with mocked HTTP responses."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest  # noqa: F401

from backend.services.mcp_client import MCPClient


def _run(coro):
    """Run an async coroutine synchronously for testing."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _AsyncClientPatch:
    """Context manager for patching httpx.AsyncClient."""

    def __init__(self, mock_client):
        self._mock_client = mock_client
        self._patcher = patch("backend.services.mcp_client.httpx.AsyncClient")

    def __enter__(self):
        mock_cls = self._patcher.start()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=self._mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        return self._mock_client

    def __exit__(self, *args):
        self._patcher.stop()


# ── Initialization ──────────────────────────────────────────────────────────


class TestMCPClientInit:
    """Test MCPClient initialization and availability."""

    @patch("backend.services.mcp_client.get_mcp_settings", return_value=None)
    def test_unavailable_when_no_settings(self, mock_settings):
        client = MCPClient()
        assert client.available is False

    @patch("backend.services.mcp_client.get_mcp_settings", return_value={})
    def test_unavailable_when_no_url(self, mock_settings):
        client = MCPClient()
        assert client.available is False

    @patch(
        "backend.services.mcp_client.get_mcp_settings",
        return_value={"url": "http://localhost:9000"},
    )
    def test_available_when_url_configured(self, mock_settings):
        client = MCPClient()
        assert client.available is True


# ── list_tools ──────────────────────────────────────────────────────────────


class TestMCPListTools:
    """Test MCPClient.list_tools."""

    @patch("backend.services.mcp_client.get_mcp_settings", return_value=None)
    def test_returns_empty_when_unavailable(self, mock_settings):
        client = MCPClient()
        result = _run(client.list_tools())
        assert result == []

    @patch(
        "backend.services.mcp_client.get_mcp_settings",
        return_value={"url": "http://localhost:9000"},
    )
    def test_returns_tools_on_success(self, mock_settings):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "tools": [{"name": "search", "description": "Search docs"}]
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with _AsyncClientPatch(mock_client):
            client = MCPClient()
            result = _run(client.list_tools())

        assert len(result) == 1
        assert result[0]["name"] == "search"

    @patch(
        "backend.services.mcp_client.get_mcp_settings",
        return_value={"url": "http://localhost:9000"},
    )
    def test_returns_empty_on_connection_error(self, mock_settings):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with _AsyncClientPatch(mock_client):
            client = MCPClient()
            result = _run(client.list_tools())

        assert result == []


# ── execute_tool ────────────────────────────────────────────────────────────


class TestMCPExecuteTool:
    """Test MCPClient.execute_tool."""

    @patch("backend.services.mcp_client.get_mcp_settings", return_value=None)
    def test_returns_none_when_unavailable(self, mock_settings):
        client = MCPClient()
        result = _run(client.execute_tool("search", {"query": "test"}))
        assert result is None

    @patch(
        "backend.services.mcp_client.get_mcp_settings",
        return_value={"url": "http://localhost:9000"},
    )
    def test_returns_result_on_success(self, mock_settings):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": "found 5 matches"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with _AsyncClientPatch(mock_client):
            client = MCPClient()
            result = _run(client.execute_tool("search", {"query": "test"}))

        assert result == {"result": "found 5 matches"}
        mock_client.post.assert_called_once_with(
            "http://localhost:9000/tools/search/execute",
            json={"query": "test"},
        )

    @patch(
        "backend.services.mcp_client.get_mcp_settings",
        return_value={"url": "http://localhost:9000"},
    )
    def test_returns_none_on_error(self, mock_settings):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with _AsyncClientPatch(mock_client):
            client = MCPClient()
            result = _run(client.execute_tool("search"))

        assert result is None
