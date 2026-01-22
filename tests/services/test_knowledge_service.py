import pytest
from unittest.mock import AsyncMock
from nebulus_gantry.services.knowledge_service import KnowledgeService


# Helper to create tool dicts
def create_tool(name):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": "",
            "parameters": {}
        }
    }


@pytest.mark.asyncio
async def test_search_web_success():
    # Mock MCP Client
    mock_mcp = AsyncMock()
    mock_mcp.list_tools.return_value = [create_tool("search_web")]

    # call_tool returns a STRING, not an object
    mock_mcp.call_tool.return_value = "Result 1"

    # Service
    service = KnowledgeService(mcp_client=mock_mcp)

    # Act
    result = await service.search_web("query")

    # Assert
    assert result == "Result 1"
    mock_mcp.call_tool.assert_called_with("search_web", {"query": "query", "max_results": 5})


@pytest.mark.asyncio
async def test_search_web_tool_missing():
    mock_mcp = AsyncMock()
    mock_mcp.list_tools.return_value = []  # No tools

    service = KnowledgeService(mcp_client=mock_mcp)

    result = await service.search_web("query")

    assert "not available" in result
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_read_url_success():
    mock_mcp = AsyncMock()
    mock_mcp.list_tools.return_value = [create_tool("scrape_url")]

    mock_mcp.call_tool.return_value = "Page Content"

    service = KnowledgeService(mcp_client=mock_mcp)

    result = await service.read_url("http://example.com")

    assert result == "Page Content"
    mock_mcp.call_tool.assert_called_with("scrape_url", {"url": "http://example.com"})


@pytest.mark.asyncio
async def test_read_document_pdf():
    mock_mcp = AsyncMock()
    mock_mcp.list_tools.return_value = [create_tool("read_pdf")]

    mock_mcp.call_tool.return_value = "PDF Content"

    service = KnowledgeService(mcp_client=mock_mcp)

    result = await service.read_document("/path/to/doc.pdf")

    assert result == "PDF Content"
    mock_mcp.call_tool.assert_called_with("read_pdf", {"path": "/path/to/doc.pdf"})


@pytest.mark.asyncio
async def test_read_document_docx():
    mock_mcp = AsyncMock()
    mock_mcp.list_tools.return_value = [create_tool("read_docx")]

    mock_mcp.call_tool.return_value = "DOCX Content"

    service = KnowledgeService(mcp_client=mock_mcp)

    result = await service.read_document("/path/to/doc.docx")

    assert result == "DOCX Content"
    mock_mcp.call_tool.assert_called_with("read_docx", {"path": "/path/to/doc.docx"})


@pytest.mark.asyncio
async def test_read_document_unsupported():
    mock_mcp = AsyncMock()
    service = KnowledgeService(mcp_client=mock_mcp)

    result = await service.read_document("/path/to/image.png")

    assert "Unsupported file type" in result


@pytest.mark.asyncio
async def test_search_web_formatting():
    """Verify that JSON results are formatted as Markdown."""
    mock_mcp = AsyncMock()
    mock_mcp.list_tools.return_value = [create_tool("search_web")]

    # Sample JSON return from MCP
    # Use strict JSON string
    json_result = '[{"title": "Nebulus Docs", "href": "https://nebulus.ai", "body": "Official documentation."}, {"title": "Gantry Guide", "href": "https://gantry.ai", "body": "User guide for Gantry."}]'

    mock_mcp.call_tool.return_value = json_result

    service = KnowledgeService(mcp_client=mock_mcp)
    result = await service.search_web("nebulus")

    assert "### 🔍 Search Results" in result
    assert "1. **[Nebulus Docs](https://nebulus.ai)**" in result
    assert "> Official documentation." in result
    assert "2. **[Gantry Guide](https://gantry.ai)**" in result
