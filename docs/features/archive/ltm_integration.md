# Feature: LTM & MCP Integration

**Status**: In Progress
**Type**: Feature
**Owner**: Gantry Architect

## Overview

Integrates the Nebulus Long-Term Memory (LTM) system and Model Context Protocol (MCP) tools into the Gantry chat interface. This allows the AI to:

1. **Research Chat History**: Perform semantic searches across past conversations via ChromaDB.
2. **Use Tools**: Access external capabilities (Web Search, File System, etc.) provided by the Nebulus MCP Server.

## Architecture

### Components

1. **LTM Tool (`src/nebulus_gantry/tools/ltm.py`)**
    - **Type**: Direct Database Connection
    - **Target**: ChromaDB (`messages` collection)
    - **Function**: `search_chat_history(query)`
    - **Rationale**: The MCP Server does not currently expose a semantic search endpoint, so a direct read-only connection is established.

2. **MCP Client (`src/nebulus_gantry/services/mcp_client.py`)**
    - **Type**: SSE Client
    - **Target**: Nebulus MCP Server (`http://host.docker.internal:8000/sse`)
    - **Function**: Discovers and executes tools like `web_search` and `read_file`.

3. **Chat Integration (`src/nebulus_gantry/chat.py`)**
    - **Logic**:
        - Injects tool definitions into the Ollama System Prompt/API.
        - Parses tool calls from the LLM response.
        - Dispatches calls to `ltm.py` or `mcp_client.py`.
        - Returns results to the LLM for final synthesis.

## Dependencies

- `chromadb`: For LTM queries.
- `mcp`: For interacting with the MCP Server.

## User Experience

- **Explicit Research**: User asks "What did we cover in the last session?", AI calls `search_chat_history`.
- **Web/File Access**: User asks "Search the web for X", AI calls `web_search`.
