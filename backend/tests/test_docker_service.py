"""Tests for DockerService with mocked Docker client."""

from unittest.mock import MagicMock, patch

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


# ── stream_logs ─────────────────────────────────────────────────────────────


class TestStreamLogs:
    """Test log streaming from Docker containers."""

    @patch("backend.services.docker_service.docker.from_env")
    def test_stream_logs_returns_lines(self, mock_from_env):
        """stream_logs yields log lines from a matching container."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = _make_container("nebulus-gantry-api")
        mock_container.logs.return_value = [
            b"2026-02-03 INFO Starting server\n",
            b"2026-02-03 INFO Listening on :8000\n",
        ]
        mock_client.containers.list.return_value = [mock_container]

        service = DockerService()
        lines = list(service.stream_logs("nebulus-gantry-api"))

        assert len(lines) == 2
        assert "Starting server" in lines[0]
        mock_container.logs.assert_called_once_with(
            stream=True, follow=True, tail=100, timestamps=True
        )

    @patch("backend.services.docker_service.docker.from_env")
    def test_stream_logs_not_found_returns_empty(self, mock_from_env):
        """stream_logs yields nothing when the container doesn't exist."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.list.return_value = []

        service = DockerService()
        lines = list(service.stream_logs("nonexistent"))

        assert lines == []

    def test_stream_logs_docker_unavailable(self):
        """stream_logs yields nothing when Docker is unavailable."""
        with patch("backend.services.docker_service.docker") as mock:
            mock.from_env.side_effect = Exception("Docker not available")
            service = DockerService()
            lines = list(service.stream_logs("any"))
            assert lines == []

    @patch("backend.services.docker_service.docker.from_env")
    def test_stream_logs_custom_tail(self, mock_from_env):
        """stream_logs respects a custom tail parameter."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = _make_container("nebulus-gantry-api")
        mock_container.logs.return_value = [b"line\n"]
        mock_client.containers.list.return_value = [mock_container]

        service = DockerService()
        list(service.stream_logs("nebulus-gantry-api", tail=50))

        mock_container.logs.assert_called_once_with(
            stream=True, follow=True, tail=50, timestamps=True
        )

    @patch("backend.services.docker_service.docker.from_env")
    def test_stream_logs_handles_exception(self, mock_from_env):
        """stream_logs yields nothing when logs() raises an exception."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = _make_container("nebulus-gantry-api")
        mock_container.logs.side_effect = Exception("Connection lost")
        mock_client.containers.list.return_value = [mock_container]

        service = DockerService()
        lines = list(service.stream_logs("nebulus-gantry-api"))

        assert lines == []
