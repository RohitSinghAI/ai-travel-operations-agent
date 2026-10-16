
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def get_server_path() -> Path:
    """Return the absolute path to the MCP server."""
    project_root = Path(__file__).resolve().parents[3]
    server_path = project_root / "mcp-servers" / "travel_tools_server.py"

    if not server_path.exists():
        raise FileNotFoundError(
            f"MCP server file not found: {server_path}"
        )

    return server_path


def get_server_parameters() -> StdioServerParameters:
    """Configure the Python process used to launch the MCP server."""
    server_path = get_server_path()
    project_root = server_path.parent.parent

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(project_root)
        if not existing_pythonpath
        else str(project_root) + os.pathsep + existing_pythonpath
    )

    return StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        env=env,
    )


async def list_travel_mcp_tools() -> list[dict[str, str]]:
    """Connect to the MCP server and list its registered tools."""
    server_params = get_server_parameters()

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()

            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                }
                for tool in result.tools
            ]


async def call_travel_mcp_tool(
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Call a registered tool on the MCP server."""
    server_params = get_server_parameters()

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            result = await session.call_tool(
                name,
                arguments=arguments,
            )

            if result.isError:
                messages = [
                    getattr(item, "text", "")
                    for item in result.content
                ]
                raise RuntimeError(
                    f"MCP tool '{name}' failed: {' '.join(messages)}"
                )

            structured_content = getattr(
                result, "structuredContent", None
            )

            if structured_content is not None:
                return {
                    "tool": name,
                    "result": structured_content,
                }

            content = [
                {"type": item.type, "text": item.text}
                if hasattr(item, "text")
                else {"type": item.type}
                for item in result.content
            ]

            return {
                "tool": name,
                "result": content,
            }
