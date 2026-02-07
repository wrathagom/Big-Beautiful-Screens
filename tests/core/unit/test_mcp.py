"""Tests for MCP (Model Context Protocol) server module."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Set up a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = str(Path(tmpdir) / "test_mcp.db")
        os.environ["SQLITE_PATH"] = test_db_path

        from app.config import get_settings

        get_settings.cache_clear()

        from app.db.factory import reset_database

        reset_database()

        import asyncio
        import concurrent.futures

        import app.database as db_module

        try:
            asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(asyncio.run, db_module.init_db()).result()
        except RuntimeError:
            asyncio.run(db_module.init_db())

        yield

        reset_database()
        get_settings.cache_clear()


class TestMCPTools:
    """Tests for MCP tool definitions."""

    def test_list_screens_tool(self):
        """Test list_screens tool definition."""
        from app.mcp.tools import list_screens_tool

        tool = list_screens_tool()
        assert tool.name == "list_screens"
        assert "List all screens" in tool.description
        assert tool.inputSchema["type"] == "object"
        assert "page" in tool.inputSchema["properties"]
        assert "per_page" in tool.inputSchema["properties"]

    def test_create_screen_tool(self):
        """Test create_screen tool definition."""
        from app.mcp.tools import create_screen_tool

        tool = create_screen_tool()
        assert tool.name == "create_screen"
        assert "Create a new display screen" in tool.description
        assert "name" in tool.inputSchema["properties"]
        assert "template_id" in tool.inputSchema["properties"]

    def test_get_screen_tool(self):
        """Test get_screen tool definition."""
        from app.mcp.tools import get_screen_tool

        tool = get_screen_tool()
        assert tool.name == "get_screen"
        assert "screen_id" in tool.inputSchema["properties"]
        assert "screen_id" in tool.inputSchema["required"]

    def test_update_screen_tool(self):
        """Test update_screen tool definition."""
        from app.mcp.tools import update_screen_tool

        tool = update_screen_tool()
        assert tool.name == "update_screen"
        assert "screen_id" in tool.inputSchema["required"]
        assert "api_key" in tool.inputSchema["required"]
        assert "theme" in tool.inputSchema["properties"]
        assert "rotation_enabled" in tool.inputSchema["properties"]

    def test_delete_screen_tool(self):
        """Test delete_screen tool definition."""
        from app.mcp.tools import delete_screen_tool

        tool = delete_screen_tool()
        assert tool.name == "delete_screen"
        assert "screen_id" in tool.inputSchema["required"]
        assert "api_key" in tool.inputSchema["required"]

    def test_send_message_tool(self):
        """Test send_message tool definition."""
        from app.mcp.tools import send_message_tool

        tool = send_message_tool()
        assert tool.name == "send_message"
        assert "screen_id" in tool.inputSchema["required"]
        assert "api_key" in tool.inputSchema["required"]
        assert "content" in tool.inputSchema["required"]
        assert "layout" in tool.inputSchema["properties"]

    def test_create_page_tool(self):
        """Test create_page tool definition."""
        from app.mcp.tools import create_page_tool

        tool = create_page_tool()
        assert tool.name == "create_page"
        assert "screen_id" in tool.inputSchema["required"]
        assert "page_name" in tool.inputSchema["required"]
        assert "api_key" in tool.inputSchema["required"]
        assert "content" in tool.inputSchema["required"]
        assert "duration" in tool.inputSchema["properties"]

    def test_list_layouts_tool(self):
        """Test list_layouts tool definition."""
        from app.mcp.tools import list_layouts_tool

        tool = list_layouts_tool()
        assert tool.name == "list_layouts"
        assert "layout presets" in tool.description


class TestMCPServer:
    """Tests for MCP server setup."""

    def test_create_mcp_server(self):
        """Test MCP server creation."""
        from app.mcp import create_mcp_server

        server = create_mcp_server()
        assert server is not None
        assert server.name == "big-beautiful-screens"

    def test_get_all_tools(self):
        """Test that all tools are returned."""
        from app.mcp.server import get_all_tools

        tools = get_all_tools()
        assert len(tools) == 8
        tool_names = [t.name for t in tools]
        assert "list_screens" in tool_names
        assert "create_screen" in tool_names
        assert "get_screen" in tool_names
        assert "update_screen" in tool_names
        assert "delete_screen" in tool_names
        assert "send_message" in tool_names
        assert "create_page" in tool_names
        assert "list_layouts" in tool_names


class TestMCPHandlers:
    """Tests for MCP tool handlers."""

    @pytest.mark.asyncio
    async def test_handle_list_layouts(self, setup_test_db):
        """Test list_layouts handler."""
        from app.mcp.handlers import handle_list_layouts

        result = await handle_list_layouts({})
        assert "layouts" in result
        assert len(result["layouts"]) > 0

    @pytest.mark.asyncio
    async def test_handle_list_screens(self, setup_test_db):
        """Test list_screens handler."""
        from app.mcp.handlers import handle_list_screens

        result = await handle_list_screens({})
        assert "screens" in result
        assert "total_count" in result
        assert "page" in result
        assert "per_page" in result

    @pytest.mark.asyncio
    async def test_handle_list_screens_pagination(self, setup_test_db):
        """Test list_screens handler with pagination."""
        from app.mcp.handlers import handle_list_screens

        result = await handle_list_screens({"page": 1, "per_page": 5})
        assert result["per_page"] == 5
        assert result["page"] == 1

    @pytest.mark.asyncio
    async def test_handle_create_screen(self, setup_test_db):
        """Test create_screen handler."""
        from app.mcp.handlers import handle_create_screen

        result = await handle_create_screen({"name": "Test MCP Screen"})
        assert "screen_id" in result
        assert "api_key" in result
        assert result["api_key"].startswith("sk_")
        assert result["name"] == "Test MCP Screen"

    @pytest.mark.asyncio
    async def test_handle_get_screen(self, setup_test_db):
        """Test get_screen handler."""
        from app.mcp.handlers import handle_create_screen, handle_get_screen

        created = await handle_create_screen({"name": "Get Test"})
        result = await handle_get_screen({"screen_id": created["screen_id"]})
        assert result["screen_id"] == created["screen_id"]
        assert result["name"] == "Get Test"

    @pytest.mark.asyncio
    async def test_handle_get_screen_not_found(self, setup_test_db):
        """Test get_screen handler with nonexistent screen."""
        from app.mcp.handlers import handle_get_screen

        result = await handle_get_screen({"screen_id": "nonexistent123"})
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_get_screen_missing_id(self, setup_test_db):
        """Test get_screen handler without screen_id."""
        from app.mcp.handlers import handle_get_screen

        result = await handle_get_screen({})
        assert "error" in result
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_send_message(self, setup_test_db):
        """Test send_message handler."""
        from app.mcp.handlers import handle_create_screen, handle_send_message

        screen = await handle_create_screen({})
        result = await handle_send_message({
            "screen_id": screen["screen_id"],
            "api_key": screen["api_key"],
            "content": ["Hello from MCP!", "# Markdown heading"],
        })
        assert result["success"] is True
        assert "viewers" in result

    @pytest.mark.asyncio
    async def test_handle_send_message_wrong_key(self, setup_test_db):
        """Test send_message handler with wrong API key."""
        from app.mcp.handlers import handle_create_screen, handle_send_message

        screen = await handle_create_screen({})
        result = await handle_send_message({
            "screen_id": screen["screen_id"],
            "api_key": "sk_wrong_key",
            "content": ["Should fail"],
        })
        assert "error" in result
        assert "Invalid API key" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_send_message_missing_content(self, setup_test_db):
        """Test send_message handler without content."""
        from app.mcp.handlers import handle_create_screen, handle_send_message

        screen = await handle_create_screen({})
        result = await handle_send_message({
            "screen_id": screen["screen_id"],
            "api_key": screen["api_key"],
        })
        assert "error" in result
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_create_page(self, setup_test_db):
        """Test create_page handler."""
        from app.mcp.handlers import handle_create_page, handle_create_screen

        screen = await handle_create_screen({})
        result = await handle_create_page({
            "screen_id": screen["screen_id"],
            "page_name": "alerts",
            "api_key": screen["api_key"],
            "content": ["Alert message!"],
        })
        assert result["success"] is True
        assert result["page"]["name"] == "alerts"

    @pytest.mark.asyncio
    async def test_handle_create_page_with_duration(self, setup_test_db):
        """Test create_page handler with duration."""
        from app.mcp.handlers import handle_create_page, handle_create_screen

        screen = await handle_create_screen({})
        result = await handle_create_page({
            "screen_id": screen["screen_id"],
            "page_name": "promo",
            "api_key": screen["api_key"],
            "content": ["Special offer!"],
            "duration": 15,
        })
        assert result["success"] is True
        assert result["page"]["duration"] == 15

    @pytest.mark.asyncio
    async def test_handle_update_screen(self, setup_test_db):
        """Test update_screen handler."""
        from app.mcp.handlers import handle_create_screen, handle_update_screen

        screen = await handle_create_screen({"name": "Original"})
        result = await handle_update_screen({
            "screen_id": screen["screen_id"],
            "api_key": screen["api_key"],
            "name": "Updated Name",
            "rotation_enabled": True,
            "rotation_interval": 20,
        })
        assert result["success"] is True
        assert result["settings"]["enabled"] is True
        assert result["settings"]["interval"] == 20

    @pytest.mark.asyncio
    async def test_handle_update_screen_wrong_key(self, setup_test_db):
        """Test update_screen handler with wrong API key."""
        from app.mcp.handlers import handle_create_screen, handle_update_screen

        screen = await handle_create_screen({})
        result = await handle_update_screen({
            "screen_id": screen["screen_id"],
            "api_key": "sk_wrong_key",
            "name": "Should fail",
        })
        assert "error" in result
        assert "Invalid API key" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_delete_screen(self, setup_test_db):
        """Test delete_screen handler."""
        from app.mcp.handlers import (
            handle_create_screen,
            handle_delete_screen,
            handle_get_screen,
        )

        screen = await handle_create_screen({})
        result = await handle_delete_screen({
            "screen_id": screen["screen_id"],
            "api_key": screen["api_key"],
        })
        assert result["success"] is True

        get_result = await handle_get_screen({"screen_id": screen["screen_id"]})
        assert "error" in get_result

    @pytest.mark.asyncio
    async def test_handle_delete_screen_wrong_key(self, setup_test_db):
        """Test delete_screen handler with wrong API key."""
        from app.mcp.handlers import handle_create_screen, handle_delete_screen

        screen = await handle_create_screen({})
        result = await handle_delete_screen({
            "screen_id": screen["screen_id"],
            "api_key": "sk_wrong_key",
        })
        assert "error" in result
        assert "Invalid API key" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_tool_call_routing(self, setup_test_db):
        """Test that handle_tool_call routes to correct handlers."""
        from app.mcp.handlers import handle_tool_call

        result = await handle_tool_call("list_layouts", {})
        assert "layouts" in result

        result = await handle_tool_call("unknown_tool", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]


class TestMCPContext:
    """Tests for MCP context management."""

    def test_get_mcp_context_default(self):
        """Test getting default MCP context."""
        from app.mcp.handlers import get_mcp_context

        ctx = get_mcp_context()
        assert ctx is not None
        assert ctx.is_self_hosted is True

    def test_set_mcp_context(self):
        """Test setting MCP context."""
        from app.mcp.handlers import get_mcp_context, set_mcp_context

        set_mcp_context(api_key="ak_test_key", user_id="user_123")
        ctx = get_mcp_context()
        assert ctx.api_key == "ak_test_key"
        assert ctx.user_id == "user_123"

        set_mcp_context()
