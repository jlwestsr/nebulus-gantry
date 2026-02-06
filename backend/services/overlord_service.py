"""Facade wrapping all Overlord module imports.

Provides graceful degradation if nebulus-atom is not on PYTHONPATH
or overlord.yml is missing.
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy import guard ────────────────────────────────────────────────────────

_OVERLORD_AVAILABLE = False
_IMPORT_ERROR: str | None = None

try:
    from nebulus_swarm.overlord.registry import (
        OverlordConfig,
        load_config,
    )
    from nebulus_swarm.overlord.scanner import scan_ecosystem, scan_project
    from nebulus_swarm.overlord.graph import DependencyGraph
    from nebulus_swarm.overlord.memory import OverlordMemory
    from nebulus_swarm.overlord.autonomy import AutonomyEngine, get_autonomy_summary
    from nebulus_swarm.overlord.dispatch import DispatchEngine, DispatchPlan
    from nebulus_swarm.overlord.model_router import ModelRouter
    from nebulus_swarm.overlord.task_parser import TaskParser
    from nebulus_swarm.overlord.proposal_manager import ProposalStore, ProposalState
    from nebulus_swarm.overlord.detectors import DetectionEngine
    from nebulus_swarm.overlord.overlord_daemon import OverlordDaemon

    _OVERLORD_AVAILABLE = True
except ImportError as exc:
    _IMPORT_ERROR = str(exc)
    logger.warning("Overlord modules not available: %s", exc)


# ── Service ──────────────────────────────────────────────────────────────────


class OverlordService:
    """Facade for all Overlord operations.

    Instantiates the required Overlord objects from ``~/.atom/overlord.yml``.
    All public methods return plain dicts suitable for JSON serialisation.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        if not _OVERLORD_AVAILABLE:
            raise RuntimeError(
                f"Overlord modules not available: {_IMPORT_ERROR}"
            )

        self._config_path = config_path or Path.home() / ".atom" / "overlord.yml"
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Overlord config not found at {self._config_path}"
            )

        self._config: OverlordConfig = load_config(self._config_path)
        self._graph = DependencyGraph(self._config)
        self._memory = OverlordMemory()
        self._autonomy = AutonomyEngine(self._config)
        self._model_router = ModelRouter(self._config)
        self._dispatch = DispatchEngine(
            self._config, self._autonomy, self._graph, self._model_router
        )
        self._task_parser = TaskParser(self._graph)

        # Proposal store (sqlite in ~/.atom/overlord/)
        proposals_db = Path.home() / ".atom" / "overlord" / "proposals.db"
        self._proposal_store = ProposalStore(str(proposals_db))

        self._detection_engine = DetectionEngine(
            self._config, self._graph, self._autonomy
        )

    # ── Tier 1: Dashboard ────────────────────────────────────────────────

    def get_dashboard(self) -> dict[str, Any]:
        """Scan all projects and return dashboard data."""
        statuses = scan_ecosystem(self._config)
        projects = []
        for s in statuses:
            projects.append({
                "name": s.name,
                "role": s.config.role if s.config else "",
                "git": asdict(s.git),
                "tests": asdict(s.tests),
                "issues": s.issues,
            })

        # Daemon status
        daemon_info = {"running": False, "pid": None}
        try:
            pid = OverlordDaemon.read_pid()
            if pid is not None:
                daemon_info = {
                    "running": OverlordDaemon.check_running(pid),
                    "pid": pid,
                }
        except Exception:
            pass

        # Config summary
        autonomy_levels = get_autonomy_summary(self._config)
        scheduled_tasks: list[dict[str, object]] = []
        for task in self._config.schedule.tasks:
            scheduled_tasks.append({
                "name": task.name,
                "cron": task.cron,
                "enabled": task.enabled,
            })

        return {
            "projects": projects,
            "daemon": daemon_info,
            "config": {
                "autonomy_levels": autonomy_levels,
                "scheduled_tasks": scheduled_tasks,
            },
        }

    def scan_single_project(self, project_name: str) -> dict[str, Any]:
        """Scan a single project by name."""
        if project_name not in self._config.projects:
            raise KeyError(f"Unknown project: {project_name}")

        status = scan_project(self._config.projects[project_name])
        return {
            "name": status.name,
            "role": status.config.role if status.config else "",
            "git": asdict(status.git),
            "tests": asdict(status.tests),
            "issues": status.issues,
        }

    def get_graph(self) -> dict[str, Any]:
        """Return dependency graph as adjacency list + ASCII render."""
        adjacency: dict[str, list[str]] = {}
        for name in self._config.projects:
            adjacency[name] = self._graph.get_downstream(name)

        return {
            "adjacency": adjacency,
            "ascii": self._graph.render_ascii(),
        }

    # ── Tier 2: Memory ───────────────────────────────────────────────────

    def list_memory(
        self,
        query: str | None = None,
        category: str | None = None,
        project: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List or search memory entries."""
        if query:
            entries = self._memory.search(
                query=query, category=category, project=project, limit=limit
            )
        else:
            entries = self._memory.get_recent(limit=limit)
            # Apply filters manually for get_recent
            if category:
                entries = [e for e in entries if e.category == category]
            if project:
                entries = [e for e in entries if e.project == project]

        result = [asdict(e) for e in entries]
        return {"entries": result, "count": len(result)}

    def add_memory(
        self, category: str, content: str, project: str | None = None
    ) -> str:
        """Add a memory entry. Returns the new entry ID."""
        return self._memory.remember(
            category=category, content=content, project=project
        )

    def delete_memory(self, entry_id: str) -> bool:
        """Delete a memory entry. Returns True if deleted."""
        return self._memory.forget(entry_id)

    # ── Tier 3: Dispatch ─────────────────────────────────────────────────

    def parse_task(self, task: str) -> dict[str, Any]:
        """Parse a natural-language task into a dispatch plan."""
        plan: DispatchPlan = self._task_parser.parse(task)
        return {
            "task": plan.task,
            "steps": [asdict(s) for s in plan.steps],
            "scope": asdict(plan.scope),
            "estimated_duration": plan.estimated_duration,
            "requires_approval": plan.requires_approval,
        }

    def execute_task(
        self, task: str, auto_approve: bool = False
    ) -> dict[str, Any]:
        """Parse and execute a task. Returns dispatch result."""
        plan = self._task_parser.parse(task)
        result = self._dispatch.execute(plan, auto_approve=auto_approve)
        return {
            "status": result.status,
            "steps": [asdict(s) for s in result.steps],
            "reason": result.reason,
        }

    def list_proposals(self, state: str | None = None) -> list[dict[str, Any]]:
        """List proposals, optionally filtered by state."""
        if state == "pending":
            proposals = self._proposal_store.list_pending()
        else:
            proposals = self._proposal_store.list_all()

        if state and state != "pending":
            proposals = [
                p for p in proposals if p.state.value == state
            ]

        return [
            {
                "id": p.id,
                "task": p.task,
                "scope_projects": p.scope_projects,
                "scope_impact": p.scope_impact,
                "affects_remote": p.affects_remote,
                "reason": p.reason,
                "state": p.state.value if hasattr(p.state, "value") else str(p.state),
                "created_at": p.created_at,
                "resolved_at": p.resolved_at,
                "result_summary": p.result_summary,
            }
            for p in proposals
        ]

    def approve_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Approve a proposal and execute it."""
        proposal = self._proposal_store.get(proposal_id)
        if not proposal:
            raise KeyError(f"Proposal not found: {proposal_id}")

        self._proposal_store.update_state(proposal_id, ProposalState.APPROVED)

        # Try to execute the approved proposal
        try:
            plan = self._task_parser.parse(proposal.task)
            result = self._dispatch.execute(plan, auto_approve=True)
            self._proposal_store.update_state(
                proposal_id,
                ProposalState.COMPLETED if result.status == "success" else ProposalState.FAILED,
                result_summary=result.reason or result.status,
            )
            return {
                "message": "Proposal approved and executed",
                "result": {
                    "status": result.status,
                    "steps": [asdict(s) for s in result.steps],
                    "reason": result.reason,
                },
            }
        except Exception as exc:
            self._proposal_store.update_state(
                proposal_id, ProposalState.FAILED, result_summary=str(exc)
            )
            raise

    def deny_proposal(self, proposal_id: str, reason: str = "") -> None:
        """Deny a proposal."""
        proposal = self._proposal_store.get(proposal_id)
        if not proposal:
            raise KeyError(f"Proposal not found: {proposal_id}")
        self._proposal_store.update_state(
            proposal_id, ProposalState.DENIED, result_summary=reason
        )

    # ── Tier 4: Audit ────────────────────────────────────────────────────

    def get_audit_proposals(
        self, state: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get proposal history for audit."""
        proposals = self.list_proposals(state=state)
        return proposals[:limit]

    def get_detections(self) -> list[dict[str, Any]]:
        """Run all detectors and return findings."""
        results = self._detection_engine.run_all()
        return [asdict(r) for r in results]

    def get_notification_stats(self) -> dict[str, Any]:
        """Return notification buffer stats."""
        # NotificationManager requires a SlackBot which we don't have
        # in the web context. Return basic stats from proposal store.
        pending = self._proposal_store.list_pending()
        return {
            "urgent_count": len([p for p in pending if p.scope_impact == "high"]),
            "buffered_count": len(pending),
            "last_digest_time": None,
        }


# ── Singleton with lazy init ────────────────────────────────────────────────

_service_instance: OverlordService | None = None
_service_error: str | None = None


def get_overlord_service() -> OverlordService:
    """Get or create the singleton OverlordService.

    Raises RuntimeError if overlord is not available.
    """
    global _service_instance, _service_error

    if _service_instance is not None:
        return _service_instance

    if _service_error is not None:
        raise RuntimeError(_service_error)

    try:
        _service_instance = OverlordService()
        return _service_instance
    except (RuntimeError, FileNotFoundError) as exc:
        _service_error = str(exc)
        raise RuntimeError(_service_error) from exc


def reset_overlord_service() -> None:
    """Reset the singleton (useful for testing)."""
    global _service_instance, _service_error
    _service_instance = None
    _service_error = None
