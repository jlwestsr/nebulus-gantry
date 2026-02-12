"""Platform-agnostic service management for Nebulus Gantry.

Uses Docker API when available (Prime/Linux). Falls back to nebulus-core
adapter for platform-specific service management (PM2 on Edge/macOS).
Returns empty results when neither is available.
"""

import logging
from typing import Generator, Optional

from backend.services.docker_service import DockerService

logger = logging.getLogger(__name__)


def _load_adapter() -> Optional[object]:
    """Load the platform adapter (reuses backend.platform's loader)."""
    try:
        from backend.platform import _load_adapter as load
        return load()
    except Exception:
        return None


class ServiceManager:
    """Platform-agnostic service management.

    Composes DockerService (kept intact) and falls back to the
    nebulus-core platform adapter when Docker is unavailable.
    """

    def __init__(self) -> None:
        self._docker = DockerService()
        self._adapter = _load_adapter()

    @property
    def available(self) -> bool:
        """True if any service management backend is available."""
        if self._docker.available:
            return True
        if self._adapter is not None:
            try:
                return hasattr(self._adapter, "services") or hasattr(
                    self._adapter, "restart_services"
                )
            except Exception:
                pass
        return False

    @property
    def backend_type(self) -> str:
        """Return 'docker', 'adapter', or 'none'."""
        if self._docker.available:
            return "docker"
        if self._adapter is not None:
            try:
                if hasattr(self._adapter, "services") or hasattr(
                    self._adapter, "restart_services"
                ):
                    return "adapter"
            except Exception:
                pass
        return "none"

    def list_services(self) -> list[dict]:
        """List platform services."""
        if self._docker.available:
            return self._docker.list_services()
        if self._adapter is not None:
            try:
                services = self._adapter.services  # type: ignore[union-attr]
                return [
                    {
                        "name": s.get("name", "unknown"),
                        "status": s.get("status", "unknown"),
                        "container_id": s.get("id", ""),
                    }
                    for s in services
                ]
            except Exception as e:
                logger.warning(f"Adapter list_services failed: {e}")
        return []

    def restart_service(self, name: str) -> bool:
        """Restart a service by name."""
        if self._docker.available:
            return self._docker.restart_service(name)
        if self._adapter is not None:
            try:
                return self._adapter.restart_services(name)  # type: ignore[union-attr]
            except Exception as e:
                logger.warning(f"Adapter restart_service failed: {e}")
        return False

    def stream_logs(
        self, name: str, tail: int = 100
    ) -> Generator[str, None, None]:
        """Stream log lines from a service."""
        if self._docker.available:
            yield from self._docker.stream_logs(name, tail=tail)
            return
        # Adapter-based log streaming not yet supported
        logger.debug("Log streaming not available without Docker")

    def close(self) -> None:
        """Close underlying service clients."""
        self._docker.close()
