"""
Personas Router for managing reusable personas.

Endpoints for user persona CRUD operations.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from backend.dependencies import get_db
from backend.routers.auth import get_current_user
from backend.services.persona_service import PersonaService
from backend.schemas.persona import (
    PersonaCreate,
    PersonaUpdate,
    PersonaResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/personas", tags=["personas"])


def get_persona_service(db: DBSession = Depends(get_db)) -> PersonaService:
    return PersonaService(db)


@router.post("", response_model=PersonaResponse)
def create_persona(
    data: PersonaCreate,
    user=Depends(get_current_user),
    service: PersonaService = Depends(get_persona_service),
):
    """Create a new persona."""
    persona = service.create_persona(
        user_id=user.id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        temperature=data.temperature,
        model_id=data.model_id,
    )
    return _persona_to_response(persona)


@router.get("", response_model=list[PersonaResponse])
def list_personas(
    user=Depends(get_current_user),
    service: PersonaService = Depends(get_persona_service),
):
    """List all personas available to the current user (own + system)."""
    personas = service.list_personas(user.id)
    return [_persona_to_response(p) for p in personas]


@router.get("/{persona_id}", response_model=PersonaResponse)
def get_persona(
    persona_id: int,
    user=Depends(get_current_user),
    service: PersonaService = Depends(get_persona_service),
):
    """Get a single persona."""
    persona = service.get_persona(persona_id, user.id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return _persona_to_response(persona)


@router.patch("/{persona_id}", response_model=PersonaResponse)
def update_persona(
    persona_id: int,
    data: PersonaUpdate,
    user=Depends(get_current_user),
    service: PersonaService = Depends(get_persona_service),
):
    """Update a persona (only own personas, not system)."""
    persona = service.update_persona(
        persona_id=persona_id,
        user_id=user.id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        temperature=data.temperature,
        model_id=data.model_id,
    )
    if not persona:
        raise HTTPException(
            status_code=404,
            detail="Persona not found or you don't have permission to edit it",
        )
    return _persona_to_response(persona)


@router.delete("/{persona_id}")
def delete_persona(
    persona_id: int,
    user=Depends(get_current_user),
    service: PersonaService = Depends(get_persona_service),
):
    """Delete a persona (only own personas, not system)."""
    if not service.delete_persona(persona_id, user.id):
        raise HTTPException(
            status_code=404,
            detail="Persona not found or you don't have permission to delete it",
        )
    return {"message": "Persona deleted"}


def _persona_to_response(persona) -> PersonaResponse:
    """Convert a Persona model to response."""
    return PersonaResponse(
        id=persona.id,
        user_id=persona.user_id,
        name=persona.name,
        description=persona.description,
        system_prompt=persona.system_prompt,
        temperature=persona.temperature,
        model_id=persona.model_id,
        is_default=persona.is_default,
        is_system=persona.user_id is None,
        created_at=persona.created_at,
    )
