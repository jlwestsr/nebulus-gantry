"""Model routes for authenticated (non-admin) users.

Provides model listing and active model queries so any authenticated
user can see which models are available and which is currently loaded.
Admin-only operations (load, unload) remain in admin.py.
"""

import logging

from fastapi import APIRouter, Depends

from backend.routers.auth import get_current_user
from backend.services.model_service import ModelService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/models", tags=["models"])

_model_service = ModelService()


@router.get("")
async def list_models(user=Depends(get_current_user)):
    """List available models with active flag.

    Any authenticated user can query this to populate the model switcher.
    """
    models = await _model_service.list_models()
    return {"models": models}


@router.get("/active")
async def get_active_model(user=Depends(get_current_user)):
    """Get the currently loaded model.

    Returns the model name/id or null if no model is loaded.
    """
    model = await _model_service.get_active_model()
    return {"model": model}
