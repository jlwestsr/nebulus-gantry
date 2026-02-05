import json
import httpx
from typing import AsyncGenerator

from backend.config import Settings


class LLMService:
    def __init__(self):
        self.settings = Settings()
        self.base_url = self.settings.tabby_host
        self.last_usage: dict | None = None

    async def stream_chat(
        self,
        messages: list[dict],
        model: str = "default",
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion from TabbyAPI (OpenAI-compatible).
        Yields chunks of the assistant's response.

        After iteration completes, self.last_usage contains token usage
        data if the API provided it (prompt_tokens, completion_tokens,
        total_tokens).
        """
        self.last_usage = None
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": model,
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
                yield "[Error: Could not connect to LLM service. Is TabbyAPI running?]"
            except Exception as e:
                yield f"[Error: {str(e)}]"

    async def chat(self, messages: list[dict], model: str = "default") -> str:
        """
        Non-streaming chat completion. Returns full response.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[Error: {str(e)}]"
