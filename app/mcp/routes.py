"""FastAPI routes for MCP server over HTTP/SSE.

This module provides HTTP endpoints for the MCP server, allowing it to run
as part of the FastAPI application on Railway or other hosting platforms.

The MCP protocol is exposed via Server-Sent Events (SSE) for real-time
communication with AI agents.
"""

from fastapi import APIRouter, Request
from fastapi.responses import Response
from mcp.server.sse import SseServerTransport
from starlette.responses import StreamingResponse

from .server import mcp_server

router = APIRouter(prefix="/mcp", tags=["MCP"])

sse_transport = SseServerTransport("/mcp/messages")


@router.get("/sse")
async def mcp_sse_endpoint(request: Request) -> StreamingResponse:
    """SSE endpoint for MCP communication.

    AI agents connect to this endpoint to receive server-sent events.
    This is the main communication channel for the MCP protocol.
    """
    async with sse_transport.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )

    return Response(status_code=200)


@router.post("/messages")
async def mcp_messages_endpoint(request: Request) -> Response:
    """POST endpoint for MCP messages.

    AI agents send messages to this endpoint. The messages are processed
    and responses are sent back via the SSE connection.
    """
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return Response(status_code=202)
