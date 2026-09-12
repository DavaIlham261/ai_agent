import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_CONNECT_TIMEOUT_SECONDS = 5  # SKPL-NF07: terpisah dari timeout 60 detik keseluruhan (SKPL-F01)


class MCPUnreachableError(Exception):
    pass


def _mcp_url(project: dict) -> str:
    return f"http://{project['tailscale_ip']}:{project['port']}/mcp"


async def fetch_mcp_tools(project: dict, project_id: str) -> list[dict]:
    """Ambil daftar tools dari MCP Server, dikonversi ke format function-calling OpenAI."""
    url = _mcp_url(project)
    try:
        async with asyncio.timeout(MCP_CONNECT_TIMEOUT_SECONDS):
            async with streamablehttp_client(url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
    except Exception as e:
        raise MCPUnreachableError(
            f"MCP Server tidak dapat dijangkau untuk proyek: {project_id}"
        ) from e

    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        for t in tools_result.tools
    ]


async def call_mcp_tool(project: dict, project_id: str, tool_name: str, tool_args: dict) -> str:
    url = _mcp_url(project)
    try:
        async with asyncio.timeout(MCP_CONNECT_TIMEOUT_SECONDS):
            async with streamablehttp_client(url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, tool_args)
    except Exception as e:
        raise MCPUnreachableError(
            f"MCP Server tidak dapat dijangkau untuk proyek: {project_id}"
        ) from e

    text_parts = [c.text for c in result.content if hasattr(c, "text")]
    output = "\n".join(text_parts)
    return f"Error dari tool: {output}" if result.isError else output