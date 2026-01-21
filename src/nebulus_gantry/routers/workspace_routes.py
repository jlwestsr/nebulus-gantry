from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from openai import AsyncOpenAI
import httpx

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


@router.get("/tools")
async def list_tools():
    """List enabled/available MCP tools (Mock for now or introspect MCP)."""
    # Since MCP is internal to the server process (FastMCP), we might need to expose them.
    # We can inspect the 'mcp' object if we import it, or just use a static list for MVP.
    # The MCP definitions are in mcp_server/server.py.
    # We are in Gantry (FastAPI). MCP is running in a different container or process?
    # Based on CONTEXT.md, Gantry and MCP are separate.
    # Actually, main.py imports 'mcp_server' modules? No.
    # Gantry and MCP Server seem to be distinct in docker-compose usually.
    # Let's check docker-compose.yml to be sure.
    # Assuming they are separate, we can't easily list tools from Gantry unless MCP exposes an API.

    # Wait, the mcp_server/server.py exposes an SSE app.
    # Gantry is the UI.
    # We might need to mock this for the "Workspace" UI feature for now
    # OR assume we are managing the config that the MCP server READS.

    # Let's return a mock list for the MVP UI structure.
    tools = [
        {
            "name": "web_search",
            "enabled": True,
            "description": "Search the web via DDG",
        },
        {
            "name": "read_file",
            "enabled": True,
            "description": "Read file from workspace",
        },
        {
            "name": "run_command",
            "enabled": False,
            "description": "Execute shell commands",
        },
    ]
    return {"tools": tools}


class ToggleToolRequest(BaseModel):
    name: str
    enabled: bool


@router.post("/tools/toggle")
async def toggle_tool(request: ToggleToolRequest):
    """Toggle a tool (Mock persistence)."""
    # specific implementation depends on how MCP loads config.
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
