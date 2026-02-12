"""Tests for the Agent Dispatch Protocol schemas."""
import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from backend.schemas.dispatch import (  # noqa: E402
    DispatchContext,
    DispatchEvent,
    DispatchRequest,
    content_event,
    error_event,
    result_event,
    status_event,
    thinking_event,
)


# ── DispatchContext ───────────────────────────────────────────────────────────


def test_dispatch_context_defaults():
    ctx = DispatchContext()
    assert ctx.active_project is None
    assert ctx.trust_level == "standard"
    assert ctx.token_budget == 50000


def test_dispatch_context_custom():
    ctx = DispatchContext(
        active_project="nebulus-core",
        trust_level="elevated",
        token_budget=100000,
    )
    assert ctx.active_project == "nebulus-core"
    assert ctx.trust_level == "elevated"
    assert ctx.token_budget == 100000


# ── DispatchRequest ──────────────────────────────────────────────────────────


def test_dispatch_request_minimal():
    req = DispatchRequest(user_message="hello")
    assert req.user_message == "hello"
    assert req.conversation_history == []
    assert req.role == "default"
    assert req.context.trust_level == "standard"


def test_dispatch_request_with_history():
    req = DispatchRequest(
        user_message="what next?",
        conversation_history=[
            {"role": "user", "content": "start"},
            {"role": "assistant", "content": "ok"},
        ],
        role="pm",
    )
    assert len(req.conversation_history) == 2
    assert req.role == "pm"


def test_dispatch_request_serialization():
    req = DispatchRequest(user_message="test")
    data = req.model_dump()
    assert data["user_message"] == "test"
    assert "context" in data
    assert data["context"]["trust_level"] == "standard"

    # Round-trip
    req2 = DispatchRequest.model_validate(data)
    assert req2.user_message == "test"


# ── DispatchEvent ────────────────────────────────────────────────────────────


def test_dispatch_event_defaults():
    event = DispatchEvent(type="content")
    assert event.source == "overlord"
    assert event.content == ""
    assert event.metadata == {}


def test_dispatch_event_to_sse():
    event = DispatchEvent(type="content", source="claude", content="hello")
    sse = event.to_sse()
    assert sse.startswith("data: ")
    assert sse.endswith("\n\n")

    # Parse the JSON payload
    payload = json.loads(sse[6:].strip())
    assert payload["type"] == "content"
    assert payload["source"] == "claude"
    assert payload["content"] == "hello"


def test_dispatch_event_to_sse_with_metadata():
    event = DispatchEvent(
        type="result",
        source="local",
        content="done",
        metadata={"tokens_used": 150},
    )
    sse = event.to_sse()
    payload = json.loads(sse[6:].strip())
    assert payload["metadata"]["tokens_used"] == 150


# ── Convenience constructors ─────────────────────────────────────────────────


def test_content_event():
    event = content_event("hello", source="claude")
    assert event.type == "content"
    assert event.source == "claude"
    assert event.content == "hello"


def test_content_event_default_source():
    event = content_event("hi")
    assert event.source == "local"


def test_thinking_event():
    event = thinking_event("routing...")
    assert event.type == "thinking"
    assert event.source == "overlord"


def test_status_event():
    event = status_event("plan ready", step_count=3)
    assert event.type == "status"
    assert event.metadata["step_count"] == 3


def test_error_event():
    event = error_event("something broke", code=500)
    assert event.type == "error"
    assert event.content == "something broke"
    assert event.metadata["code"] == 500


def test_result_event():
    event = result_event("success", source="claude", tokens_used=100)
    assert event.type == "result"
    assert event.source == "claude"
    assert event.metadata["tokens_used"] == 100
