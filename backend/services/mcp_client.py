"""Lightweight MCP client for Nebulus Gantry.

Connects to the nebulus-core MCP server endpoint to list and execute tools.
Gracefully degrades when the MCP server is unavailable.
"""

import logging
from typing import Any, Optional

import httpx

from backend.platform import get_mcp_settings

logger = logging.getLogger(__name__)


class MCPClient:
    """Thin HTTP client for the nebulus-core MCP server.

    The MCP server handles tool execution — this client just relays
    requests and returns results.
    """

    def __init__(self) -> None:
        settings = get_mcp_settings()
        self._base_url: Optional[str] = None
        if settings:
            self._base_url = settings.get("url")
            if self._base_url:
                logger.info(f"MCP client configured: {self._base_url}")
            else:
                logger.debug("MCP settings present but no URL configured")
        else:
            logger.debug("MCP server not configured")

    @property
    def available(self) -> bool:
        """True if an MCP server URL is configured."""
        return self._base_url is not None

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server.

        Returns a list of tool descriptors, or an empty list
        if the server is unavailable.
        """
        if not self._base_url:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/tools")
                response.raise_for_status()
                data = response.json()
                return data.get("tools", [])
        except Exception as e:
            logger.warning(f"MCP list_tools failed: {e}")
            return []

    async def execute_tool(
        self, name: str, args: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Execute a tool on the MCP server.

        Args:
            name: Tool name to execute.
            args: Optional arguments to pass to the tool.

        Returns:
            Tool execution result dict, or None on failure.
        """
        if not self._base_url:
            return None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/tools/{name}/execute",
                    json=args or {},
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"MCP execute_tool({name}) failed: {e}")
            return None
