import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from backend.dependencies import get_db
from backend.models.session import Session
from backend.models.user import User
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
from backend.services.auth_service import AuthService
from backend.services.docker_service import DockerService
from backend.services.model_service import ModelService

logger = logging.getLogger(__name__)

# Singleton service instances (gracefully handle unavailable backends)
_docker_service = DockerService()
_model_service = ModelService()

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
def list_users(
    db: DBSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """List all users (does not return password hashes)."""
    users = db.query(User).all()
    return UserListResponse(users=users)


@router.post("/users", response_model=UserAdminResponse, status_code=201)
def create_user(
    request: CreateUserRequest,
    db: DBSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Create a new user. Returns 409 if the email already exists."""
    auth_service = AuthService(db)
    try:
        user = auth_service.create_user(
            email=request.email,
            password=request.password,
            display_name=request.display_name,
            role=request.role,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    return user


@router.delete("/users/{user_id}", response_model=DeleteUserResponse)
def delete_user(
    user_id: int,
    db: DBSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Delete a user by ID. Cannot delete yourself."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Delete associated sessions first to avoid FK constraint violations
    db.query(Session).filter(Session.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return DeleteUserResponse(message=f"User {user.email} deleted")


# ── Service Management ───────────────────────────────────────────────────────


@router.get("/services", response_model=ServiceListResponse)
def list_services(admin=Depends(require_admin)):
    """List Nebulus service statuses via Docker API."""
    services = _docker_service.list_services()
    return ServiceListResponse(
        services=[
            ServiceStatus(
                name=s["name"],
                status=s["status"],
                container_id=s.get("container_id"),
            )
            for s in services
        ]
    )


@router.post("/services/{service_name}/restart", response_model=RestartServiceResponse)
def restart_service(service_name: str, admin=Depends(require_admin)):
    """Restart a service by name via Docker API."""
    if not _docker_service.available:
        raise HTTPException(status_code=503, detail="Docker is not available")
    success = _docker_service.restart_service(service_name)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Service '{service_name}' not found"
        )
    return RestartServiceResponse(
        message=f"Service '{service_name}' restarted successfully",
        service=service_name,
    )


# ── Model Management ─────────────────────────────────────────────────────────


@router.get("/models", response_model=ModelListResponse)
async def list_models(admin=Depends(require_admin)):
    """List available LLM models from TabbyAPI.

    Returns an empty list if TabbyAPI is unreachable (graceful degradation).
    """
    models = await _model_service.list_models()
    return ModelListResponse(
        models=[
            ModelInfo(id=m["id"], name=m["name"], active=m["active"])
            for m in models
        ]
    )


@router.post("/models/switch", response_model=SwitchModelResponse)
async def switch_model(request: SwitchModelRequest, admin=Depends(require_admin)):
    """Switch the active LLM model in TabbyAPI.

    Returns 503 if the model switch fails (e.g., TabbyAPI unreachable).
    """
    success = await _model_service.switch_model(request.model_id)
    if not success:
        raise HTTPException(
            status_code=503,
            detail="Failed to switch model. Is TabbyAPI available?",
        )
    return SwitchModelResponse(
        message=f"Model switched to {request.model_id}",
        model_id=request.model_id,
    )


# ── Log Streaming ─────────────────────────────────────────────────────────────


@router.get("/logs/{service_name}")
async def stream_logs(service_name: str, admin=Depends(require_admin)):
    """Stream service logs via SSE. Placeholder - Task 25 will implement."""

    async def placeholder_stream() -> AsyncGenerator[str, None]:
        yield f"data: Log streaming for {service_name} not yet implemented\n\n"

    return StreamingResponse(placeholder_stream(), media_type="text/event-stream")
