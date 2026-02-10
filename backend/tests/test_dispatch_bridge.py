"""Tests for the dispatch bridge — OverlordService.dispatch_from_chat().

Validates that Gantry's chat dispatch routes through the real Dispatcher
(GAP-1 fix) with governance enforcement (GAP-2 fix) and graceful fallback.
"""
import os
import sys
from dataclasses import dataclass
from types import ModuleType
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402

from backend.schemas.dispatch import DispatchRequest, DispatchContext  # noqa: E402


# ── Fake module injection ────────────────────────────────────────────────────
# nebulus_swarm isn't installed in Gantry's venv, so we inject mock modules
# into sys.modules to satisfy the lazy imports in dispatch_from_chat().


@dataclass
class FakeDispatchResultRecord:
    """Mimics DispatchResultRecord for testing."""

    task_id: str = "fake-task-id"
    worker_id: str = "claude"
    model_id: str = "opus"
    branch_name: str = "atom/fake1234"
    mission_brief_path: str = ""
    review_status: str = "passed"
    usage_stats: dict = None
    output_log: str = "Task completed successfully"
    tokens_used: int = 1500

    def __post_init__(self):
        if self.usage_stats is None:
            self.usage_stats = {}


# Mock module hierarchy for nebulus_swarm
_mock_modules: dict[str, ModuleType] = {}


def _setup_mock_modules(
    mock_queue_cls: MagicMock,
    mock_dispatcher_cls: MagicMock,
    mock_mirror_cls: MagicMock,
    mock_governance_cls: MagicMock,
    mock_claude_cls: MagicMock | None = None,
    mock_gemini_cls: MagicMock | None = None,
    mock_local_cls: MagicMock | None = None,
) -> dict[str, ModuleType]:
    """Inject fake nebulus_swarm modules into sys.modules."""
    mods = {}

    for name in [
        "nebulus_swarm",
        "nebulus_swarm.overlord",
        "nebulus_swarm.overlord.dispatcher",
        "nebulus_swarm.overlord.work_queue",
        "nebulus_swarm.overlord.mirrors",
        "nebulus_swarm.overlord.governance",
        "nebulus_swarm.overlord.workers",
        "nebulus_swarm.overlord.workers.claude",
        "nebulus_swarm.overlord.workers.gemini",
        "nebulus_swarm.overlord.workers.local",
    ]:
        mod = ModuleType(name)
        mods[name] = mod

    mods["nebulus_swarm.overlord.dispatcher"].Dispatcher = mock_dispatcher_cls
    mods["nebulus_swarm.overlord.work_queue"].WorkQueue = mock_queue_cls
    mods["nebulus_swarm.overlord.mirrors"].MirrorManager = mock_mirror_cls
    mods["nebulus_swarm.overlord.governance"].GovernanceEngine = mock_governance_cls

    # Worker classes with worker_type attribute
    if mock_claude_cls is None:
        mock_claude_cls = MagicMock()
        inst = MagicMock()
        inst.worker_type = "claude"
        mock_claude_cls.return_value = inst
    if mock_gemini_cls is None:
        mock_gemini_cls = MagicMock()
        inst = MagicMock()
        inst.worker_type = "gemini"
        mock_gemini_cls.return_value = inst
    if mock_local_cls is None:
        mock_local_cls = MagicMock()
        inst = MagicMock()
        inst.worker_type = "local"
        mock_local_cls.return_value = inst

    mods["nebulus_swarm.overlord.workers.claude"].ClaudeWorker = mock_claude_cls
    mods["nebulus_swarm.overlord.workers.gemini"].GeminiWorker = mock_gemini_cls
    mods["nebulus_swarm.overlord.workers.local"].LocalWorker = mock_local_cls

    return mods


@pytest.fixture
def inject_modules():
    """Context manager that injects and cleans up mock nebulus_swarm modules."""
    original = {}
    injected_keys: list[str] = []

    def _inject(mods: dict[str, ModuleType]):
        for name, mod in mods.items():
            if name in sys.modules:
                original[name] = sys.modules[name]
            sys.modules[name] = mod
            injected_keys.append(name)

    yield _inject

    for name in injected_keys:
        if name in original:
            sys.modules[name] = original[name]
        else:
            sys.modules.pop(name, None)


