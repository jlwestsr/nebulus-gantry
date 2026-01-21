import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from nebulus_gantry.services.mcp_client import GantryMcpClient


@pytest.fixture
def mcp_client():
    return GantryMcpClient()


@pytest.mark.asyncio
async def test_list_tools_success(mcp_client):
    # Mock sse_client and ClientSession
    with patch("nebulus_gantry.services.mcp_client.sse_client") as mock_sse, \
         patch("nebulus_gantry.services.mcp_client.ClientSession") as mock_session_cls:

        # Configure sse_client context manager to yield (read, write)
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_sse.return_value.__aenter__.return_value = (mock_read, mock_write)

        # Setup Mock Session
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        # Mock ListToolsResult
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_tool.inputSchema = {"type": "object"}

        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        mock_session.list_tools.return_value = mock_result

        # Execute
        tools = await mcp_client.list_tools()

        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "test_tool"
        assert tools[0]["function"]["description"] == "A test tool"


@pytest.mark.asyncio
async def test_call_tool_success(mcp_client):
    with patch("nebulus_gantry.services.mcp_client.sse_client") as mock_sse, \
         patch("nebulus_gantry.services.mcp_client.ClientSession") as mock_session_cls:

        # Configure sse_client context manager
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_sse.return_value.__aenter__.return_value = (mock_read, mock_write)

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        # Mock CallToolResult
        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = "Tool Output"

        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_result.isError = False
        mock_session.call_tool.return_value = mock_result

        result = await mcp_client.call_tool("test_tool", {})
        assert result == "Tool Output"


@pytest.mark.asyncio
async def test_call_tool_error(mcp_client):
    with patch("nebulus_gantry.services.mcp_client.sse_client") as mock_sse, \
            patch("nebulus_gantry.services.mcp_client.ClientSession") as mock_session_cls:

        # Configure sse_client context manager
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_sse.return_value.__aenter__.return_value = (mock_read, mock_write)

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.content = []
        mock_result.isError = True
        mock_session.call_tool.return_value = mock_result

        result = await mcp_client.call_tool("test_tool", {})
        assert "Tool execution error" in result
