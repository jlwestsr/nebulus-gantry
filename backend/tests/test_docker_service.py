"""Tests for DockerService with mocked Docker client."""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from backend.services.docker_service import DockerService


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_container(name: str, status: str = "running", short_id: str = "abc123"):
    """Create a mock container object."""
    c = MagicMock()
    c.name = name
    c.status = status
    c.short_id = short_id
    return c


# ── DockerService.__init__ ───────────────────────────────────────────────────


class TestDockerServiceInit:
    """Test DockerService initialization and availability."""

    @patch("backend.services.docker_service.docker.from_env")
    def test_available_when_docker_running(self, mock_from_env):
        """DockerService.available should be True when docker.from_env succeeds."""
        mock_from_env.return_value = MagicMock()
        svc = DockerService()
        assert svc.available is True
        assert svc.client is not None

    @patch("backend.services.docker_service.docker.from_env")
    def test_unavailable_when_docker_not_running(self, mock_from_env):
        """DockerService.available should be False when docker.from_env raises."""
        mock_from_env.side_effect = Exception("Docker not found")
        svc = DockerService()
        assert svc.available is False
        assert svc.client is None


# ── list_services ────────────────────────────────────────────────────────────


class TestListServices:
    """Test DockerService.list_services with mocked Docker client."""

    @patch("backend.services.docker_service.docker.from_env")
    def test_returns_filtered_containers(self, mock_from_env):
        """Only containers with nebulus-related names should be returned."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.list.return_value = [
            _make_container("nebulus-web", "running", "abc123"),
            _make_container("tabby-server", "running", "def456"),
            _make_container("chroma-db", "exited", "ghi789"),
            _make_container("gantry-backend", "running", "jkl012"),
            _make_container("postgres-db", "running", "mno345"),  # not nebulus-related
            _make_container("redis-cache", "running", "pqr678"),  # not nebulus-related
        ]

        svc = DockerService()
        services = svc.list_services()

        assert len(services) == 4
        names = {s["name"] for s in services}
        assert names == {"nebulus-web", "tabby-server", "chroma-db", "gantry-backend"}

    @patch("backend.services.docker_service.docker.from_env")
    def test_returns_correct_fields(self, mock_from_env):
        """Each service dict should have name, status, and container_id."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.list.return_value = [
            _make_container("nebulus-web", "running", "abc123"),
        ]

        svc = DockerService()
        services = svc.list_services()

        assert len(services) == 1
        assert services[0] == {
            "name": "nebulus-web",
            "status": "running",
            "container_id": "abc123",
        }

    @patch("backend.services.docker_service.docker.from_env")
    def test_returns_empty_when_docker_unavailable(self, mock_from_env):
        """list_services should return [] when Docker is unavailable."""
        mock_from_env.side_effect = Exception("Docker not found")
        svc = DockerService()
        services = svc.list_services()
        assert services == []

    @patch("backend.services.docker_service.docker.from_env")
    def test_returns_empty_on_list_exception(self, mock_from_env):
        """list_services should return [] when containers.list raises."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.list.side_effect = Exception("Connection refused")

        svc = DockerService()
        services = svc.list_services()
        assert services == []

    @patch("backend.services.docker_service.docker.from_env")
    def test_returns_empty_when_no_matching_containers(self, mock_from_env):
        """list_services should return [] when no containers match filter."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.list.return_value = [
            _make_container("postgres-db", "running", "abc123"),
            _make_container("redis-cache", "running", "def456"),
        ]

        svc = DockerService()
        services = svc.list_services()
        assert services == []


# ── restart_service ──────────────────────────────────────────────────────────


class TestRestartService:
    """Test DockerService.restart_service with mocked Docker client."""

    @patch("backend.services.docker_service.docker.from_env")
    def test_restart_success(self, mock_from_env):
        """restart_service should return True and call container.restart()."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        container = _make_container("nebulus-web")
        mock_client.containers.list.return_value = [container]

        svc = DockerService()
        result = svc.restart_service("nebulus-web")

        assert result is True
        container.restart.assert_called_once()
        mock_client.containers.list.assert_called_once_with(
            all=True, filters={"name": "nebulus-web"}
        )

    @patch("backend.services.docker_service.docker.from_env")
    def test_restart_service_not_found(self, mock_from_env):
        """restart_service should return False when container not found."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.list.return_value = []

        svc = DockerService()
        result = svc.restart_service("nonexistent-service")

        assert result is False

    @patch("backend.services.docker_service.docker.from_env")
    def test_restart_returns_false_when_docker_unavailable(self, mock_from_env):
        """restart_service should return False when Docker is unavailable."""
        mock_from_env.side_effect = Exception("Docker not found")
        svc = DockerService()
        result = svc.restart_service("nebulus-web")
        assert result is False

    @patch("backend.services.docker_service.docker.from_env")
    def test_restart_returns_false_on_exception(self, mock_from_env):
        """restart_service should return False when restart raises."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        container = _make_container("nebulus-web")
        container.restart.side_effect = Exception("Restart failed")
        mock_client.containers.list.return_value = [container]

        svc = DockerService()
        result = svc.restart_service("nebulus-web")

        assert result is False
