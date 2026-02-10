"""Tests for ServiceManager with mocked Docker and adapter backends."""

from unittest.mock import MagicMock, patch

from backend.services.service_manager import ServiceManager


def _make_docker_available(mock_from_env):
    """Set up mock Docker client that reports as available."""
    mock_client = MagicMock()
    mock_from_env.return_value = mock_client
    return mock_client


def _make_docker_unavailable(mock_from_env):
    """Set up mock Docker client that reports as unavailable."""
    mock_from_env.side_effect = Exception("Docker not found")


# ── backend_type and available ──────────────────────────────────────────────


class TestServiceManagerBackendType:
    """Test ServiceManager.backend_type and .available properties."""

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter", return_value=None)
    def test_docker_backend(self, mock_adapter, mock_from_env):
        _make_docker_available(mock_from_env)
        sm = ServiceManager()
        assert sm.backend_type == "docker"
        assert sm.available is True

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter")
    def test_adapter_backend(self, mock_adapter, mock_from_env):
        _make_docker_unavailable(mock_from_env)
        adapter = MagicMock()
        adapter.services = []
        mock_adapter.return_value = adapter
        sm = ServiceManager()
        assert sm.backend_type == "adapter"
        assert sm.available is True

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter", return_value=None)
    def test_none_backend(self, mock_adapter, mock_from_env):
        _make_docker_unavailable(mock_from_env)
        sm = ServiceManager()
        assert sm.backend_type == "none"
        assert sm.available is False


# ── list_services ───────────────────────────────────────────────────────────


class TestServiceManagerListServices:
    """Test ServiceManager.list_services delegation."""

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter", return_value=None)
    def test_delegates_to_docker(self, mock_adapter, mock_from_env):
        mock_client = _make_docker_available(mock_from_env)
        mock_client.containers.list.return_value = [
            _make_container("nebulus-web", "running", "abc123"),
        ]
        sm = ServiceManager()
        services = sm.list_services()
        assert len(services) == 1
        assert services[0]["name"] == "nebulus-web"

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter")
    def test_falls_back_to_adapter(self, mock_adapter, mock_from_env):
        _make_docker_unavailable(mock_from_env)
        adapter = MagicMock()
        adapter.services = [
            {"name": "mlx-server", "status": "online", "id": "pm2-1"},
        ]
        mock_adapter.return_value = adapter
        sm = ServiceManager()
        services = sm.list_services()
        assert len(services) == 1
        assert services[0]["name"] == "mlx-server"
        assert services[0]["status"] == "online"

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter", return_value=None)
    def test_returns_empty_when_nothing_available(self, mock_adapter, mock_from_env):
        _make_docker_unavailable(mock_from_env)
        sm = ServiceManager()
        assert sm.list_services() == []


# ── restart_service ─────────────────────────────────────────────────────────


class TestServiceManagerRestart:
    """Test ServiceManager.restart_service delegation."""

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter", return_value=None)
    def test_delegates_restart_to_docker(self, mock_adapter, mock_from_env):
        mock_client = _make_docker_available(mock_from_env)
        container = _make_container("nebulus-web")
        mock_client.containers.list.return_value = [container]
        sm = ServiceManager()
        assert sm.restart_service("nebulus-web") is True

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter")
    def test_falls_back_restart_to_adapter(self, mock_adapter, mock_from_env):
        _make_docker_unavailable(mock_from_env)
        adapter = MagicMock()
        adapter.restart_services.return_value = True
        mock_adapter.return_value = adapter
        sm = ServiceManager()
        assert sm.restart_service("mlx-server") is True
        adapter.restart_services.assert_called_once_with("mlx-server")

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter", return_value=None)
    def test_returns_false_when_nothing_available(self, mock_adapter, mock_from_env):
        _make_docker_unavailable(mock_from_env)
        sm = ServiceManager()
        assert sm.restart_service("anything") is False


# ── stream_logs ─────────────────────────────────────────────────────────────


class TestServiceManagerStreamLogs:
    """Test ServiceManager.stream_logs delegation."""

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter", return_value=None)
    def test_streams_from_docker(self, mock_adapter, mock_from_env):
        mock_client = _make_docker_available(mock_from_env)
        container = _make_container("nebulus-web")
        container.logs.return_value = [b"log line 1\n", b"log line 2\n"]
        mock_client.containers.list.return_value = [container]
        sm = ServiceManager()
        lines = list(sm.stream_logs("nebulus-web"))
        assert len(lines) == 2

    @patch("backend.services.docker_service.docker.from_env")
    @patch("backend.services.service_manager._load_adapter", return_value=None)
    def test_yields_nothing_without_docker(self, mock_adapter, mock_from_env):
        _make_docker_unavailable(mock_from_env)
        sm = ServiceManager()
        lines = list(sm.stream_logs("anything"))
        assert lines == []


# ── helpers ─────────────────────────────────────────────────────────────────


def _make_container(name, status="running", short_id="abc123"):
    c = MagicMock()
    c.name = name
    c.status = status
    c.short_id = short_id
    return c
