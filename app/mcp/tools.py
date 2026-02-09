"""MCP Tool definitions for Big Beautiful Screens.

This module defines the MCP tools and their JSON schemas. Schemas are generated
from Pydantic models in `app/mcp/arg_models.py` to avoid manual drift.
"""

from __future__ import annotations

from mcp.types import Tool

from .arg_models import (
    CreatePageArgs,
    CreateScreenArgs,
    DeleteScreenArgs,
    GetScreenArgs,
    ListLayoutsArgs,
    ListScreensArgs,
    SendMessageArgs,
    UpdateScreenArgs,
)
from .schema import input_schema_from_model


def list_screens_tool() -> Tool:
    return Tool(
        name="list_screens",
        description=(
            "List all screens accessible to the authenticated user. "
            "In SaaS mode, returns only the user's screens. "
            "In self-hosted mode, returns all screens. "
            "Supports pagination with page and per_page parameters."
        ),
        inputSchema=input_schema_from_model(ListScreensArgs),
    )


def create_screen_tool() -> Tool:
    return Tool(
        name="create_screen",
        description=(
            "Create a new display screen. Returns the screen ID and API key. "
            "Optionally provide a template_id to initialize with a template's configuration. "
            "In SaaS mode, the screen is owned by the authenticated user. "
            "In self-hosted mode, screens are created without ownership."
        ),
        inputSchema=input_schema_from_model(CreateScreenArgs),
    )


def get_screen_tool() -> Tool:
    return Tool(
        name="get_screen",
        description=(
            "Get details of a specific screen including its display settings. "
            "Returns screen ID, name, creation time, last update time, and settings."
        ),
        inputSchema=input_schema_from_model(GetScreenArgs),
    )


def update_screen_tool() -> Tool:
    return Tool(
        name="update_screen",
        description=(
            "Update a screen's properties including name, theme, rotation settings, "
            "and styling (colors, fonts, layout). Requires the screen's API key. "
            "You can apply a theme and override specific values in the same request."
        ),
        inputSchema=input_schema_from_model(UpdateScreenArgs),
    )


def delete_screen_tool() -> Tool:
    return Tool(
        name="delete_screen",
        description=(
            "Delete a screen and all its pages. This action is irreversible. "
            "Requires the screen's API key for authentication."
        ),
        inputSchema=input_schema_from_model(DeleteScreenArgs),
    )


def send_message_tool() -> Tool:
    return Tool(
        name="send_message",
        description=(
            "Send content to a screen's default page. Content can be text, markdown, "
            "images, or videos. Strings are auto-detected. "
            "Use structured content items for explicit control over content type and styling."
        ),
        inputSchema=input_schema_from_model(SendMessageArgs),
    )


def create_page_tool() -> Tool:
    return Tool(
        name="create_page",
        description=(
            "Create or update a named page on a screen. Pages are used for rotation/carousel. "
            "Each page can have its own content, layout, and styling. "
            "The 'default' page is the main page shown when rotation is disabled."
        ),
        inputSchema=input_schema_from_model(CreatePageArgs),
    )


def list_layouts_tool() -> Tool:
    return Tool(
        name="list_layouts",
        description=(
            "List all available layout presets. Layouts control how content panels "
            "are arranged on the screen. Returns preset names, descriptions, and "
            "configuration details."
        ),
        inputSchema=input_schema_from_model(ListLayoutsArgs),
    )
