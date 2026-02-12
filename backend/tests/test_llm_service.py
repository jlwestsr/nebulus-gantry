"""Tests for LLMService: streaming chat, non-streaming chat, error handling,
and async concurrency safety."""
import asyncio
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
        assert chunks[0] == "[Error: Could not connect to LLM service. Is the LLM service running?]"


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


# -- TestConcurrencySafety ---------------------------------------------------


class TestConcurrencySafety:
    """Verify that per-request LLMService instances isolate usage data.

    LLMService stores last_usage on the instance.  This is safe because
    each request creates its own instance (see chat.py).  This test
    proves that concurrent async tasks using separate instances do not
    bleed usage data between each other.
    """

    @pytest.mark.asyncio
    async def test_concurrent_streams_do_not_share_usage(self):
        """Two concurrent stream_chat calls on separate instances get independent usage."""

        def _make_sse_lines(content: str, usage: dict):
            return [
                "data: " + json.dumps({"choices": [{"delta": {"content": content}}]}),
                "data: " + json.dumps({"choices": [{"delta": {}}], "usage": usage}),
                "data: [DONE]",
            ]

        usage_a = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        usage_b = {"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280}

        def _mock_client(sse_lines):
            mock_response = MagicMock()
            mock_response.aiter_lines.return_value = AsyncIterator(sse_lines)
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.stream.return_value = AsyncContextManager(mock_response)
            return AsyncContextManager(mock_client)

        async def consume(service):
            chunks = []
            async for chunk in service.stream_chat([{"role": "user", "content": "Hi"}]):
                chunks.append(chunk)
            return chunks, service.last_usage

        mock_a = _mock_client(_make_sse_lines("response_a", usage_a))
        mock_b = _mock_client(_make_sse_lines("response_b", usage_b))

        call_count = 0

        def client_factory(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_a if call_count == 1 else mock_b

        with patch("backend.services.llm_service.httpx.AsyncClient", side_effect=client_factory):
            service_a = LLMService()
            service_b = LLMService()

            task_a = asyncio.create_task(consume(service_a))
            task_b = asyncio.create_task(consume(service_b))

            (chunks_a, last_a), (chunks_b, last_b) = await asyncio.gather(task_a, task_b)

        # Each instance has its own usage — no cross-contamination
        assert chunks_a == ["response_a"]
        assert chunks_b == ["response_b"]
        assert last_a == usage_a
        assert last_b == usage_b
        assert last_a != last_b
