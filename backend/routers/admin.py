import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.routers.auth import get_current_user
from backend.schemas.admin import (
    CreateUserRequest,
    DeleteUserResponse,
    ModelInfo,
    ModelListResponse,
    RestartServiceResponse,
    ServiceListResponse,
    ServiceStatus,
    SwitchModelRequest,
    SwitchModelResponse,
    UserAdminResponse,
    UserListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(user=Depends(get_current_user)):
    """Dependency that ensures the current user has admin role.

    Raises HTTPException 403 if user is not an admin.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── User Management ──────────────────────────────────────────────────────────


@router.get("/users", response_model=UserListResponse)
def list_users(admin=Depends(require_admin)):
    """List all users. Placeholder - Task 24 will implement."""
    return UserListResponse(users=[])


@router.post("/users", response_model=UserAdminResponse, status_code=201)
def create_user(request: CreateUserRequest, admin=Depends(require_admin)):
    """Create a new user. Placeholder - Task 24 will implement."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/users/{user_id}", response_model=DeleteUserResponse)
def delete_user(user_id: int, admin=Depends(require_admin)):
    """Delete a user by ID. Placeholder - Task 24 will implement."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


# ── Service Management ───────────────────────────────────────────────────────


@router.get("/services", response_model=ServiceListResponse)
def list_services(admin=Depends(require_admin)):
    """List Nebulus service statuses. Placeholder - Task 25 will implement."""
    return ServiceListResponse(services=[])


@router.post("/services/{service_name}/restart", response_model=RestartServiceResponse)
def restart_service(service_name: str, admin=Depends(require_admin)):
    """Restart a service by name. Placeholder - Task 25 will implement."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


# ── Model Management ─────────────────────────────────────────────────────────


@router.get("/models", response_model=ModelListResponse)
def list_models(admin=Depends(require_admin)):
    """List available LLM models. Placeholder - Task 26 will implement."""
    return ModelListResponse(models=[])


@router.post("/models/switch", response_model=SwitchModelResponse)
def switch_model(request: SwitchModelRequest, admin=Depends(require_admin)):
    """Switch the active LLM model. Placeholder - Task 26 will implement."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


# ── Log Streaming ─────────────────────────────────────────────────────────────


@router.get("/logs/{service_name}")
async def stream_logs(service_name: str, admin=Depends(require_admin)):
    """Stream service logs via SSE. Placeholder - Task 25 will implement."""

    async def placeholder_stream() -> AsyncGenerator[str, None]:
        yield f"data: Log streaming for {service_name} not yet implemented\n\n"

    return StreamingResponse(placeholder_stream(), media_type="text/event-stream")
