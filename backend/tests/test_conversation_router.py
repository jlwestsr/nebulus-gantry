"""Tests for the conversation router — intent classification and worker selection."""
import os
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402

from backend.services.conversation_router import (  # noqa: E402
    Intent,
    classify_intent,
    select_worker_for_question,
    ConversationRouter,
    reset_conversation_router,
)
from backend.schemas.dispatch import DispatchRequest  # noqa: E402


# ── Intent Classification ────────────────────────────────────────────────────


class TestClassifyIntent:
    def test_halt_stop_everything(self):
        assert classify_intent("stop everything") == Intent.HALT_COMMAND

    def test_halt_emergency(self):
        assert classify_intent("emergency stop now!") == Intent.HALT_COMMAND

    def test_halt_kill_all(self):
        assert classify_intent("kill all agents") == Intent.HALT_COMMAND

    def test_halt_abort(self):
        assert classify_intent("abort") == Intent.HALT_COMMAND

    def test_status_whats_running(self):
        assert classify_intent("what's running?") == Intent.STATUS_QUERY

    def test_status_show_status(self):
        assert classify_intent("show status") == Intent.STATUS_QUERY

    def test_status_active_agents(self):
        assert classify_intent("active agents") == Intent.STATUS_QUERY

    def test_status_overlord_status(self):
        assert classify_intent("overlord status") == Intent.STATUS_QUERY

    def test_dispatch_build_feature(self):
        assert classify_intent("build the auth feature for nebulus-core") == Intent.DISPATCH_COMMAND

    def test_dispatch_run_tests(self):
        assert classify_intent("run tests on nebulus-atom") == Intent.DISPATCH_COMMAND

    def test_dispatch_refactor(self):
        assert classify_intent("refactor the router in gantry") == Intent.DISPATCH_COMMAND

    def test_question_simple(self):
        assert classify_intent("explain how the LLM service works") == Intent.QUESTION

    def test_question_default(self):
        assert classify_intent("hello world") == Intent.QUESTION

    def test_question_complex(self):
        assert classify_intent("what is the architecture of this project?") == Intent.QUESTION

    def test_halt_takes_priority(self):
        """Halt should take priority over other patterns."""
        assert classify_intent("halt all builds for the project") == Intent.HALT_COMMAND

    def test_whitespace_stripped(self):
        assert classify_intent("  show status  ") == Intent.STATUS_QUERY


# ── Worker Selection ─────────────────────────────────────────────────────────


class TestSelectWorker:
    def test_pm_role_routes_to_gemini(self):
        assert select_worker_for_question("anything", role="pm") == "gemini"

    def test_code_keywords_route_to_claude(self):
        assert select_worker_for_question("explain this function") == "claude"
        assert select_worker_for_question("fix the bug in module X") == "claude"
        assert select_worker_for_question("debug the traceback") == "claude"

    def test_strategy_keywords_route_to_gemini(self):
        assert select_worker_for_question("what's our roadmap?") == "gemini"
        assert select_worker_for_question("help me plan the next sprint") == "gemini"
        assert select_worker_for_question("evaluate the architecture") == "gemini"

    def test_default_routes_to_local(self):
        assert select_worker_for_question("hello") == "local"
        assert select_worker_for_question("tell me a joke") == "local"

    def test_case_insensitive(self):
        assert select_worker_for_question("What is this API endpoint?") == "claude"
        assert select_worker_for_question("PLAN the next release") == "gemini"


# ── ConversationRouter ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_router():
    reset_conversation_router()
    yield
    reset_conversation_router()


class TestConversationRouterQuestion:
    @pytest.mark.asyncio
    async def test_question_streams_content_events(self):
        """Questions should emit thinking + content + result events."""
        router = ConversationRouter()
        request = DispatchRequest(user_message="hello world")

        # Mock httpx to return a fake streaming response
        mock_lines = [
            'data: {"choices":[{"delta":{"content":"Hi"}}]}',
            'data: {"choices":[{"delta":{"content":" there"}}]}',
            'data: [DONE]',
        ]

        # Build the mock chain: AsyncClient() -> ctx mgr -> client.stream() -> ctx mgr -> response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = MagicMock(return_value=_async_iter(mock_lines))

        stream_ctx = AsyncMock()
        stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=stream_ctx)

        client_ctx = AsyncMock()
        client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.services.conversation_router.httpx.AsyncClient",
            return_value=client_ctx,
        ):
            events = []
            async for event in router.route_message(request):
                events.append(event)

        # Should have: thinking (intent), thinking (routing), content x2, result
        types = [e.type for e in events]
        assert "thinking" in types
        assert "content" in types
        assert "result" in types

        # Content events should contain the streamed text
        content_parts = [e.content for e in events if e.type == "content"]
        assert "Hi" in content_parts
        assert " there" in content_parts

    @pytest.mark.asyncio
    async def test_question_connect_error(self):
        """Connection errors should yield an error event."""
        import httpx

        router = ConversationRouter()
        request = DispatchRequest(user_message="hello")

        # client.stream() context manager raises ConnectError on __aenter__
        stream_ctx = AsyncMock()
        stream_ctx.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("refused"))
        stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=stream_ctx)

        client_ctx = AsyncMock()
        client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "backend.services.conversation_router.httpx.AsyncClient",
            return_value=client_ctx,
        ):
            events = []
            async for event in router.route_message(request):
                events.append(event)

        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) >= 1
        assert "connect" in error_events[0].content.lower() or "LLM" in error_events[0].content


