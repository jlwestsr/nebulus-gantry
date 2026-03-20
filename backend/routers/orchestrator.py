"""
Orchestrator API router — proxy to Nebulus Atom's workflow orchestrator.

All endpoints require admin authentication.
Returns 503 when Atom is unreachable.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from backend.config import settings
from backend.routers.admin import require_admin
from backend.services.orchestrator_client import OrchestratorClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


# -------------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------------


class JobSubmitRequest(BaseModel):
    """Request schema for submitting a workflow job."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "template": "build-feature",
                    "inputs": {"goal": "Add JWT authentication to the FastAPI backend"},
                },
                {
                    "template": "fix-bug",
                    "inputs": {
                        "goal": "Login endpoint returns 500 when email contains special chars"
                    },
                },
            ]
        }
    )

    template: str | None = None
    workflow_yaml: str | None = None
    inputs: Dict[str, Any] = {}


class StepResultResponse(BaseModel):
    """Response schema for a workflow step result."""

    status: str
    output: str | None = None
    error: str | None = None
    duration_seconds: float | None = None
    model_used: str | None = None


class JobResponse(BaseModel):
    """Response schema for a workflow job."""

    id: str
    workflow: str
    status: str
    inputs: Dict[str, Any]
    steps: Dict[str, StepResultResponse]
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class TemplateInfo(BaseModel):
    """Response schema for a workflow template."""

    name: str
    description: str
    steps: List[str]


class HealthResponse(BaseModel):
    """Response schema for orchestrator health check."""

    available: bool
    base_url: str


# -------------------------------------------------------------------------
# Dependency
# -------------------------------------------------------------------------


def get_client() -> OrchestratorClient:
    """Get the orchestrator client instance."""
    return OrchestratorClient(base_url=settings.atom_base_url)


# -------------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def check_health(client: OrchestratorClient = Depends(get_client)):
    """Check if Atom's orchestrator is reachable (unauthenticated probe)."""
    available = await client.health_check()
    return HealthResponse(available=available, base_url=client.base_url)


@router.post("/jobs", response_model=JobResponse, status_code=202)
async def submit_job(
    request: JobSubmitRequest,
    admin=Depends(require_admin),
    client: OrchestratorClient = Depends(get_client),
):
    """Submit a workflow job to Atom's orchestrator."""
    try:
        result = await client.submit_job(
            template=request.template,
            workflow_yaml=request.workflow_yaml,
            inputs=request.inputs,
        )
        return JobResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to submit job to Atom orchestrator")
        raise HTTPException(
            status_code=503,
            detail=f"Orchestrator unavailable: {str(e)}",
        )


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    admin=Depends(require_admin),
    client: OrchestratorClient = Depends(get_client),
):
    """List recent workflow jobs from Atom's orchestrator."""
    try:
        results = await client.list_jobs(limit=limit)
        return [JobResponse(**job) for job in results]
    except Exception as e:
        logger.exception("Failed to list jobs from Atom orchestrator")
        raise HTTPException(
            status_code=503,
            detail=f"Orchestrator unavailable: {str(e)}",
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    admin=Depends(require_admin),
    client: OrchestratorClient = Depends(get_client),
):
    """Get job status and results from Atom's orchestrator."""
    try:
        result = await client.get_job(job_id)
        return JobResponse(**result)
    except httpx.HTTPStatusError as e:
        logger.exception(f"Failed to get job {job_id} from Atom orchestrator")
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        raise HTTPException(
            status_code=503,
            detail=f"Orchestrator unavailable: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"Failed to get job {job_id} from Atom orchestrator")
        raise HTTPException(
            status_code=503,
            detail=f"Orchestrator unavailable: {str(e)}",
        )


@router.get("/templates", response_model=List[TemplateInfo])
async def list_templates(
    admin=Depends(require_admin),
    client: OrchestratorClient = Depends(get_client),
):
    """List available workflow templates from Atom's orchestrator."""
    try:
        results = await client.list_templates()
        return [TemplateInfo(**template) for template in results]
    except Exception as e:
        logger.exception("Failed to list templates from Atom orchestrator")
        raise HTTPException(
            status_code=503,
            detail=f"Orchestrator unavailable: {str(e)}",
        )


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(
    job_id: str,
    admin=Depends(require_admin),
    client: OrchestratorClient = Depends(get_client),
):
    """Cancel a running workflow job in Atom's orchestrator (best-effort)."""
    try:
        await client.cancel_job(job_id)
    except httpx.HTTPStatusError as e:
        logger.exception(f"Failed to cancel job {job_id} in Atom orchestrator")
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        if e.response.status_code == 409:
            raise HTTPException(status_code=409, detail="Job is not running")
        raise HTTPException(
            status_code=503,
            detail=f"Orchestrator unavailable: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"Failed to cancel job {job_id} in Atom orchestrator")
        raise HTTPException(
            status_code=503,
            detail=f"Orchestrator unavailable: {str(e)}",
        )
