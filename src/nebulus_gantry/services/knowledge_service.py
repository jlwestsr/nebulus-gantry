import logging
from typing import Optional
from nebulus_gantry.services.mcp_client import get_mcp_client, GantryMcpClient

logger = logging.getLogger(__name__)


class KnowledgeService:
    """
    Orchestrates knowledge retrieval from external sources via the Nebulus MCP Server.
    """

    def __init__(self, mcp_client: Optional[GantryMcpClient] = None):
        self.mcp = mcp_client or get_mcp_client()

    async def search_web(self, query: str, max_results: int = 5) -> str:
        """
        Search the web using the Nebulus MCP 'search_web' tool.
        """
        try:
            # Check availability
            tools = await self.mcp.list_tools()
            # tools are OpenAI tool definitions (dicts)
            if not any(t["function"]["name"] == "search_web" for t in tools):
                logger.error(f"Tools available: {[t['function']['name'] for t in tools]}")
                return "Error: 'search_web' tool not available on Nebulus MCP."

            # Execute
            result = await self.mcp.call_tool("search_web", {"query": query, "max_results": max_results})
            return result
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return f"Error performing web search: {str(e)}"

    async def read_url(self, url: str) -> str:
        """
        Read the content of a URL using the Nebulus MCP 'scrape_url' tool.
        """
        try:
            tools = await self.mcp.list_tools()
            if not any(t["function"]["name"] == "scrape_url" for t in tools):
                return "Error: 'scrape_url' tool not available on Nebulus MCP."

            return await self.mcp.call_tool("scrape_url", {"url": url})
        except Exception as e:
            logger.error(f"URL read failed: {e}")
            return f"Error reading URL: {str(e)}"

    async def read_document(self, path: str) -> str:
        """
        Read a document (PDF/DOCX) using Nebulus MCP tools.
        Automatically selects read_pdf or read_docx based on extension.
        """
        try:
            tool_name = None
            if path.lower().endswith(".pdf"):
                tool_name = "read_pdf"
            elif path.lower().endswith(".docx"):
                tool_name = "read_docx"
            else:
                return f"Error: Unsupported file type for {path}"

            tools = await self.mcp.list_tools()
            if not any(t["function"]["name"] == tool_name for t in tools):
                return f"Error: '{tool_name}' tool not available on Nebulus MCP."

            return await self.mcp.call_tool(tool_name, {"path": path})
        except Exception as e:
            logger.error(f"Document read failed: {e}")
            return f"Error reading document: {str(e)}"


# Singleton Global
_knowledge_service = None


def get_knowledge_service() -> KnowledgeService:
    global _knowledge_service
    if not _knowledge_service:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
