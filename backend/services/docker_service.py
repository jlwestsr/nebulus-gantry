"""Docker service management for Nebulus Gantry.

Provides container listing, restart, and log streaming capabilities for admin operations.
Gracefully degrades when Docker is not available (e.g., in CI or dev environments).
"""

import docker
import logging
from typing import Generator

logger = logging.getLogger(__name__)


class DockerService:
    def __init__(self):
        try:
            self.client = docker.from_env()
            self._available = True
        except Exception as e:
            logger.warning(f"Docker not available: {e}")
            self.client = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def list_services(self) -> list[dict]:
        """List Nebulus-related containers."""
        if not self.available:
            return []
        try:
            containers = self.client.containers.list(all=True)
            services = []
            for c in containers:
                # Filter for nebulus-related containers
                if any(
                    name in c.name.lower()
                    for name in ["nebulus", "tabby", "chroma", "gantry"]
                ):
                    services.append(
                        {
                            "name": c.name,
                            "status": c.status,
                            "container_id": c.short_id,
                        }
                    )
            return services
        except Exception as e:
            logger.warning(f"Failed to list services: {e}")
            return []

    def restart_service(self, service_name: str) -> bool:
        """Restart a container by name."""
        if not self.available:
            return False
        try:
            containers = self.client.containers.list(
                all=True, filters={"name": service_name}
            )
            if not containers:
                return False
            containers[0].restart()
            return True
        except Exception as e:
            logger.warning(f"Failed to restart {service_name}: {e}")
            return False

    def stream_logs(
        self, service_name: str, tail: int = 100
    ) -> Generator[str, None, None]:
        """Stream log lines from a Docker container by name.

        Args:
            service_name: Container name to stream logs from.
            tail: Number of historical lines to include before following.

        Yields:
            Decoded log lines as strings.
        """
        if not self.available:
            return
        try:
            containers = self.client.containers.list(
                all=True, filters={"name": service_name}
            )
            if not containers:
                return
            for chunk in containers[0].logs(
                stream=True, follow=True, tail=tail, timestamps=True
            ):
                yield chunk.decode("utf-8", errors="replace").rstrip("\n")
        except Exception as e:
            logger.warning(f"Failed to stream logs for {service_name}: {e}")
