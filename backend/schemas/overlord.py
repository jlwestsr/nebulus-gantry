"""Pydantic schemas for Overlord API endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field


# ── Shared / Nested ─────────────────────────────────────────────────────────


class GitStateSchema(BaseModel):
    branch: str = ""
    clean: bool = True
    ahead: int = 0
    behind: int = 0
    last_commit: str = ""
    last_commit_date: str = ""
    stale_branches: list[str] = Field(default_factory=list)


class TestHealthSchema(BaseModel):
    has_tests: bool = False
    test_command: str | None = None


class ProjectStatusSchema(BaseModel):
    name: str
    role: str = ""
    git: GitStateSchema = Field(default_factory=GitStateSchema)
    tests: TestHealthSchema = Field(default_factory=TestHealthSchema)
    issues: list[str] = Field(default_factory=list)


# ── Tier 1: Dashboard ───────────────────────────────────────────────────────


class DaemonStatusSchema(BaseModel):
    running: bool = False
    pid: int | None = None


class ConfigSummarySchema(BaseModel):
    autonomy_levels: dict[str, str] = Field(default_factory=dict)
    scheduled_tasks: list[dict[str, object]] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    projects: list[ProjectStatusSchema] = Field(default_factory=list)
    daemon: DaemonStatusSchema = Field(default_factory=DaemonStatusSchema)
    config: ConfigSummarySchema = Field(default_factory=ConfigSummarySchema)


class GraphResponse(BaseModel):
    adjacency: dict[str, list[str]] = Field(default_factory=dict)
    ascii: str = ""


# ── Tier 2: Memory ──────────────────────────────────────────────────────────


class MemoryEntrySchema(BaseModel):
    id: str
    timestamp: str
    category: str
    project: str | None = None
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)


class MemoryListResponse(BaseModel):
    entries: list[MemoryEntrySchema] = Field(default_factory=list)
    count: int = 0


class CreateMemoryRequest(BaseModel):
    category: str
    content: str
    project: str | None = None


class CreateMemoryResponse(BaseModel):
    id: str
    message: str = "Memory created"


class DeleteMemoryResponse(BaseModel):
    message: str = "Memory deleted"


# ── Tier 3: Dispatch ────────────────────────────────────────────────────────


class ScopeSchema(BaseModel):
    projects: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    destructive: bool = False
    reversible: bool = True
    affects_remote: bool = False
    estimated_impact: str = "low"


class StepSchema(BaseModel):
    id: str
    action: str
    project: str
    dependencies: list[str] = Field(default_factory=list)
    model_tier: str | None = None
    timeout: int = 300


class PlanSchema(BaseModel):
    task: str
    steps: list[StepSchema] = Field(default_factory=list)
    scope: ScopeSchema = Field(default_factory=ScopeSchema)
    estimated_duration: int = 0
    requires_approval: bool = False


class ParseTaskRequest(BaseModel):
    task: str


class ExecuteTaskRequest(BaseModel):
    task: str
    auto_approve: bool = False


class StepResultSchema(BaseModel):
    step_id: str
    success: bool
    output: str = ""
    error: str | None = None
    duration: float = 0.0


class DispatchResultSchema(BaseModel):
    status: str
    steps: list[StepResultSchema] = Field(default_factory=list)
    reason: str = ""


class ProposalSchema(BaseModel):
    id: str
    task: str
    scope_projects: list[str] = Field(default_factory=list)
    scope_impact: str = "low"
    affects_remote: bool = False
    reason: str = ""
    state: str = "pending"
    created_at: str = ""
    resolved_at: str | None = None
    result_summary: str | None = None


class ProposalListResponse(BaseModel):
    proposals: list[ProposalSchema] = Field(default_factory=list)


class ApproveProposalResponse(BaseModel):
    message: str = "Proposal approved"
    result: DispatchResultSchema | None = None


class DenyProposalRequest(BaseModel):
    reason: str = ""


class DenyProposalResponse(BaseModel):
    message: str = "Proposal denied"


# ── Tier 4: Audit ───────────────────────────────────────────────────────────


class DetectionResultSchema(BaseModel):
    detector: str
    project: str
    severity: str
    description: str
    proposed_action: str


class DetectionListResponse(BaseModel):
    detections: list[DetectionResultSchema] = Field(default_factory=list)


class NotificationStatsSchema(BaseModel):
    urgent_count: int = 0
    buffered_count: int = 0
    last_digest_time: str | None = None


# ── Error ────────────────────────────────────────────────────────────────────


class OverlordErrorResponse(BaseModel):
    detail: str
