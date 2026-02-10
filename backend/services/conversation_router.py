"""Conversation router — intent classification and worker routing.

Sits between the chat endpoint and the dispatch engine. Classifies user
intent, selects the appropriate worker, and assembles streaming responses
as DispatchEvent objects.
"""
from __future__ import annotations

import json
import logging
import re
from typing import AsyncGenerator

import httpx

from backend.platform import get_llm_base_url
from backend.schemas.dispatch import (
    DispatchEvent,
    DispatchRequest,
    content_event,
    error_event,
    result_event,
    status_event,
    thinking_event,
)

logger = logging.getLogger(__name__)


# ── Intent Classification ────────────────────────────────────────────────────

# Pattern-based intent classification (no LLM call needed for obvious cases)
_STATUS_PATTERNS = re.compile(
    r"\b(what.?s running|show status|active agents?|overlord status|show dispatches?)\b",
    re.IGNORECASE,
)
_HALT_PATTERNS = re.compile(
    r"\b(stop everything|halt|kill all|emergency stop|abort)\b",
    re.IGNORECASE,
)
_DISPATCH_PATTERNS = re.compile(
    r"\b(build|implement|create|deploy|run tests?|refactor|fix bug|add feature)\b.*\b(for|in|on|to)\b",
    re.IGNORECASE,
)


class Intent:
    """Classified user intent."""

    QUESTION = "question"
    STATUS_QUERY = "status_query"
    DISPATCH_COMMAND = "dispatch_command"
    HALT_COMMAND = "halt_command"


def classify_intent(message: str) -> str:
    """Classify the user's message into an intent category.

    Uses pattern matching for obvious commands, defaults to QUESTION
    for everything else (fast path to LLM).

    Args:
        message: The raw user message text.

    Returns:
        One of the Intent constants.
    """
    text = message.strip()
    if _HALT_PATTERNS.search(text):
        return Intent.HALT_COMMAND
    if _STATUS_PATTERNS.search(text):
        return Intent.STATUS_QUERY
    if _DISPATCH_PATTERNS.search(text):
        return Intent.DISPATCH_COMMAND
    return Intent.QUESTION


# ── Worker Selection ─────────────────────────────────────────────────────────


def select_worker_for_question(message: str, role: str = "default") -> str:
    """Select the best worker for a question based on content heuristics.

    Args:
        message: The user message.
        role: "pm" routes to strategy-oriented workers.

    Returns:
        Worker identifier: "claude", "gemini", or "local".
    """
    lower = message.lower()

    # PM role biases toward Gemini for strategy
    if role == "pm":
        return "gemini"

    # Code-related keywords → Claude
    code_keywords = [
        "code", "function", "class", "error", "bug", "implement",
        "refactor", "debug", "test", "import", "module", "api",
        "traceback", "exception", "syntax",
    ]
    if any(kw in lower for kw in code_keywords):
        return "claude"

    # Planning/strategy keywords → Gemini
    strategy_keywords = [
        "plan", "prioritize", "strategy", "roadmap", "architecture",
        "design", "trade-off", "tradeoff", "compare", "evaluate",
        "decision", "next steps",
    ]
    if any(kw in lower for kw in strategy_keywords):
        return "gemini"

    # Default: local LLM (fastest, cheapest)
    return "local"


# ── Conversation Router ──────────────────────────────────────────────────────


