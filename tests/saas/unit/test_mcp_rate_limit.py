"""Tests for the per-key connection rate limit on /mcp/sse."""

import os
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(scope="module", autouse=True)
def saas_environment():
    """Run the MCP app in SaaS mode for this module."""
    original = os.environ.get("APP_MODE")
    os.environ["APP_MODE"] = "saas"

    from app.config import get_settings

    get_settings.cache_clear()
    yield
    if original is None:
        os.environ.pop("APP_MODE", None)
    else:
        os.environ["APP_MODE"] = original
    get_settings.cache_clear()


@pytest.fixture
def enabled_limiter():
    """Enable rate limiting (off under TESTING) with fresh counters."""
    from app import rate_limit

    rate_limit.reset_mcp_sse_limits()
    with patch.object(rate_limit.limiter, "enabled", True):
        yield rate_limit
    rate_limit.reset_mcp_sse_limits()


async def _call(path: str, api_key: str):
    from app.mcp.routes import mcp_app

    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/mcp{path}",
        "root_path": "/mcp",
        "headers": [(b"x-api-key", api_key.encode())],
        "query_string": b"",
    }
    await mcp_app(scope, receive, send)
    return sent[0]["status"], sent[0].get("headers", [])


class TestMcpSseLimit:
    def test_allows_burst_up_to_limit_then_blocks(self, enabled_limiter):
        allowed = [enabled_limiter.hit_mcp_sse_limit("ak_one") for _ in range(4)]
        assert allowed == [True, True, True, False]

    def test_limits_are_per_key(self, enabled_limiter):
        for _ in range(3):
            enabled_limiter.hit_mcp_sse_limit("ak_one")
        assert enabled_limiter.hit_mcp_sse_limit("ak_one") is False
        assert enabled_limiter.hit_mcp_sse_limit("ak_two") is True

    def test_hourly_cap_blocks_slow_steady_polling(self, enabled_limiter):
        """A client reconnecting every minute must hit the hourly cap."""
        from datetime import datetime, timedelta
        from unittest.mock import patch as mock_patch

        start = datetime(2026, 1, 1, 12, 0, 0)
        results = []
        for minute in range(30):
            now = (start + timedelta(minutes=minute)).timestamp()
            with mock_patch("time.time", return_value=now):
                results.append(enabled_limiter.hit_mcp_sse_limit("ak_poller"))
        assert results[:20] == [True] * 20
        assert results[20:] == [False] * 10

    def test_disabled_limiter_never_blocks(self):
        from app import rate_limit

        rate_limit.reset_mcp_sse_limits()
        with patch.object(rate_limit.limiter, "enabled", False):
            assert all(rate_limit.hit_mcp_sse_limit("ak_one") for _ in range(50))

    @pytest.mark.asyncio
    async def test_sse_returns_429_without_touching_the_database(self, enabled_limiter):
        for _ in range(3):
            enabled_limiter.hit_mcp_sse_limit("ak_hammer")

        with patch("app.mcp.routes.validate_account_key", new_callable=AsyncMock) as validate:
            status, headers = await _call("/sse", "ak_hammer")

        assert status == 429
        assert (b"retry-after", b"60") in headers
        validate.assert_not_called()

    @pytest.mark.asyncio
    async def test_messages_endpoint_is_not_limited(self, enabled_limiter):
        """Only new SSE connections count; message POSTs on a session do not."""
        for _ in range(3):
            enabled_limiter.hit_mcp_sse_limit("ak_hammer")

        with patch(
            "app.mcp.routes.validate_account_key", new_callable=AsyncMock, return_value=None
        ):
            status, _ = await _call("/messages", "ak_hammer")

        assert status == 401  # reached auth, not rate-limited
