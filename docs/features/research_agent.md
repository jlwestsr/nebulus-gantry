# Feature: Research Agent (Knowledge Service)

## 1. Overview

**Branch**: `feat/research-agent`

This feature integrates Nebulus Gantry with the Nebulus MCP Server to provide "Research Agent" capabilities. It allows the Gantry Chat interface to perform web searches, read URLs, and parse documents (PDF/DOCX) by delegating these tasks to the underlying Nebulus infrastructure via MCP.

## 2. Requirements

- [ ] **Web Search**: The AI must be able to query DuckDuckGo and receive results.
- [ ] **URL Reading**: The AI must be able to fetch and read the content of a given URL.
- [ ] **Document Reading**: The AI must be able to read PDF/DOCX files from the workspace.
- [ ] **Unified Service**: A `KnowledgeService` must orchestrate these calls.

## 3. Technical Implementation

- **Modules**:
  - `src/nebulus_gantry/services/knowledge_service.py` (New): Wrapper for MCP tools.
  - `src/nebulus_gantry/chat.py` (Modified): Register tools with LLM and handle execution.
- **Dependencies**: None (Uses existing `mcp_client`).
- **Data**: None.

## 4. Verification Plan

**Automated Tests**:

- [ ] Script/Test: `pytest tests/services/test_knowledge_service.py`
- [ ] Logic Verified: Mock `McpClient` to ensure `KnowledgeService` correctly translates tool calls.

**Manual Verification**:

- [ ] Step 1: Start Gantry with `./bin/gantry start`.
- [ ] Step 2: Ask "Search the web for the latest Nebulus features."
- [ ] Step 3: Ask "Read <https://example.com>".
- [ ] Step 4: Verify correct responses in Chat UI.

## 5. Workflow Checklist

- [ ] **Branch**: Created `feat/research-agent` branch?
- [ ] **Work**: Implemented changes?
- [ ] **Test**: All tests pass (`pytest`)?
- [ ] **Doc**: Updated `README.md` and `walkthrough.md`?
- [ ] **Data**: `git add .`, `git commit`, `git push`?
