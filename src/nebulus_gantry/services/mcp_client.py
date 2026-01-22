from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import CallToolResult
import os
from typing import List, Dict, Any


class GantryMcpClient:
    def __init__(self, host: str = "http://host.docker.internal:8000"):
        """
        Initialize MCP Client.
        Default host assumes connection from Gantry container to MCP container via Docker DNS.
        """
        self.host = os.getenv("MCP_HOST", host)
        self.sse_url = f"{self.host}/sse"
        self._tools: List[Dict[str, Any]] = []

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Connects to MCP Server, lists tools, and disconnects.
        Ideally, we would maintain a persistent connection, but for HTTP/SSE statelessness
        in this context, we might connect-query-close or keep a session manager.
        """
        try:
            # We must trick FastMCP into thinking we are localhost to avoid "Invalid Host header"
            # when connecting via host.docker.internal
            headers = {"Host": "localhost:8002"}
            async with sse_client(self.sse_url, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()

                    # Transform to OpenAI/Ollama friendly format
                    self._tools = []
                    for tool in result.tools:
                        tool_def = {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema
                            }
                        }
                        self._tools.append(tool_def)

                    return self._tools
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error listing MCP tools: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Call a specific tool on the MCP server."""
        try:
            headers = {"Host": "localhost:8002"}
            async with sse_client(self.sse_url, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result: CallToolResult = await session.call_tool(name, arguments)

                    # Concatenate text content
                    output = []
                    if result.content:
                        for item in result.content:
                            if item.type == "text":
                                output.append(item.text)
                            elif item.type == "image":
                                output.append("[Image returned]")

                    final_output = "\n".join(output)
                    if result.isError:
                        return f"Tool execution error: {final_output}"

                    return final_output
        except Exception as e:
            return f"Error executing tool {name}: {str(e)}"


# Singleton or factory
_client = None


def get_mcp_client():
    global _client
    if not _client:
        _client = GantryMcpClient()
    return _client
