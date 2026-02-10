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


def _make_mock_response(status_code=200, json_data=None, raise_for_status=None):
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    if raise_for_status:
        resp.raise_for_status = MagicMock(side_effect=raise_for_status)
    else:
        resp.raise_for_status = MagicMock()
    resp.json.return_value = json_data or {}
    return resp


class _AsyncClientPatch:
    """Context manager for patching httpx.AsyncClient."""

    def __init__(self, mock_client):
        self._mock_client = mock_client
        self._patcher = patch("backend.services.model_service.httpx.AsyncClient")

    def __enter__(self):
        mock_cls = self._patcher.start()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=self._mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        return self._mock_client

    def __exit__(self, *args):
        self._patcher.stop()


# ── get_active_model ──────────────────────────────────────────────────────────


class TestGetActiveModel:
    """Test ModelService.get_active_model.

    The method now tries TabbyAPI-specific /v1/model first, then falls back
    to the first model from /v1/models. Both use the same httpx client.
    """

    def test_returns_active_model_from_tabby_endpoint(self):
        """get_active_model should return dict from /v1/model when available."""
        resp = _make_mock_response(json_data={"id": "llama-3-8b"})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=resp)

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.get_active_model())

        assert result == {"id": "llama-3-8b", "name": "llama-3-8b"}

    def test_falls_back_to_v1_models(self):
        """get_active_model should fall back to /v1/models when /v1/model fails."""
        tabby_error = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        models_resp = _make_mock_response(json_data={
            "data": [{"id": "mlx-model"}]
        })
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[tabby_error, models_resp])

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.get_active_model())

        assert result == {"id": "mlx-model", "name": "mlx-model"}

    def test_returns_none_when_no_model_loaded(self):
        """get_active_model should return None when /v1/model returns empty
        id and /v1/models returns no models."""
        tabby_resp = _make_mock_response(json_data={"id": ""})
        models_resp = _make_mock_response(json_data={"data": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[tabby_resp, models_resp])

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.get_active_model())

        assert result is None

    def test_returns_none_on_connection_error(self):
        """get_active_model should return None when LLM server is unreachable."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.get_active_model())

        assert result is None


# ── list_models ─────────────────────────────────────────────────────────────


class TestListModels:
    """Test ModelService.list_models with mocked HTTP responses.

    Note: list_models() internally calls get_active_model() first (which may
    make 1-2 GET calls), then fetches the model list (GET /v1/models).
    """

    def test_returns_parsed_models_with_active_flag(self):
        """list_models should mark the active model correctly."""
        # get_active_model: GET /v1/model → success (1 call)
        # list_models: GET /v1/models → model list (1 call)
        active_resp = _make_mock_response(json_data={"id": "llama-3-8b"})
        list_resp = _make_mock_response(json_data={
            "data": [
                {"id": "llama-3-8b"},
                {"id": "mistral-7b"},
            ]
        })
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[active_resp, list_resp])

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            models = _run(svc.list_models())

        assert len(models) == 2
        assert models[0] == {"id": "llama-3-8b", "name": "llama-3-8b", "active": True}
        assert models[1] == {"id": "mistral-7b", "name": "mistral-7b", "active": False}

    def test_returns_empty_on_connection_error(self):
        """list_models should return [] when LLM server is unreachable."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            models = _run(svc.list_models())

        assert models == []

    def test_returns_empty_on_http_error(self):
        """list_models should return [] when LLM server returns an error status."""
        error = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=error)

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            models = _run(svc.list_models())

        assert models == []

    def test_returns_empty_when_data_key_missing(self):
        """list_models should return [] when response has no 'data' key."""
        # get_active_model: /v1/model → empty id, /v1/models fallback → no data
        tabby_resp = _make_mock_response(json_data={"id": ""})
        fallback_resp = _make_mock_response(json_data={"data": []})
        list_resp = _make_mock_response(json_data={})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[tabby_resp, fallback_resp, list_resp])

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            models = _run(svc.list_models())

        assert models == []

    def test_defaults_active_to_false_when_no_active_model(self):
        """Models should default to active=False when no model is loaded."""
        # get_active_model: /v1/model → empty id, /v1/models fallback → no models
        tabby_resp = _make_mock_response(json_data={"id": ""})
        fallback_resp = _make_mock_response(json_data={"data": []})
        list_resp = _make_mock_response(json_data={
            "data": [{"id": "some-model"}]
        })
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[tabby_resp, fallback_resp, list_resp])

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            models = _run(svc.list_models())

        assert len(models) == 1
        assert models[0]["active"] is False


# ── switch_model ────────────────────────────────────────────────────────────


class TestSwitchModel:
    """Test ModelService.switch_model with mocked HTTP responses."""

    def test_switch_success(self):
        """switch_model should return True on successful POST."""
        resp = _make_mock_response()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=resp)

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.switch_model("llama-3-8b"))

        assert result is True
        mock_client.post.assert_called_once_with(
            f"{svc.base_url}/v1/model/load",
            json={"name": "llama-3-8b"},
        )

    def test_switch_returns_false_on_connection_error(self):
        """switch_model should return False when LLM server is unreachable."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.switch_model("llama-3-8b"))

        assert result is False

    def test_switch_returns_false_on_http_error(self):
        """switch_model should return False when LLM server returns an error."""
        error = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        resp = _make_mock_response(raise_for_status=error)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=resp)

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.switch_model("bad-model"))

        assert result is False

    def test_switch_returns_false_on_404_non_tabby(self):
        """switch_model should return False with warning when endpoint not found."""
        error = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=error)

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.switch_model("some-model"))

        assert result is False

    def test_switch_returns_false_on_timeout(self):
        """switch_model should return False on timeout."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ReadTimeout("Timeout"))

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.switch_model("large-model"))

        assert result is False


# ── unload_model ────────────────────────────────────────────────────────────


class TestUnloadModel:
    """Test ModelService.unload_model with mocked HTTP responses."""

    def test_unload_success(self):
        """unload_model should return True on successful POST."""
        resp = _make_mock_response()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=resp)

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.unload_model())

        assert result is True
        mock_client.post.assert_called_once_with(
            f"{svc.base_url}/v1/model/unload",
        )

    def test_unload_returns_false_on_error(self):
        """unload_model should return False on connection error."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.unload_model())

        assert result is False

    def test_unload_returns_false_on_404_non_tabby(self):
        """unload_model should return False with warning when endpoint not found."""
        error = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=error)

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.unload_model())

        assert result is False
