"""Pydantic schemas for the Agent Dispatch Protocol.

Defines the standardized request/response format between Gantry's chat
interface and Overlord's dispatch layer. Used by the conversation router
to communicate with the frontend via Server-Sent Events.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ── Request ──────────────────────────────────────────────────────────────────


class DispatchContext(BaseModel):
    """Contextual metadata for routing decisions."""

    active_project: str | None = None
    trust_level: str = "standard"  # minimal | cautious | standard | elevated | full
    token_budget: int = 50000


class DispatchRequest(BaseModel):
    """Incoming message from the Gantry chat interface."""

    user_message: str
    conversation_history: list[dict] = Field(default_factory=list)
    context: DispatchContext = Field(default_factory=DispatchContext)
    role: str = "default"  # "default" | "pm"


# ── Response (SSE stream events) ─────────────────────────────────────────────


class DispatchEvent(BaseModel):
    """A single event in the dispatch response stream.

    Sent to the frontend via Server-Sent Events. The ``type`` field
    determines how the frontend renders the event.
    """

    type: str  # "thinking" | "content" | "action" | "result" | "status" | "approval_request" | "error"
    source: str = "overlord"  # "overlord" | "claude" | "gemini" | "local"
    content: str = ""
    metadata: dict = Field(default_factory=dict)

    def to_sse(self) -> str:
        """Serialize as an SSE data line."""
        import json

        payload = self.model_dump()
        return f"data: {json.dumps(payload)}\n\n"


# ── Convenience constructors ─────────────────────────────────────────────────


def content_event(text: str, source: str = "local") -> DispatchEvent:
    """Create a content chunk event (streaming LLM tokens)."""
    return DispatchEvent(type="content", source=source, content=text)


def thinking_event(text: str, source: str = "overlord") -> DispatchEvent:
    """Create a thinking/routing event."""
    return DispatchEvent(type="thinking", source=source, content=text)


def status_event(text: str, **meta) -> DispatchEvent:
    """Create a status update event."""
    return DispatchEvent(type="status", source="overlord", content=text, metadata=meta)


def error_event(message: str, **meta) -> DispatchEvent:
    """Create an error event."""
    return DispatchEvent(type="error", source="overlord", content=message, metadata=meta)


def result_event(text: str, source: str = "overlord", **meta) -> DispatchEvent:
    """Create a final result event with metadata."""
    return DispatchEvent(type="result", source=source, content=text, metadata=meta)
