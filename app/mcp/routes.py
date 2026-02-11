"""ASGI application for MCP server over HTTP/SSE.

This module provides a single ASGI application that handles all MCP
transport endpoints.  It is mounted on the main FastAPI app at ``/mcp``.

The SSE transport methods (connect_sse, handle_post_message) manage the
full ASGI response lifecycle internally, so they cannot be wrapped in
FastAPI/Starlette Route endpoints (which would send a second response).
Instead, all MCP paths are routed inside a single ASGI app so that they
share the same ``root_path`` and the SSE transport computes the correct
message URL for clients.
"""

from mcp.server.sse import SseServerTransport
from starlette.responses import Response

from ..auth import validate_account_key
from ..config import AppMode, get_settings
from .handlers import reset_mcp_context, set_mcp_context
from .server import mcp_server
from .streamable_http_asgi import streamable_http_app

# "/messages" is relative — when mounted at /mcp the transport resolves
# the full client POST path as root_path + "/messages" = "/mcp/messages".
sse_transport = SseServerTransport("/messages")


class MCPApp:
    """Combined ASGI app for all MCP endpoints.

    Routes:
        /sse      – SSE connection for MCP communication
        /messages – POST endpoint for MCP messages (used by SSE clients)
        /http     – Streamable HTTP transport (Codex / non-SSE clients)
    """

    @staticmethod
    def _local_path(scope):
        """Return the path relative to this app's mount point.

        Starlette's Mount does not modify ``scope["path"]``; it only
        updates ``root_path``.  We strip root_path to get the local
        portion that this app should route on.
        """
        path = scope.get("path", "")
        root = scope.get("root_path", "")
        if root and path.startswith(root):
            path = path[len(root) :]
        return path or "/"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return

        settings = get_settings()

        headers = dict(scope.get("headers", []))
        api_key = headers.get(b"x-api-key", b"").decode("utf-8")

        if settings.APP_MODE == AppMode.SAAS:
            if not api_key or not api_key.startswith("ak_"):
                response = Response("Unauthorized: X-API-Key header required", status_code=401)
                await response(scope, receive, send)
                return

            user = await validate_account_key(api_key)
            if not user:
                response = Response("Unauthorized: Invalid or expired API key", status_code=401)
                await response(scope, receive, send)
                return

            token = set_mcp_context(api_key=api_key, user_id=user.user_id)
        else:
            token = set_mcp_context()

        try:
            path = self._local_path(scope)

            if path in ("/sse", "/sse/"):
                async with sse_transport.connect_sse(scope, receive, send) as streams:
                    await mcp_server.run(
                        streams[0],
                        streams[1],
                        mcp_server.create_initialization_options(),
                    )
            elif path.startswith("/messages"):
                await sse_transport.handle_post_message(scope, receive, send)
            elif path.startswith("/http"):
                await streamable_http_app(scope, receive, send)
            else:
                response = Response("Not Found", status_code=404)
                await response(scope, receive, send)
        finally:
            reset_mcp_context(token)


mcp_app = MCPApp()
