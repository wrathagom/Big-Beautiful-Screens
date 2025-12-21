"""Structured usage logging middleware for API calls.

Logs API calls in Elasticsearch-compatible JSON format (ECS - Elastic Common Schema).
Designed to be non-blocking using async fire-and-forget pattern.
"""

import asyncio
import json
import logging
import re
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Configure usage logger
usage_logger = logging.getLogger("bbs.usage")


class UsageLoggingMiddleware(BaseHTTPMiddleware):
    """Logs API calls in Elasticsearch-compatible JSON format without blocking requests."""

    # Regex to extract screen_id from paths like /api/v1/screens/{screen_id}/...
    SCREEN_ID_PATTERN = re.compile(r"/api/v1/screens/([a-zA-Z0-9]+)")

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log usage data."""
        # Only log API endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Skip health checks and similar
        if request.url.path in ("/api/health", "/api/v1/health"):
            return await call_next(request)

        start_time = datetime.now(UTC)

        # Process request
        response = await call_next(request)

        # Calculate duration
        end_time = datetime.now(UTC)
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Extract user info from request state (set by auth middleware if available)
        user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None

        # Extract screen_id from path if present
        screen_id = None
        match = self.SCREEN_ID_PATTERN.search(request.url.path)
        if match:
            screen_id = match.group(1)

        # Build ECS-compatible log entry
        log_entry = {
            "@timestamp": start_time.isoformat(),
            "event": {
                "category": "api",
                "action": request.method.lower(),
                "duration": int(duration_ms * 1_000_000),  # nanoseconds for ECS
                "outcome": "success" if response.status_code < 400 else "failure",
            },
            "http": {
                "request": {
                    "method": request.method,
                },
                "response": {
                    "status_code": response.status_code,
                },
            },
            "url": {
                "path": request.url.path,
                "query": str(request.url.query) if request.url.query else None,
            },
            "client": {
                "ip": request.client.host if request.client else None,
            },
            "user_agent": {
                "original": request.headers.get("user-agent"),
            },
        }

        # Add user info if available
        if user_id:
            log_entry["user"] = {"id": user_id}

        # Add screen info if available
        if screen_id:
            log_entry["screen"] = {"id": screen_id}

        # Log asynchronously to not block response
        asyncio.create_task(self._write_log(log_entry))

        return response

    async def _write_log(self, entry: dict) -> None:
        """Write log entry asynchronously (non-blocking)."""
        import contextlib

        with contextlib.suppress(Exception):
            # Output as JSON for Elasticsearch ingestion
            usage_logger.info(json.dumps(entry, default=str))


def configure_usage_logging(destination: str = "stdout", file_path: str | None = None) -> None:
    """Configure the usage logger based on settings.

    Args:
        destination: Where to log - "stdout", "file", or "external"
        file_path: Path to log file (required if destination is "file")
    """
    logger = logging.getLogger("bbs.usage")
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    logger.handlers.clear()

    # Prevent propagation to root logger
    logger.propagate = False

    if destination == "stdout":
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    elif destination == "file" and file_path:
        # Ensure directory exists
        from pathlib import Path

        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(file_path)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    # "external" means no local handler - logs go to external service via separate config
