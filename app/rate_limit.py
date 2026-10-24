"""Rate limiting configuration using slowapi."""

import os

from limits import parse_many
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from slowapi import Limiter
from slowapi.util import get_remote_address

# Disable rate limiting during tests
_testing = os.environ.get("TESTING", "").lower() in ("1", "true", "yes")

# Create limiter instance - uses client IP by default
limiter = Limiter(key_func=get_remote_address, enabled=not _testing)

# Rate limit constants
RATE_LIMIT_UPLOADS = "10/minute"  # File uploads are expensive
RATE_LIMIT_CREATE = "20/minute"  # Creating resources
RATE_LIMIT_MUTATE = "60/minute"  # Updates/deletes
RATE_LIMIT_READ = "200/minute"  # Reading data
RATE_LIMIT_AUTH = "10/minute"  # Auth-related endpoints (prevent brute force)

# MCP SSE connections, per account key. A real client holds one long-lived
# stream and only reconnects occasionally; the hourly cap stops clients that
# poll by reconnecting in a loop.
RATE_LIMIT_MCP_SSE = "3/minute;20/hour"

_mcp_sse_limits = parse_many(RATE_LIMIT_MCP_SSE)
_mcp_sse_storage = MemoryStorage()
_mcp_sse_limiter = MovingWindowRateLimiter(_mcp_sse_storage)


def hit_mcp_sse_limit(api_key: str) -> bool:
    """Record an SSE connection attempt for this key; False once over the limit."""
    if not limiter.enabled:
        return True
    return all(_mcp_sse_limiter.hit(limit, "mcp_sse", api_key) for limit in _mcp_sse_limits)


def reset_mcp_sse_limits() -> None:
    """Clear all MCP SSE counters (for tests)."""
    _mcp_sse_storage.reset()
