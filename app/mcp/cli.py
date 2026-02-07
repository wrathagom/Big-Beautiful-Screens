"""CLI entry point for running the MCP server standalone.

This module provides a command-line interface to run the MCP server
using stdio transport, which is the standard way for AI agents like
Claude Desktop to communicate with MCP servers.

Usage:
    python -m app.mcp.cli

Or via the installed script:
    bbs-mcp-server
"""

import asyncio
import os
import sys


def main():
    """Main entry point for the MCP server CLI."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from app.mcp.server import run_mcp_server

    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()