def _make_mock_service():
    """Create a mock OverlordService with the necessary attributes."""
    svc = MagicMock()

    # TaskParser mock for project inference
    mock_scope = MagicMock()
    mock_scope.projects = ["nebulus-core"]
    mock_plan = MagicMock()
    mock_plan.scope = mock_scope
    svc._task_parser.parse.return_value = mock_plan

    # Config mock
    svc._config.workspace_root = "/tmp/test-workspace"
    svc._config.projects = {
        "nebulus-core": MagicMock(name="nebulus-core", path="/tmp/nebulus-core"),
    }

    # run_governance_check — default to approved
    svc.run_governance_check.return_value = {
        "approved": True,
        "violations": [],
    }

    return svc


# ── Tests: dispatch_from_chat ────────────────────────────────────────────────


class TestDispatchFromChat:
    def test_creates_work_queue_task_and_dispatches(self, inject_modules):
        """dispatch_from_chat should create a task and call Dispatcher."""
        request = DispatchRequest(
            user_message="build auth feature for nebulus-core",
            context=DispatchContext(active_project="nebulus-core", token_budget=25000),
        )

        mock_queue = MagicMock()
        mock_queue.add_task.return_value = "test-task-id-001"

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_task.return_value = FakeDispatchResultRecord(
            task_id="test-task-id-001"
        )

        mods = _setup_mock_modules(
            mock_queue_cls=MagicMock(return_value=mock_queue),
            mock_dispatcher_cls=MagicMock(return_value=mock_dispatcher),
            mock_mirror_cls=MagicMock(),
            mock_governance_cls=MagicMock(),
        )
        inject_modules(mods)

        mock_svc = _make_mock_service()

        from backend.services.overlord_service import OverlordService

        result = OverlordService.dispatch_from_chat(mock_svc, request)

        assert result["status"] == "completed"
        assert result["task_id"] == "test-task-id-001"
        mock_queue.add_task.assert_called_once()
        # Verify token_budget was passed
        _, kwargs = mock_queue.add_task.call_args
        assert kwargs.get("token_budget") == 25000

    def test_governance_rejection_returns_error(self, inject_modules):
        """When governance rejects, should return failure without dispatching."""
        request = DispatchRequest(
            user_message="build feature in root workspace",
            context=DispatchContext(active_project="nebulus-core"),
        )

        mock_queue = MagicMock()
        mock_queue.add_task.return_value = "test-task-id-002"

        mock_disp_cls = MagicMock()

        mods = _setup_mock_modules(
            mock_queue_cls=MagicMock(return_value=mock_queue),
            mock_dispatcher_cls=mock_disp_cls,
            mock_mirror_cls=MagicMock(),
            mock_governance_cls=MagicMock(),
        )
        inject_modules(mods)

        mock_svc = _make_mock_service()
        mock_svc.run_governance_check.return_value = {
            "approved": False,
            "violations": [
                {
                    "rule": "root-workspace",
                    "severity": "hard-block",
                    "message": "Cannot dispatch to workspace root",
                }
            ],
        }

        from backend.services.overlord_service import OverlordService

        result = OverlordService.dispatch_from_chat(mock_svc, request)

        assert result["status"] == "failed"
        assert "Governance" in result["reason"]
        assert result.get("violations")
        # Dispatcher should NOT have been instantiated
        mock_disp_cls.assert_not_called()

    def test_fallback_to_legacy_when_imports_fail(self):
        """If Dispatcher imports fail, should fall back to execute_task."""
        # Setting sys.modules[key] = None causes Python to raise ImportError
        # on subsequent imports, even if the package is installed.
        blocked_keys = [
            "nebulus_swarm.overlord.dispatcher",
            "nebulus_swarm.overlord.work_queue",
            "nebulus_swarm.overlord.mirrors",
            "nebulus_swarm.overlord.governance",
        ]
        removed = {}
        for key in blocked_keys:
            if key in sys.modules:
                removed[key] = sys.modules[key]
            sys.modules[key] = None  # blocks import

        try:
            request = DispatchRequest(user_message="build something")
            mock_svc = _make_mock_service()
            mock_svc.execute_task.return_value = {
                "status": "success",
                "steps": [],
                "reason": "Legacy fallback",
            }

            from backend.services.overlord_service import OverlordService

            result = OverlordService.dispatch_from_chat(mock_svc, request)

            assert result["status"] == "success"
            assert result["reason"] == "Legacy fallback"
            mock_svc.execute_task.assert_called_once_with(
                request.user_message, auto_approve=False
            )
        finally:
            for key in blocked_keys:
                if key in removed:
                    sys.modules[key] = removed[key]
                else:
                    sys.modules.pop(key, None)

    def test_token_budget_passthrough(self, inject_modules):
        """Token budget from DispatchRequest.context should flow to work queue."""
        request = DispatchRequest(
            user_message="refactor the auth module in nebulus-core",
            context=DispatchContext(
                active_project="nebulus-core",
                token_budget=75000,
            ),
        )

        mock_queue = MagicMock()
        mock_queue.add_task.return_value = "test-task-id-003"
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_task.return_value = FakeDispatchResultRecord(
            task_id="test-task-id-003"
        )

        mods = _setup_mock_modules(
            mock_queue_cls=MagicMock(return_value=mock_queue),
            mock_dispatcher_cls=MagicMock(return_value=mock_dispatcher),
            mock_mirror_cls=MagicMock(),
            mock_governance_cls=MagicMock(),
        )
        inject_modules(mods)

        mock_svc = _make_mock_service()

        from backend.services.overlord_service import OverlordService

        OverlordService.dispatch_from_chat(mock_svc, request)

        _, kwargs = mock_queue.add_task.call_args
        assert kwargs.get("token_budget") == 75000

    def test_project_inferred_from_context(self, inject_modules):
        """Project should be extracted from request.context.active_project."""
        request = DispatchRequest(
            user_message="fix the bug",
            context=DispatchContext(active_project="nebulus-gantry"),
        )

        mock_queue = MagicMock()
        mock_queue.add_task.return_value = "test-task-id-004"
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_task.return_value = FakeDispatchResultRecord(
            task_id="test-task-id-004"
        )

        mods = _setup_mock_modules(
            mock_queue_cls=MagicMock(return_value=mock_queue),
            mock_dispatcher_cls=MagicMock(return_value=mock_dispatcher),
            mock_mirror_cls=MagicMock(),
            mock_governance_cls=MagicMock(),
        )
        inject_modules(mods)

        mock_svc = _make_mock_service()

        from backend.services.overlord_service import OverlordService

        OverlordService.dispatch_from_chat(mock_svc, request)

        _, kwargs = mock_queue.add_task.call_args
        assert kwargs["project"] == "nebulus-gantry"

    def test_dispatch_failure_returns_error_dict(self, inject_modules):
        """If Dispatcher.dispatch_task raises, return failure dict."""
        request = DispatchRequest(
            user_message="build auth feature for nebulus-core",
            context=DispatchContext(active_project="nebulus-core"),
        )

        mock_queue = MagicMock()
        mock_queue.add_task.return_value = "test-task-id-005"
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_task.side_effect = RuntimeError(
            "No workers available"
        )

        mods = _setup_mock_modules(
            mock_queue_cls=MagicMock(return_value=mock_queue),
            mock_dispatcher_cls=MagicMock(return_value=mock_dispatcher),
            mock_mirror_cls=MagicMock(),
            mock_governance_cls=MagicMock(),
        )
        inject_modules(mods)

        mock_svc = _make_mock_service()

        from backend.services.overlord_service import OverlordService

        result = OverlordService.dispatch_from_chat(mock_svc, request)

        assert result["status"] == "failed"
        assert "No workers available" in result["reason"]

    def test_role_passed_to_dispatcher(self, inject_modules):
        """The role from DispatchRequest should be passed to dispatch_task."""
        request = DispatchRequest(
            user_message="plan the next sprint for nebulus-core",
            context=DispatchContext(active_project="nebulus-core"),
            role="pm",
        )

        mock_queue = MagicMock()
        mock_queue.add_task.return_value = "test-task-id-006"
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_task.return_value = FakeDispatchResultRecord(
            task_id="test-task-id-006"
        )

        mods = _setup_mock_modules(
            mock_queue_cls=MagicMock(return_value=mock_queue),
            mock_dispatcher_cls=MagicMock(return_value=mock_dispatcher),
            mock_mirror_cls=MagicMock(),
            mock_governance_cls=MagicMock(),
        )
        inject_modules(mods)

        mock_svc = _make_mock_service()

        from backend.services.overlord_service import OverlordService

        OverlordService.dispatch_from_chat(mock_svc, request)

        mock_dispatcher.dispatch_task.assert_called_once_with(
            "test-task-id-006", role="pm"
        )
