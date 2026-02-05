"""Model management service for Nebulus Gantry.

Interacts with TabbyAPI (OpenAI-compatible) for listing available models
and switching the active model. Gracefully degrades when TabbyAPI is
unreachable (returns empty list / False).
"""

import httpx
import logging

from backend.config import Settings

logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self):
        self.settings = Settings()
        self.base_url = self.settings.tabby_host

    async def get_active_model(self) -> dict | None:
        """Query TabbyAPI for the currently loaded model.

        Uses the TabbyAPI-specific /v1/model endpoint.
        Returns a dict with 'id' and 'name', or None if unavailable.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/v1/model")
                response.raise_for_status()
                data = response.json()
                model_id = data.get("id", "")
                if model_id:
                    return {"id": model_id, "name": model_id}
                return None
        except Exception as e:
            logger.warning(f"Failed to get active model: {e}")
            return None

    async def list_models(self) -> list[dict]:
        """Query TabbyAPI for available models.

        Returns a list of dicts with keys: id, name, active.
        Cross-references with the active model endpoint to mark
        which model is currently loaded.
        Returns an empty list if TabbyAPI is unreachable.
        """
        try:
            active_model = await self.get_active_model()
            active_id = active_model["id"] if active_model else None

            async with httpx.AsyncClient(timeout=10.0) as client:
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
        """Switch the active model in TabbyAPI.

        Uses the TabbyAPI model loading endpoint to load a new model.
        Returns True on success, False on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/model/load",
                    json={"name": model_id},
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.warning(f"Failed to switch model: {e}")
            return False

    async def unload_model(self) -> bool:
        """Unload the current model from TabbyAPI.

        Returns True on success, False on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/model/unload",
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.warning(f"Failed to unload model: {e}")
            return False
