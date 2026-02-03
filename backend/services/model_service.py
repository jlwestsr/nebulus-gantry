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

    async def list_models(self) -> list[dict]:
        """Query TabbyAPI for available models.

        Returns a list of dicts with keys: id, name, active.
        Returns an empty list if TabbyAPI is unreachable.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/v1/models")
                response.raise_for_status()
                data = response.json()
                models = []
                for model in data.get("data", []):
                    models.append({
                        "id": model["id"],
                        "name": model.get("id", "unknown"),
                        "active": model.get("active", False),
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
