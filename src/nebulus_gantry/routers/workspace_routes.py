from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from openai import AsyncOpenAI
import httpx
from nebulus_gantry.services.mcp_client import get_mcp_client

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

# Configure Ollama client (Shared config, arguably should be central)
# Using the same config as main.py
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11435")
client = AsyncOpenAI(
    base_url=OLLAMA_HOST + "/v1",
    api_key="ollama",
)


# --- Models ---


@router.get("/models")
async def list_models():
    """List available models from Ollama with detailed metadata."""
    try:
        # Candidate hosts to try (Configured, Localhost mapped, Internal Docker)
        hosts = [
            OLLAMA_HOST,
            "http://localhost:11435",
            "http://127.0.0.1:11435",
            "http://ollama:11434",
            "http://host.docker.internal:11434",
            "http://host.docker.internal:11435"
        ]
        # Remove duplicates while preserving order
        unique_hosts = []
        [unique_hosts.append(h) for h in hosts if h not in unique_hosts]

        async with httpx.AsyncClient(timeout=3.0) as http_client:
            last_error = None
            for host in unique_hosts:
                try:
                    # Clean host string
                    host = host.rstrip("/")
                    resp = await http_client.get(f"{host}/api/tags")

                    if resp.status_code == 200:
                        data = resp.json()
                        return JSONResponse(content=data)
                    else:
                        last_error = f"Error {resp.status_code} from {host}"
                except Exception as e:
                    last_error = f"Failed to connect to {host}: {str(e)}"
                    continue
            # If we get here, all failed
            return JSONResponse(
                content={"error": f"Could not connect to Ollama. Last error: {last_error}", "tried": unique_hosts},
                status_code=500,
            )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


class PullModelRequest(BaseModel):
    name: str


@router.post("/models/pull")
async def pull_model(request: PullModelRequest):
    """Trigger a model pull via Ollama API."""
    try:
        # We need to hit Ollama's /api/pull endpoint directly
        # OpenAI SDK might not expose pull granularly
        # We trigger it via httpx

        req = httpx.post(
            f"{OLLAMA_HOST}/api/pull",
            json={"name": request.name, "stream": False},
            timeout=None,
        )

        if req.status_code == 200:
            return {
                "status": "success",
                "message": f"Model {request.name} pulled successfully",
            }
        else:
            return JSONResponse(
                content={"error": req.text}, status_code=req.status_code
            )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.delete("/models/{name}")
async def delete_model(name: str):
    """Delete a model via Ollama API."""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.delete(
                f"{OLLAMA_HOST}/api/delete", json={"name": name}
            )
            if resp.status_code == 200:
                return {"status": "success"}
            else:
                return JSONResponse(
                    content={"error": resp.text}, status_code=resp.status_code
                )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# --- Tools ---

# In-memory mock persistence for MVP
DISABLED_TOOLS = set()


@router.get("/tools")
async def list_tools():
    """List available MCP tools from the server."""
    try:
        mcp = get_mcp_client()
        try:
            # list_tools returns list of dicts: {"type": "function", "function": {...}}
            tools_payload = await mcp.list_tools()
        except Exception:
            # If MCP is down, return empty or cached
            return {"tools": [], "error": "MCP Server unavailable"}

        # Transform for UI
        ui_tools = []
        for t in tools_payload:
            fn = t.get("function", {})
            name = fn.get("name")
            if name:
                ui_tools.append({
                    "name": name,
                    "description": fn.get("description", "No description"),
                    "enabled": name not in DISABLED_TOOLS
                })

        return {"tools": ui_tools}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


class ToggleToolRequest(BaseModel):
    name: str
    enabled: bool


@router.post("/tools/toggle")
async def toggle_tool(request: ToggleToolRequest):
    """Toggle a tool."""
    if request.enabled:
        DISABLED_TOOLS.discard(request.name)
    else:
        DISABLED_TOOLS.add(request.name)

    return {"status": "success", "tool": request.name, "enabled": request.enabled}


# --- Knowledge ---


@router.get("/knowledge")
async def list_knowledge():
    """List RAG collections."""
    # Placeholder for ChromaDB connection
    return {
        "collections": [
            {"name": "default", "count": 142, "status": "ready"},
            {"name": "project_docs", "count": 45, "status": "indexing"},
        ]
    }
