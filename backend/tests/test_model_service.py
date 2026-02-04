"""Tests for ModelService with mocked httpx client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest  # noqa: F401

from backend.services.model_service import ModelService


def _run(coro):
    """Run an async coroutine synchronously for testing."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── list_models ─────────────────────────────────────────────────────────────


class TestListModels:
    """Test ModelService.list_models with mocked HTTP responses."""

    def test_returns_parsed_models(self):
        """list_models should parse the OpenAI-compatible /v1/models response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "llama-3-8b", "active": True},
                {"id": "mistral-7b", "active": False},
            ]
        }

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            svc = ModelService()
            models = _run(svc.list_models())

        assert len(models) == 2
        assert models[0] == {"id": "llama-3-8b", "name": "llama-3-8b", "active": True}
        assert models[1] == {"id": "mistral-7b", "name": "mistral-7b", "active": False}

    def test_returns_empty_on_connection_error(self):
        """list_models should return [] when TabbyAPI is unreachable."""
        with patch("backend.services.model_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            svc = ModelService()
            models = _run(svc.list_models())

        assert models == []

    def test_returns_empty_on_http_error(self):
        """list_models should return [] when TabbyAPI returns an error status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=mock_response,
            )
        )

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            svc = ModelService()
            models = _run(svc.list_models())

        assert models == []

    def test_returns_empty_when_data_key_missing(self):
        """list_models should return [] when response has no 'data' key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            svc = ModelService()
            models = _run(svc.list_models())

        assert models == []

    def test_defaults_active_to_false(self):
        """Models without an 'active' field should default to active=False."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "some-model"},
            ]
        }

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)

            svc = ModelService()
            models = _run(svc.list_models())

        assert len(models) == 1
        assert models[0]["active"] is False


# ── switch_model ────────────────────────────────────────────────────────────


class TestSwitchModel:
    """Test ModelService.switch_model with mocked HTTP responses."""

    def test_switch_success(self):
        """switch_model should return True on successful POST."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)

            svc = ModelService()
            result = _run(svc.switch_model("llama-3-8b"))

        assert result is True
        mock_client.post.assert_called_once_with(
            f"{svc.base_url}/v1/model/load",
            json={"name": "llama-3-8b"},
        )

    def test_switch_returns_false_on_connection_error(self):
        """switch_model should return False when TabbyAPI is unreachable."""
        with patch("backend.services.model_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            svc = ModelService()
            result = _run(svc.switch_model("llama-3-8b"))

        assert result is False

    def test_switch_returns_false_on_http_error(self):
        """switch_model should return False when TabbyAPI returns an error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=mock_response,
            )
        )

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)

            svc = ModelService()
            result = _run(svc.switch_model("bad-model"))

        assert result is False

    def test_switch_returns_false_on_timeout(self):
        """switch_model should return False on timeout."""
        with patch("backend.services.model_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.ReadTimeout("Timeout"))

            svc = ModelService()
            result = _run(svc.switch_model("large-model"))

        assert result is False
