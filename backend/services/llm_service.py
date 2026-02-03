import httpx
from typing import AsyncGenerator

from backend.config import Settings


class LLMService:
    def __init__(self):
        self.settings = Settings()
        self.base_url = self.settings.tabby_host

    async def stream_chat(
        self,
        messages: list[dict],
        model: str = "default",
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion from TabbyAPI (OpenAI-compatible).
        Yields chunks of the assistant's response.
        """
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
                                import json
                                chunk = json.loads(data)
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
