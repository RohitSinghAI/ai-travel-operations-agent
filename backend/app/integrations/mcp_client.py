
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def list_travel_mcp_tools() -> list[dict]:
    project_root = Path(__file__).resolve().parents[4]
    server_path = project_root / "mcp-servers" / "travel_tools_server.py"

    if not server_path.exists():
        raise FileNotFoundError(
            f"MCP server not found: {server_path}"
        )

    server_params = StdioServerParameters(
        command=os.getenv("PYTHON_EXECUTABLE", "python"),
        args=[str(server_path)],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()

            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                }
                for tool in result.tools
            ]