class TestConversationRouterStatus:
    @pytest.mark.asyncio
    async def test_status_query_returns_dashboard(self):
        """Status queries should call get_dashboard and return formatted text."""
        router = ConversationRouter()
        request = DispatchRequest(user_message="show status")

        mock_svc = MagicMock()
        mock_svc.get_dashboard.return_value = {
            "projects": [
                {"name": "nebulus-core", "git": {"branch": "develop", "clean": True}, "issues": []},
            ],
            "daemon": {"running": False, "pid": None},
        }

        with patch(
            "backend.services.overlord_service.get_overlord_service",
            return_value=mock_svc,
        ):
            events = []
            async for event in router.route_message(request):
                events.append(event)

        content_events = [e for e in events if e.type == "content"]
        assert len(content_events) >= 1
        assert "nebulus-core" in content_events[0].content

    @pytest.mark.asyncio
    async def test_status_query_overlord_unavailable(self):
        """When Overlord is unavailable, status should return error event."""
        router = ConversationRouter()
        request = DispatchRequest(user_message="what's running?")

        with patch(
            "backend.services.overlord_service.get_overlord_service",
            side_effect=RuntimeError("not available"),
        ):
            events = []
            async for event in router.route_message(request):
                events.append(event)

        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) >= 1


class TestConversationRouterHalt:
    @pytest.mark.asyncio
    async def test_halt_command(self):
        """Halt should call halt_all and return status event."""
        router = ConversationRouter()
        request = DispatchRequest(user_message="stop everything")

        mock_svc = MagicMock()
        mock_svc.halt_all.return_value = {
            "message": "Halted: 2 task(s) cancelled, daemon stopped",
            "tasks_cancelled": 2,
            "daemon_stopped": True,
        }

        with patch(
            "backend.services.overlord_service.get_overlord_service",
            return_value=mock_svc,
        ):
            events = []
            async for event in router.route_message(request):
                events.append(event)

        status_events = [e for e in events if e.type == "status"]
        assert len(status_events) >= 1
        assert "Halted" in status_events[0].content


class TestConversationRouterDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_command_runs_governance_and_dispatches(self):
        """Dispatch commands should run governance then call dispatch_from_chat."""
        router = ConversationRouter()
        request = DispatchRequest(
            user_message="build auth feature for nebulus-core"
        )

        mock_svc = MagicMock()
        mock_svc.run_governance_check.return_value = {
            "approved": True,
            "violations": [],
        }
        mock_svc.dispatch_from_chat.return_value = {
            "status": "completed",
            "task_id": "abc12345-0000-0000-0000-000000000000",
            "worker": "claude",
            "model": "opus",
            "tokens_used": 1500,
            "review_status": "passed",
            "output": "Done",
            "reason": "",
        }

        with patch(
            "backend.services.overlord_service.get_overlord_service",
            return_value=mock_svc,
        ):
            events = []
            async for event in router.route_message(request):
                events.append(event)

        # Should have called governance and dispatch_from_chat
        mock_svc.run_governance_check.assert_called_once()
        mock_svc.dispatch_from_chat.assert_called_once_with(request)

        result_events = [e for e in events if e.type == "result"]
        assert len(result_events) >= 1

    @pytest.mark.asyncio
    async def test_dispatch_governance_rejection(self):
        """When governance rejects, should yield error event and NOT dispatch."""
        router = ConversationRouter()
        request = DispatchRequest(
            user_message="deploy feature to production"
        )

        mock_svc = MagicMock()
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

        with patch(
            "backend.services.overlord_service.get_overlord_service",
            return_value=mock_svc,
        ):
            events = []
            async for event in router.route_message(request):
                events.append(event)

        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) >= 1
        assert "Governance" in error_events[0].content

        # dispatch_from_chat should NOT have been called
        mock_svc.dispatch_from_chat.assert_not_called()


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _async_iter(items):
    for item in items:
        yield item
