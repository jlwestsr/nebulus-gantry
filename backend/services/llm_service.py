import json
import os
import httpx
from typing import AsyncGenerator

from backend.platform import get_llm_base_url, get_default_model


def _get_llm_headers() -> dict:
    """Build auth headers for LLM API if NEBULUS_LLM_API_KEY is set."""
    api_key = os.getenv("NEBULUS_LLM_API_KEY")
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}


class LLMService:
    """OpenAI-compatible LLM client for streaming and non-streaming chat.

    CONCURRENCY NOTE: This class stores per-call state in self.last_usage.
    It is safe ONLY because callers instantiate a new LLMService() per
    request (see chat.py send_message / dispatch_message).  Do NOT convert
    this to a singleton or shared dependency without first removing the
    mutable instance state.
    """

    def __init__(self):
        self.base_url = get_llm_base_url()
        self.headers = _get_llm_headers()
        self.last_usage: dict | None = None

    async def stream_chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from the LLM inference server (OpenAI-compatible).

        Yields chunks of the assistant's response.

        Args:
            messages: List of message dicts with role and content.
            model: Model ID to use (default: "default").
            temperature: Optional temperature override (0.0-2.0).

        After iteration completes, self.last_usage contains token usage
        data if the API provided it (prompt_tokens, completion_tokens,
        total_tokens).
        """
        self.last_usage = None
        request_body = {
            "model": model or get_default_model(),
            "messages": messages,
            "stream": True,
        }
        if temperature is not None:
            request_body["temperature"] = temperature

        async with httpx.AsyncClient(timeout=60.0, headers=self.headers) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    json=request_body,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                # Capture usage if present (typically in last chunk)
                                if "usage" in chunk and chunk["usage"]:
                                    self.last_usage = chunk["usage"]
                                if content := chunk.get("choices", [{}])[0].get("delta", {}).get("content"):
                                    yield content
                            except json.JSONDecodeError:
                                continue
            except httpx.HTTPStatusError as e:
                yield f"[Error: LLM service returned {e.response.status_code}]"
            except httpx.ConnectError:
                yield "[Error: Could not connect to LLM service. Is the LLM service running?]"
            except Exception as e:
                yield f"[Error: {str(e)}]"

    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        """
        Non-streaming chat completion. Returns full response.
        """
        async with httpx.AsyncClient(timeout=60.0, headers=self.headers) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": model or get_default_model(),
                        "messages": messages,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[Error: {str(e)}]"
