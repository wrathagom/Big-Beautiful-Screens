"""MCP Server implementation for Big Beautiful Screens.

This module implements the MCP (Model Context Protocol) server that wraps
the existing REST API endpoints, enabling AI agents to manage screens,
content, and styling programmatically.

The server works in both SaaS and self-hosted modes:
- SaaS mode: Uses account API keys (ak_ prefix) for authentication
- Self-hosted mode: Uses simpler authentication (no account keys needed)
"""

import json
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl

from ..config import AppMode, get_settings
from .resources import RESOURCES, get_resource_content
from .tools import (
    create_page_tool,
    create_screen_tool,
    delete_screen_tool,
    get_screen_tool,
    list_layouts_tool,
    list_screens_tool,
    send_message_tool,
    update_screen_tool,
)

mcp_server = Server("big-beautiful-screens")


def get_all_tools() -> list[Tool]:
    """Get all available MCP tools."""
    return [
        list_screens_tool(),
        create_screen_tool(),
        get_screen_tool(),
        update_screen_tool(),
        delete_screen_tool(),
        send_message_tool(),
        create_page_tool(),
        list_layouts_tool(),
    ]


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return get_all_tools()


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    """Execute an MCP tool and return the result."""
    from .handlers import handle_tool_call

    result = await handle_tool_call(name, arguments or {})
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Resources – read-only documentation that helps AI clients understand
# how to use the tools effectively.
# ---------------------------------------------------------------------------


@mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    return RESOURCES


@mcp_server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    return get_resource_content(str(uri))


def create_mcp_server() -> Server:
    """Create and return the MCP server instance."""
    return mcp_server


async def run_mcp_server():
    """Run the MCP server using stdio transport."""
    settings = get_settings()
    mode = "SaaS" if settings.APP_MODE == AppMode.SAAS else "self-hosted"
    print(f"Starting Big Beautiful Screens MCP server in {mode} mode...")

    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )


@asynccontextmanager
async def get_mcp_server_context():
    """Context manager for MCP server lifecycle."""
    yield mcp_server
