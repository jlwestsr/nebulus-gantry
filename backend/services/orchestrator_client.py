"""
Orchestrator HTTP client — proxy layer to Nebulus Atom's workflow orchestrator.

Gantry talks to Atom via HTTP, not direct imports.
Designed to gracefully handle Atom being unavailable.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)


class OrchestratorClient:
    """HTTP client for Atom's orchestrator API."""

    def __init__(self, base_url: str | None = None):
        """
        Initialize the orchestrator client.

        Args:
            base_url: Base URL for Atom's API (default: http://localhost:8010)
        """
        self.base_url = base_url or os.getenv("ATOM_BASE_URL", "http://localhost:8010")
        self.timeout = httpx.Timeout(30.0, connect=5.0)

    async def submit_job(
        self,
        template: str | None = None,
        workflow_yaml: str | None = None,
        inputs: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Submit a workflow job to Atom.

        Args:
            template: Built-in template name (e.g., "build-feature")
            workflow_yaml: Inline YAML workflow definition
            inputs: Input variables for the workflow

        Returns:
            Job response dict with id, status, steps, etc.

        Raises:
            httpx.HTTPError: If the request fails
        """
        if not template and not workflow_yaml:
            raise ValueError("Provide either 'template' or 'workflow_yaml'")

        payload = {"inputs": inputs or {}}
        if template:
            payload["template"] = template
        if workflow_yaml:
            payload["workflow_yaml"] = workflow_yaml

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/orchestrator/jobs",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status and results.

        Args:
            job_id: Job identifier

        Returns:
            Job response dict

        Raises:
            httpx.HTTPError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/orchestrator/jobs/{job_id}"
            )
            response.raise_for_status()
            return response.json()

    async def list_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List recent jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of job response dicts

        Raises:
            httpx.HTTPError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/orchestrator/jobs",
                params={"limit": limit},
            )
            response.raise_for_status()
            return response.json()

    async def list_templates(self) -> List[Dict[str, Any]]:
        """
        List available workflow templates.

        Returns:
            List of template info dicts (name, description, steps)

        Raises:
            httpx.HTTPError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/orchestrator/templates")
            response.raise_for_status()
            return response.json()

    async def cancel_job(self, job_id: str) -> None:
        """
        Cancel a running job (best-effort).

        Args:
            job_id: Job identifier

        Raises:
            httpx.HTTPError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                f"{self.base_url}/orchestrator/jobs/{job_id}"
            )
            response.raise_for_status()

    async def health_check(self) -> bool:
        """
        Check if Atom's orchestrator is reachable.

        Returns:
            True if reachable, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
                response = await client.get(f"{self.base_url}/orchestrator/templates")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Orchestrator health check failed: {e}")
            return False