class ConversationRouter:
    """Routes chat messages through Overlord's dispatch layer.

    Handles intent classification, worker selection, governance checks,
    and streaming response assembly.
    """

    def __init__(self) -> None:
        self._llm_base_url = get_llm_base_url()

    async def route_message(
        self, request: DispatchRequest
    ) -> AsyncGenerator[DispatchEvent, None]:
        """Route a user message and yield DispatchEvent objects.

        This is the main entry point for the dispatch endpoint.

        Args:
            request: The incoming dispatch request.

        Yields:
            DispatchEvent objects for the SSE stream.
        """
        intent = classify_intent(request.user_message)

        yield thinking_event(f"Intent: {intent}")

        if intent == Intent.HALT_COMMAND:
            async for event in self._handle_halt():
                yield event
        elif intent == Intent.STATUS_QUERY:
            async for event in self._handle_status():
                yield event
        elif intent == Intent.DISPATCH_COMMAND:
            async for event in self._handle_dispatch(request):
                yield event
        else:
            async for event in self._handle_question(request):
                yield event

    async def _handle_question(  # noqa: C901
        self, request: DispatchRequest
    ) -> AsyncGenerator[DispatchEvent, None]:
        """Route a question to the best available LLM worker.

        Streams tokens back as content events.
        """
        worker = select_worker_for_question(
            request.user_message, request.role
        )
        yield thinking_event(f"Routing to {worker} worker")

        # Build messages for the LLM
        messages = []

        # Add system prompt
        system_content = (
            "You are Nebulus Overlord, the AI orchestrator for the Nebulus ecosystem."
        )
        if request.role == "pm":
            system_content += (
                "\n\nYou are operating in Project Manager mode. "
                "Prioritize: sequencing, dependency analysis, risk assessment, "
                "business alignment. "
                "Deprioritize: code generation, implementation details."
            )
        messages.append({"role": "system", "content": system_content})

        # Add conversation history
        for msg in request.conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add current message
        messages.append({"role": "user", "content": request.user_message})

        # Stream from LLM
        tokens_used = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._llm_base_url}/v1/chat/completions",
                    json={
                        "model": "default",
                        "messages": messages,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                # Track usage
                                if "usage" in chunk and chunk["usage"]:
                                    tokens_used = chunk["usage"].get(
                                        "total_tokens", 0
                                    )
                                delta = (
                                    chunk.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content")
                                )
                                if delta:
                                    yield content_event(delta, source=worker)
                            except json.JSONDecodeError:
                                continue
            except httpx.HTTPStatusError as e:
                yield error_event(
                    f"LLM service returned {e.response.status_code}"
                )
                return
            except httpx.ConnectError:
                yield error_event(
                    "Could not connect to LLM service. Is it running?"
                )
                return
            except Exception as e:
                yield error_event(str(e))
                return

        # Final result event with metadata
        yield result_event(
            "",
            source=worker,
            tokens_used=tokens_used,
            worker=worker,
            intent=Intent.QUESTION,
        )

    async def _handle_status(
        self,
    ) -> AsyncGenerator[DispatchEvent, None]:
        """Handle a status query by returning Overlord state."""
        try:
            from backend.services.overlord_service import get_overlord_service

            svc = get_overlord_service()
            dashboard = svc.get_dashboard()

            # Format a human-readable status
            lines = ["**Ecosystem Status**\n"]
            for proj in dashboard.get("projects", []):
                name = proj.get("name", "?")
                branch = proj.get("git", {}).get("branch", "?")
                clean = (
                    "clean" if proj.get("git", {}).get("clean", True) else "dirty"
                )
                issues = proj.get("issues", [])
                status_icon = "+" if not issues else "!"
                lines.append(f"  {status_icon} **{name}** ({branch}, {clean})")
                for issue in issues[:2]:
                    lines.append(f"    - {issue}")

            daemon = dashboard.get("daemon", {})
            if daemon.get("running"):
                lines.append(f"\nDaemon: running (PID {daemon.get('pid')})")
            else:
                lines.append("\nDaemon: not running")

            yield content_event("\n".join(lines), source="overlord")
            yield result_event("", source="overlord", intent=Intent.STATUS_QUERY)

        except Exception as e:
            logger.warning("Overlord status unavailable: %s", e)
            yield error_event(f"Overlord unavailable: {e}")

    async def _handle_halt(self) -> AsyncGenerator[DispatchEvent, None]:
        """Handle a halt command — emergency stop all dispatches."""
        try:
            from backend.services.overlord_service import get_overlord_service

            svc = get_overlord_service()
            halt_result = svc.halt_all()
            msg = halt_result.get("message", "Halt executed")
            yield status_event(msg)
            yield result_event(msg, source="overlord", intent=Intent.HALT_COMMAND)
        except Exception as e:
            logger.warning("Halt failed: %s", e)
            yield error_event(f"Halt failed: {e}")

    async def _handle_dispatch(
        self, request: DispatchRequest
    ) -> AsyncGenerator[DispatchEvent, None]:
        """Handle a dispatch command via the real Dispatcher with governance."""
        try:
            from backend.services.overlord_service import get_overlord_service

            svc = get_overlord_service()

            # Run governance check before dispatch
            yield thinking_event("Running governance checks...")
            project = (
                request.context.active_project if request.context else None
            )
            gov = svc.run_governance_check(request.user_message, project)
            if not gov.get("approved", True):
                violations = gov.get("violations", [])
                msg = violations[0]["message"] if violations else "Blocked by governance"
                yield error_event(f"Governance: {msg}")
                return

            yield thinking_event("Dispatching through work queue...")

            # Route through the real Dispatcher via dispatch_from_chat
            result = svc.dispatch_from_chat(request)

            status = result.get("status", "unknown")
            reason = result.get("reason", "")
            task_id = result.get("task_id", "")

            if status == "failed":
                yield error_event(reason or "Dispatch failed")
                return

            yield result_event(
                reason or f"Dispatch {status} (task {task_id[:8]})",
                source="overlord",
                status=status,
                task_id=task_id,
                intent=Intent.DISPATCH_COMMAND,
            )

        except Exception as e:
            logger.warning("Dispatch failed: %s", e)
            yield error_event(f"Dispatch failed: {e}")


# ── Module-level singleton ───────────────────────────────────────────────────

_router_instance: ConversationRouter | None = None


def get_conversation_router() -> ConversationRouter:
    """Get or create the singleton ConversationRouter."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ConversationRouter()
    return _router_instance


def reset_conversation_router() -> None:
    """Reset the singleton (for testing)."""
    global _router_instance
    _router_instance = None
