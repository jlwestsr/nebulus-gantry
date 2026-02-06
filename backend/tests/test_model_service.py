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


def _patch_async_client(get_responses=None, post_response=None, get_side_effect=None,
                        post_side_effect=None):
    """Create a context manager that patches httpx.AsyncClient with given responses.

    get_responses: list of responses for successive GET calls.
    post_response: single response for POST calls.
    """
    mock_client = AsyncMock()

    if get_side_effect:
        mock_client.get = AsyncMock(side_effect=get_side_effect)
    elif get_responses:
        mock_client.get = AsyncMock(side_effect=get_responses)
    else:
        mock_client.get = AsyncMock(return_value=MagicMock())

    if post_side_effect:
        mock_client.post = AsyncMock(side_effect=post_side_effect)
    elif post_response:
        mock_client.post = AsyncMock(return_value=post_response)

    patcher = patch("backend.services.model_service.httpx.AsyncClient")
    return patcher, mock_client


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
    """Test ModelService.get_active_model."""

    def test_returns_active_model(self):
        """get_active_model should return dict with id and name."""
        resp = _make_mock_response(json_data={"id": "llama-3-8b"})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=resp)

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.get_active_model())

        assert result == {"id": "llama-3-8b", "name": "llama-3-8b"}

    def test_returns_none_when_no_model_loaded(self):
        """get_active_model should return None when no model is loaded."""
        resp = _make_mock_response(json_data={"id": ""})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=resp)

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.get_active_model())

        assert result is None

    def test_returns_none_on_connection_error(self):
        """get_active_model should return None when TabbyAPI is unreachable."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.get_active_model())

        assert result is None


# ── list_models ─────────────────────────────────────────────────────────────


class TestListModels:
    """Test ModelService.list_models with mocked HTTP responses.

    Note: list_models() internally calls get_active_model() first (GET /v1/model),
    then fetches the model list (GET /v1/models). Both use separate httpx clients,
    so we need to mock both GET calls.
    """

    def test_returns_parsed_models_with_active_flag(self):
        """list_models should mark the active model correctly."""
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
        """list_models should return [] when TabbyAPI is unreachable."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            models = _run(svc.list_models())

        assert models == []

    def test_returns_empty_on_http_error(self):
        """list_models should return [] when TabbyAPI returns an error status."""
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
        active_resp = _make_mock_response(json_data={"id": ""})
        list_resp = _make_mock_response(json_data={})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[active_resp, list_resp])

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            models = _run(svc.list_models())

        assert models == []

    def test_defaults_active_to_false_when_no_active_model(self):
        """Models should default to active=False when no model is loaded."""
        active_resp = _make_mock_response(json_data={"id": ""})
        list_resp = _make_mock_response(json_data={
            "data": [{"id": "some-model"}]
        })
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[active_resp, list_resp])

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
            json={"model_name": "llama-3-8b"},
        )

    def test_switch_returns_false_on_connection_error(self):
        """switch_model should return False when TabbyAPI is unreachable."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with _AsyncClientPatch(mock_client):
            svc = ModelService()
            result = _run(svc.switch_model("llama-3-8b"))

        assert result is False

    def test_switch_returns_false_on_http_error(self):
        """switch_model should return False when TabbyAPI returns an error."""
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
