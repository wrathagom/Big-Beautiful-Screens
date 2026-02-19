"""MCP (Model Context Protocol) server for Big Beautiful Screens.

This module provides MCP server functionality that enables AI agents (like Claude)
to programmatically manage screens, content, and styling through the MCP protocol.
"""

from .server import create_mcp_server, mcp_server

__all__ = ["create_mcp_server", "mcp_server"]
