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

    _OVERLORD_AVAILABLE = True
except ImportError as exc:
    _IMPORT_ERROR = str(exc)
    logger.warning("Overlord modules not available: %s", exc)

# Daemon import is optional (requires slack_bolt which is heavy)
_OverlordDaemon = None
try:
    from nebulus_swarm.overlord.overlord_daemon import OverlordDaemon as _OverlordDaemon
except ImportError:
    logger.info("OverlordDaemon not available (slack_bolt not installed)")


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
        if _OverlordDaemon is not None:
            try:
                pid = _OverlordDaemon.read_pid()
                if pid is not None:
                    daemon_info = {
                        "running": _OverlordDaemon.check_running(pid),
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

    # ── Tier 5: Chat Routing ─────────────────────────────────────────────

    def dispatch_from_chat(  # noqa: C901
        self, request: Any
    ) -> dict[str, Any]:
        """Bridge Gantry chat dispatch to the real Dispatcher.

        Creates a work queue task, runs governance checks, and dispatches
        through the full Analyze → Brief → Provision → Execute → Review
        lifecycle.

        Args:
            request: DispatchRequest from the chat endpoint.

        Returns:
            Dict with dispatch result suitable for JSON serialisation.
        """
        try:
            from nebulus_swarm.overlord.dispatcher import Dispatcher
            from nebulus_swarm.overlord.work_queue import WorkQueue
            from nebulus_swarm.overlord.mirrors import MirrorManager
            from nebulus_swarm.overlord.governance import GovernanceEngine
        except ImportError:
            logger.warning(
                "Dispatcher modules not available, falling back to legacy dispatch"
            )
            return self.execute_task(request.user_message, auto_approve=False)

        # Infer project from context or task parser
        project = None
        if hasattr(request, "context") and request.context:
            project = getattr(request.context, "active_project", None)

        if not project:
            try:
                plan = self._task_parser.parse(request.user_message)
                if plan.scope and hasattr(plan.scope, "projects"):
                    projects = plan.scope.projects
                    if projects:
                        project = projects[0]
            except Exception:
                logger.debug("TaskParser could not extract project")

        if not project:
            project = "unknown"

        # Extract token budget
        token_budget = 50000
        if hasattr(request, "context") and request.context:
            token_budget = getattr(request.context, "token_budget", 50000) or 50000

        # Create work queue task
        queue = WorkQueue()
        task_id = queue.add_task(
            title=request.user_message[:100],
            project=project,
            description=request.user_message,
            token_budget=token_budget,
        )

        # Transition backlog → active (required before dispatch)
        queue.transition(task_id, "active", changed_by="gantry-chat")

        # Run governance check
        gov_result = self.run_governance_check(request.user_message, project)
        if not gov_result.get("approved", True):
            violations = gov_result.get("violations", [])
            reason = violations[0]["message"] if violations else "Governance rejected"
            queue.transition(
                task_id, "failed", changed_by="gantry-chat",
                reason=f"Governance: {reason}",
            )
            return {
                "status": "failed",
                "task_id": task_id,
                "reason": f"Governance: {reason}",
                "violations": violations,
            }

        # Build Dispatcher dependencies
        workspace_root = (
            self._config.workspace_root
            if hasattr(self._config, "workspace_root")
            else None
        )
        mirrors = MirrorManager(workspace_root) if workspace_root else MirrorManager()
        gov_engine = GovernanceEngine(
            self._config, queue, workspace_root=workspace_root,
        )

        # Build workers dict from available worker types
        workers: dict[str, Any] = {}
        try:
            from nebulus_swarm.overlord.workers.claude import ClaudeWorker
            from nebulus_swarm.overlord.workers.gemini import GeminiWorker
            from nebulus_swarm.overlord.workers.local import LocalWorker

            for WorkerClass in (ClaudeWorker, GeminiWorker, LocalWorker):
                try:
                    w = WorkerClass()
                    workers[w.worker_type] = w
                except Exception:
                    logger.debug("Worker %s not available", WorkerClass.__name__)
        except ImportError:
            logger.warning("Worker modules not available")

        if not workers:
            queue.transition(
                task_id, "failed", changed_by="gantry-chat",
                reason="No workers available",
            )
            return {
                "status": "failed",
                "task_id": task_id,
                "reason": "No workers available",
            }

        # Instantiate and call Dispatcher
        role = getattr(request, "role", "default") or "default"
        dispatcher = Dispatcher(
            queue=queue,
            config=self._config,
            mirrors=mirrors,
            workers=workers,
            governance=gov_engine,
        )

        try:
            result = dispatcher.dispatch_task(task_id, role=role)
        except Exception as exc:
            logger.warning("Dispatcher failed: %s", exc)
            return {
                "status": "failed",
                "task_id": task_id,
                "reason": str(exc),
            }

        # Translate DispatchResultRecord to dict
        return {
            "status": "completed",
            "task_id": result.task_id,
            "worker": result.worker_id,
            "model": result.model_id,
            "tokens_used": result.tokens_used,
            "review_status": result.review_status,
            "output": (result.output_log or "")[:500],
            "reason": "",
        }

    def get_budget_status(self) -> dict[str, Any]:
        """Return daily budget/cost status for the situation map.

        Queries WorkQueue for daily token usage and cost ledger data.
        Returns zeros with a flag when data is unavailable.
        """
        try:
            from nebulus_swarm.overlord.work_queue import WorkQueue

            queue = WorkQueue()
            usage = queue.get_daily_usage() if hasattr(queue, "get_daily_usage") else {}
            tokens_used = usage.get("tokens_used", 0)
            token_ceiling = usage.get("token_ceiling", 200000)
            cost_used = usage.get("cost_usd", 0.0)
            cost_ceiling = usage.get("cost_ceiling_usd", 10.0)
            pct = (tokens_used / token_ceiling * 100) if token_ceiling > 0 else 0.0
            return {
                "tokens_used_today": tokens_used,
                "token_ceiling": token_ceiling,
                "cost_usd_today": round(cost_used, 2),
                "cost_ceiling_usd": round(cost_ceiling, 2),
                "usage_pct": round(pct, 1),
            }
        except Exception as exc:
            logger.warning("Could not get budget status: %s", exc)
            return {
                "tokens_used_today": 0,
                "token_ceiling": 200000,
                "cost_usd_today": 0.0,
                "cost_ceiling_usd": 10.0,
                "usage_pct": 0.0,
            }

    def get_active_dispatches(self) -> list[dict[str, Any]]:
        """Return currently active/dispatched tasks for status display."""
        try:
            from nebulus_swarm.overlord.work_queue import WorkQueue

            queue = WorkQueue()
            active = queue.list_tasks(status="dispatched")
            return [
                {
                    "id": t.id,
                    "title": t.title,
                    "project": t.project,
                    "status": t.status,
                }
                for t in active
            ]
        except Exception as exc:
            logger.warning("Could not list active dispatches: %s", exc)
            return []

    def halt_all(self) -> dict[str, Any]:
        """Emergency stop — cancel all dispatched tasks and stop daemon."""
        cancelled = 0
        try:
            from nebulus_swarm.overlord.work_queue import WorkQueue

            queue = WorkQueue()
            for task in queue.list_tasks(status="dispatched"):
                queue.transition(task.id, "failed", "overlord-ui", reason="halted from Gantry")
                cancelled += 1
            for task in queue.list_tasks(status="active"):
                if getattr(task, "locked_by", None):
                    queue.transition(task.id, "failed", "overlord-ui", reason="halted from Gantry")
                    cancelled += 1
        except Exception as exc:
            logger.warning("Queue halt failed: %s", exc)

        daemon_stopped = False
        if _OverlordDaemon is not None:
            try:
                pid = _OverlordDaemon.read_pid()
                if pid and _OverlordDaemon.check_running(pid):
                    _OverlordDaemon.stop_daemon(timeout=5.0)
                    daemon_stopped = True
            except Exception as exc:
                logger.warning("Daemon stop failed: %s", exc)

        return {
            "message": f"Halted: {cancelled} task(s) cancelled, daemon {'stopped' if daemon_stopped else 'not running'}",
            "tasks_cancelled": cancelled,
            "daemon_stopped": daemon_stopped,
        }

    def run_governance_check(
        self, task_text: str, project_name: str | None = None
    ) -> dict[str, Any]:
        """Run governance pre-dispatch check for a chat-initiated task.

        Returns a dict with 'approved' and 'violations' keys.
        """
        try:
            from nebulus_swarm.overlord.governance import GovernanceEngine
            from nebulus_swarm.overlord.work_queue import WorkQueue, Task

            queue = WorkQueue()
            engine = GovernanceEngine(
                self._config, queue,
                workspace_root=self._config.workspace_root
                if hasattr(self._config, "workspace_root")
                else None,
            )

            # Build a minimal task for the check
            import uuid

            task = Task(
                id=str(uuid.uuid4()),
                title=task_text[:100],
                project=project_name or "unknown",
                status="active",
                description=task_text,
            )

            pc = self._config.projects.get(project_name) if project_name else None
            if pc is None:
                # No project config — skip governance
                return {"approved": True, "violations": []}

            result = engine.pre_dispatch_check(task, pc)
            return {
                "approved": result.approved,
                "violations": [
                    {
                        "rule": v.rule,
                        "severity": v.severity,
                        "message": v.message,
                    }
                    for v in result.violations
                ],
            }
        except ImportError:
            logger.info("Governance modules not available, skipping check")
            return {"approved": True, "violations": []}
        except Exception as exc:
            logger.warning("Governance check failed: %s", exc)
            return {"approved": True, "violations": []}


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
