import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from nebulus_gantry.services.mcp_client import GantryMcpClient  # noqa: E402


async def main():
    # mcp-server is exposed on localhost:8002 by docker-compose
    host = "http://localhost:8002"
    print(f"Connecting to MCP at {host}...")

    client = GantryMcpClient(host=host)
    try:
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools:")
        for t in tools:
            name = t.get("function", {}).get("name")
            print(f" - {name}")

        print("\nFull dump of first tool if exists:")
        if tools:
            print(tools[0])

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
