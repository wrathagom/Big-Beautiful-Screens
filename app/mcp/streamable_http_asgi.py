"""Streamable HTTP transport for MCP (for Codex and other clients).

Big Beautiful Screens already exposes MCP via SSE endpoints in `app/mcp/routes.py`.
Codex (as of Feb 2026) supports MCP over stdio and "streamable HTTP" rather than
the legacy SSE + /messages pattern, so we expose an additional ASGI endpoint.

Implementation note:
- We run the MCP server in stateless mode per request. This keeps the wiring
  small and avoids managing long-lived session state in the web app.
"""

from __future__ import annotations

import anyio
from anyio.abc import TaskStatus
from mcp.server.streamable_http import StreamableHTTPServerTransport

from .server import mcp_server


def _accepts_sse(scope) -> bool:
    headers = dict(scope.get("headers") or [])
    accept = headers.get(b"accept", b"").decode("latin-1").lower()
    return "text/event-stream" in accept


class MCPStreamableHTTPApp:
    """ASGI app that handles MCP requests via Streamable HTTP."""

    async def __call__(self, scope, receive, send):
        # Some clients (including Codex variants) prefer JSON-only responses (no SSE streaming)
        # and will not send `Accept: text/event-stream`. StreamableHTTP supports both.
        json_only = not _accepts_sse(scope)

        transport = StreamableHTTPServerTransport(
            mcp_session_id=None,
            is_json_response_enabled=json_only,
        )

        async with anyio.create_task_group() as tg:

            async def run_server(*, task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED):
                async with transport.connect() as (read_stream, write_stream):
                    task_status.started()
                    await mcp_server.run(
                        read_stream,
                        write_stream,
                        mcp_server.create_initialization_options(),
                        stateless=True,
                    )

            await tg.start(run_server)
            await transport.handle_request(scope, receive, send)

            # Ensure we don't leak the server task after responding.
            await transport.terminate()
            tg.cancel_scope.cancel()


streamable_http_app = MCPStreamableHTTPApp()
