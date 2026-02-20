"""Model management service for Nebulus Gantry.

Interacts with the LLM server (OpenAI-compatible) for listing available models
and switching the active model. Supports TabbyAPI-specific endpoints
(/v1/model, /v1/model/load, /v1/model/unload) when available, with graceful
fallback to standard OpenAI endpoints for other servers.
"""

import httpx
import logging

from backend.platform import get_llm_base_url
from backend.services.llm_service import _get_llm_headers

logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self):
        self.base_url = get_llm_base_url()
        self.headers = _get_llm_headers()

    async def get_active_model(self) -> dict | None:
        """Query the LLM server for the currently loaded model.

        Tries the TabbyAPI-specific /v1/model endpoint first. Falls back
        to the first model from the standard /v1/models list.
        Returns a dict with 'id' and 'name', or None if unavailable.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=self.headers) as client:
                # Try TabbyAPI-specific endpoint first
                try:
                    response = await client.get(f"{self.base_url}/v1/model")
                    response.raise_for_status()
                    data = response.json()
                    model_id = data.get("id", "")
                    if model_id:
                        return {"id": model_id, "name": model_id}
                except (httpx.HTTPStatusError, httpx.ConnectError):
                    pass

                # Fallback: first model from standard OpenAI /v1/models
                try:
                    response = await client.get(f"{self.base_url}/v1/models")
                    response.raise_for_status()
                    data = response.json()
                    models = data.get("data", [])
                    if models:
                        model_id = models[0].get("id", "")
                        if model_id:
                            return {"id": model_id, "name": model_id}
                except (httpx.HTTPStatusError, httpx.ConnectError):
                    pass

                return None
        except Exception as e:
            logger.warning(f"Failed to get active model: {e}")
            return None

    async def list_models(self) -> list[dict]:
        """Query the LLM server for available models.

        Returns a list of dicts with keys: id, name, active.
        Cross-references with the active model endpoint to mark
        which model is currently loaded.
        Returns an empty list if the LLM server is unreachable.
        """
        try:
            active_model = await self.get_active_model()
            active_id = active_model["id"] if active_model else None

            async with httpx.AsyncClient(timeout=10.0, headers=self.headers) as client:
                response = await client.get(f"{self.base_url}/v1/models")
                response.raise_for_status()
                data = response.json()
                models = []
                for model in data.get("data", []):
                    model_id = model["id"]
                    models.append({
                        "id": model_id,
                        "name": model.get("id", "unknown"),
                        "active": model.get("active", model_id == active_id),
                    })
                return models
        except Exception as e:
            logger.warning(f"Failed to list models: {e}")
            return []

    async def switch_model(self, model_id: str) -> bool:
        """Switch the active model on the LLM server.

        Tries the TabbyAPI-specific /v1/model/load endpoint. Returns False
        with a warning on non-TabbyAPI servers (model switching not supported).
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                response = await client.post(
                    f"{self.base_url}/v1/model/load",
                    json={"name": model_id},
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    "Model switching not supported by this LLM server "
                    "(TabbyAPI /v1/model/load endpoint not found)"
                )
            else:
                logger.warning(f"Failed to switch model: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to switch model: {e}")
            return False

    async def unload_model(self) -> bool:
        """Unload the current model from the LLM server.

        Tries the TabbyAPI-specific /v1/model/unload endpoint. Returns False
        with a warning on non-TabbyAPI servers (model unloading not supported).
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                response = await client.post(
                    f"{self.base_url}/v1/model/unload",
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    "Model unloading not supported by this LLM server "
                    "(TabbyAPI /v1/model/unload endpoint not found)"
                )
            else:
                logger.warning(f"Failed to unload model: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to unload model: {e}")
            return False
