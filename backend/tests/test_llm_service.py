"""Tests for LLMService: streaming chat, non-streaming chat, error handling."""
import os

# Set test database URL before any backend imports to avoid the module-level
# create_all in dependencies.py trying to open the default sqlite file.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import json  # noqa: E402
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

from backend.services.llm_service import LLMService  # noqa: E402


# -- Helpers ------------------------------------------------------------------


class AsyncIterator:
    """Wraps a list into an async iterator for mocking aiter_lines."""

    def __init__(self, items):
        self._items = items
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


class AsyncContextManager:
    """Wraps a mock into an async context manager for mocking client.stream."""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        pass


# -- TestStreamChat -----------------------------------------------------------


class TestStreamChat:
    """Test LLMService.stream_chat (streaming SSE responses)."""

    @pytest.mark.asyncio
    async def test_stream_chat_yields_content(self):
        """Mocks httpx.AsyncClient to return SSE lines, verifies chunks."""
        # Build SSE lines that the stream would return
        sse_lines = [
            "data: "
            + json.dumps(
                {"choices": [{"delta": {"content": "Hello"}}]}
            ),
            "data: "
            + json.dumps(
                {"choices": [{"delta": {"content": " world"}}]}
            ),
            "data: [DONE]",
        ]

        # Mock the response object with aiter_lines
        mock_response = MagicMock()
        mock_response.aiter_lines.return_value = AsyncIterator(sse_lines)
        mock_response.raise_for_status = MagicMock()

        # Mock the client: client.stream(...) returns an async context manager
        mock_client = MagicMock()
        mock_client.stream.return_value = AsyncContextManager(mock_response)

        # Wrap mock_client itself as an async context manager (async with httpx.AsyncClient() as client)
        mock_client_cm = AsyncContextManager(mock_client)

        with patch("backend.services.llm_service.httpx.AsyncClient", return_value=mock_client_cm):
            service = LLMService()
            chunks = []
            async for chunk in service.stream_chat([{"role": "user", "content": "Hi"}]):
                chunks.append(chunk)

        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_chat_connect_error(self):
        """Mocks httpx.AsyncClient to raise ConnectError, verifies error message chunk."""
        # Mock client whose stream() raises ConnectError
        mock_client = MagicMock()
        mock_client.stream.side_effect = httpx.ConnectError("Connection refused")

        mock_client_cm = AsyncContextManager(mock_client)

        with patch("backend.services.llm_service.httpx.AsyncClient", return_value=mock_client_cm):
            service = LLMService()
            chunks = []
            async for chunk in service.stream_chat([{"role": "user", "content": "Hi"}]):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0] == "[Error: Could not connect to LLM service. Is TabbyAPI running?]"


# -- TestChat -----------------------------------------------------------------


class TestChat:
    """Test LLMService.chat (non-streaming responses)."""

    @pytest.mark.asyncio
    async def test_chat_returns_content(self):
        """Mocks httpx.AsyncClient.post to return JSON response, verifies content string."""
        response_data = {
            "choices": [{"message": {"content": "Hello from LLM"}}]
        }

        # Mock the response object
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = response_data

        # Mock the client with async post
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        mock_client_cm = AsyncContextManager(mock_client)

        with patch("backend.services.llm_service.httpx.AsyncClient", return_value=mock_client_cm):
            service = LLMService()
            result = await service.chat([{"role": "user", "content": "Hi"}])

        assert result == "Hello from LLM"

    @pytest.mark.asyncio
    async def test_chat_returns_error_on_failure(self):
        """Mocks httpx.AsyncClient.post to raise Exception, verifies '[Error:' prefix."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=Exception("Something went wrong"))

        mock_client_cm = AsyncContextManager(mock_client)

        with patch("backend.services.llm_service.httpx.AsyncClient", return_value=mock_client_cm):
            service = LLMService()
            result = await service.chat([{"role": "user", "content": "Hi"}])

        assert result.startswith("[Error:")
        assert "Something went wrong" in result
