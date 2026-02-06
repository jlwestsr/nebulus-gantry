"""Overlord API router — visual control plane for the meta-orchestrator.

All endpoints require admin authentication.
Returns 503 when Overlord modules are unavailable or misconfigured.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.routers.admin import require_admin
from backend.schemas.overlord import (
    ApproveProposalResponse,
    CreateMemoryRequest,
    CreateMemoryResponse,
    DashboardResponse,
    DeleteMemoryResponse,
    DenyProposalRequest,
    DenyProposalResponse,
    DetectionListResponse,
    DispatchResultSchema,
    GraphResponse,
    MemoryListResponse,
    NotificationStatsSchema,
    ParseTaskRequest,
    PlanSchema,
    ProjectStatusSchema,
    ProposalListResponse,
    ExecuteTaskRequest,
)
from backend.services.overlord_service import get_overlord_service, OverlordService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/overlord", tags=["overlord"])


def _get_service() -> OverlordService:
    """Dependency that provides the OverlordService or raises 503."""
    try:
        return get_overlord_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── Tier 1: Ecosystem Dashboard ─────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Scan all projects and return ecosystem dashboard."""
    return svc.get_dashboard()


@router.get("/scan/{project}", response_model=ProjectStatusSchema)
def scan_project(
    project: str,
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Scan a single project."""
    try:
        return svc.scan_single_project(project)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown project: {project}")


@router.get("/graph", response_model=GraphResponse)
def get_graph(
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Return dependency graph as adjacency list + ASCII."""
    return svc.get_graph()


# ── Tier 2: Memory Browser ──────────────────────────────────────────────────


@router.get("/memory", response_model=MemoryListResponse)
def list_memory(
    query: str | None = Query(None),
    category: str | None = Query(None),
    project: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """List or search memory entries."""
    return svc.list_memory(query=query, category=category, project=project, limit=limit)


@router.post("/memory", response_model=CreateMemoryResponse, status_code=201)
def add_memory(
    body: CreateMemoryRequest,
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Add a new memory entry."""
    entry_id = svc.add_memory(
        category=body.category, content=body.content, project=body.project
    )
    return {"id": entry_id, "message": "Memory created"}


@router.delete("/memory/{entry_id}", response_model=DeleteMemoryResponse)
def delete_memory(
    entry_id: str,
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Delete a memory entry."""
    deleted = svc.delete_memory(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return {"message": "Memory deleted"}


# ── Tier 3: Dispatch Console ────────────────────────────────────────────────


@router.post("/dispatch/parse", response_model=PlanSchema)
def parse_task(
    body: ParseTaskRequest,
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Parse a natural-language task into a dispatch plan."""
    try:
        return svc.parse_task(body.task)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/dispatch/execute", response_model=DispatchResultSchema)
def execute_task(
    body: ExecuteTaskRequest,
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Parse and execute a task."""
    try:
        return svc.execute_task(body.task, auto_approve=body.auto_approve)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/proposals", response_model=ProposalListResponse)
def list_proposals(
    state: str | None = Query(None),
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """List proposals, optionally filtered by state."""
    return {"proposals": svc.list_proposals(state=state)}


@router.post("/proposals/{proposal_id}/approve", response_model=ApproveProposalResponse)
def approve_proposal(
    proposal_id: str,
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Approve a pending proposal and execute it."""
    try:
        return svc.approve_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Proposal not found")


@router.post("/proposals/{proposal_id}/deny", response_model=DenyProposalResponse)
def deny_proposal(
    proposal_id: str,
    body: DenyProposalRequest,
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Deny a pending proposal."""
    try:
        svc.deny_proposal(proposal_id, reason=body.reason)
        return {"message": "Proposal denied"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Proposal not found")


# ── Tier 4: Audit Log ───────────────────────────────────────────────────────


@router.get("/audit/proposals", response_model=ProposalListResponse)
def get_audit_proposals(
    state: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Get proposal history for audit purposes."""
    return {"proposals": svc.get_audit_proposals(state=state, limit=limit)}


@router.get("/audit/detections", response_model=DetectionListResponse)
def get_detections(
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Run all detectors and return findings."""
    return {"detections": svc.get_detections()}


@router.get("/audit/notifications", response_model=NotificationStatsSchema)
def get_notification_stats(
    admin=Depends(require_admin),
    svc: OverlordService = Depends(_get_service),
):
    """Get notification buffer stats."""
    return svc.get_notification_stats()
