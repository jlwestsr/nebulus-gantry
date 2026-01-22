
import pytest
from unittest.mock import AsyncMock
from nebulus_gantry.services.knowledge_service import KnowledgeService


@pytest.fixture
def mock_mcp_client():
    """
    Creates a mock GantryMcpClient with predefined tool responses.
    """
    mock = AsyncMock()
    # Default behavior: list_tools returns the tools we expect
    mock.list_tools.return_value = [
        {"function": {"name": "search_web"}},
        {"function": {"name": "scrape_url"}},
        {"function": {"name": "read_pdf"}},
    ]
    return mock


@pytest.mark.asyncio
async def test_search_web_success(mock_mcp_client):
    """
    Test that search_web calls the MCP client correctly and returns the result.
    """
    # Setup
    service = KnowledgeService(mcp_client=mock_mcp_client)
    mock_mcp_client.call_tool.return_value = "Search Results: Python is great."

    # Execute
    result = await service.search_web(query="Python", max_results=3)

    # Verify
    assert "Search Results" in result
    mock_mcp_client.call_tool.assert_awaited_once_with(
        "search_web", {"query": "Python", "max_results": 3}
    )


@pytest.mark.asyncio
async def test_search_web_tool_missing(mock_mcp_client):
    """
    Test that search_web handles the case where the tool is not available.
    """
    # Setup: Return empty tool list
    mock_mcp_client.list_tools.return_value = []
    service = KnowledgeService(mcp_client=mock_mcp_client)

    # Execute
    result = await service.search_web("query")

    # Verify
    assert "Error: 'search_web' tool not available" in result
    mock_mcp_client.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_read_document_pdf(mock_mcp_client):
    """
    Test that read_document correctly selects the 'read_pdf' tool for .pdf files.
    """
    service = KnowledgeService(mcp_client=mock_mcp_client)
    mock_mcp_client.call_tool.return_value = "PDF Content"

    result = await service.read_document("/path/to/doc.pdf")

    assert result == "PDF Content"
    mock_mcp_client.call_tool.assert_awaited_once_with(
        "read_pdf", {"path": "/path/to/doc.pdf"}
    )
