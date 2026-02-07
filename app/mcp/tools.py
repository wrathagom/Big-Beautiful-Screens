"""MCP Tool definitions for Big Beautiful Screens.

This module defines the MCP tools that wrap the existing REST API endpoints.
Each tool includes a name, description, and parameter schema.
"""

from mcp.types import Tool


def list_screens_tool() -> Tool:
    """Tool definition for listing screens."""
    return Tool(
        name="list_screens",
        description=(
            "List all screens accessible to the authenticated user. "
            "In SaaS mode, returns only the user's screens. "
            "In self-hosted mode, returns all screens. "
            "Supports pagination with page and per_page parameters."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1,
                    "minimum": 1,
                },
                "per_page": {
                    "type": "integer",
                    "description": "Items per page (default: 20, max: 100)",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": [],
        },
    )


def create_screen_tool() -> Tool:
    """Tool definition for creating a new screen."""
    return Tool(
        name="create_screen",
        description=(
            "Create a new display screen. Returns the screen ID and API key. "
            "Optionally provide a template_id to initialize with a template's configuration. "
            "In SaaS mode, the screen is owned by the authenticated user. "
            "In self-hosted mode, screens are created without ownership."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Optional name for the new screen",
                },
                "template_id": {
                    "type": "string",
                    "description": "Optional template ID to initialize screen with template configuration",
                },
            },
            "required": [],
        },
    )


def get_screen_tool() -> Tool:
    """Tool definition for getting screen details."""
    return Tool(
        name="get_screen",
        description=(
            "Get details of a specific screen including its display settings. "
            "Returns screen ID, name, creation time, last update time, and settings."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "screen_id": {
                    "type": "string",
                    "description": "The unique identifier of the screen",
                },
            },
            "required": ["screen_id"],
        },
    )


def update_screen_tool() -> Tool:
    """Tool definition for updating a screen."""
    return Tool(
        name="update_screen",
        description=(
            "Update a screen's properties including name, theme, rotation settings, "
            "and styling (colors, fonts, layout). Requires the screen's API key. "
            "You can apply a theme and override specific values in the same request."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "screen_id": {
                    "type": "string",
                    "description": "The unique identifier of the screen",
                },
                "api_key": {
                    "type": "string",
                    "description": "The screen's API key (sk_xxx) for authentication",
                },
                "name": {
                    "type": "string",
                    "description": "Human-readable screen name",
                },
                "theme": {
                    "type": "string",
                    "description": "Apply a theme by name (e.g., 'catppuccin-mocha', 'nord', 'dracula')",
                },
                "rotation_enabled": {
                    "type": "boolean",
                    "description": "Enable/disable page rotation",
                },
                "rotation_interval": {
                    "type": "integer",
                    "description": "Seconds between page transitions",
                    "minimum": 1,
                },
                "gap": {
                    "type": "string",
                    "description": "Gap between panels (CSS length, e.g., '1rem', '16px')",
                },
                "border_radius": {
                    "type": "string",
                    "description": "Panel corner rounding (CSS length)",
                },
                "panel_shadow": {
                    "type": "string",
                    "description": "Panel shadow (CSS box-shadow)",
                },
                "background_color": {
                    "type": "string",
                    "description": "Screen background (CSS color/gradient)",
                },
                "panel_color": {
                    "type": "string",
                    "description": "Default panel background (CSS color)",
                },
                "font_family": {
                    "type": "string",
                    "description": "Default font (CSS font-family)",
                },
                "font_color": {
                    "type": "string",
                    "description": "Default text color (CSS color)",
                },
                "default_layout": {
                    "type": "string",
                    "description": "Default layout preset for all pages (e.g., 'vertical', 'grid-2x2')",
                },
                "transition": {
                    "type": "string",
                    "description": "Transition effect between pages ('none', 'fade', 'slide-left')",
                    "enum": ["none", "fade", "slide-left"],
                },
                "transition_duration": {
                    "type": "integer",
                    "description": "Transition duration in milliseconds",
                    "minimum": 0,
                    "maximum": 5000,
                },
            },
            "required": ["screen_id", "api_key"],
        },
    )


def delete_screen_tool() -> Tool:
    """Tool definition for deleting a screen."""
    return Tool(
        name="delete_screen",
        description=(
            "Delete a screen and all its pages. This action is irreversible. "
            "Requires the screen's API key for authentication."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "screen_id": {
                    "type": "string",
                    "description": "The unique identifier of the screen to delete",
                },
                "api_key": {
                    "type": "string",
                    "description": "The screen's API key (sk_xxx) for authentication",
                },
            },
            "required": ["screen_id", "api_key"],
        },
    )


def send_message_tool() -> Tool:
    """Tool definition for sending a message to a screen."""
    return Tool(
        name="send_message",
        description=(
            "Send content to a screen's default page. Content can be text, markdown, "
            "images, or videos. Strings are auto-detected: URLs ending in image/video "
            "extensions become media, text starting with # becomes markdown. "
            "Use structured content items for explicit control over content type and styling."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "screen_id": {
                    "type": "string",
                    "description": "The unique identifier of the screen",
                },
                "api_key": {
                    "type": "string",
                    "description": "The screen's API key (sk_xxx) for authentication",
                },
                "content": {
                    "type": "array",
                    "description": (
                        "Array of content items. Strings are auto-detected. "
                        "Use objects for explicit control: "
                        "{type: 'text'|'markdown'|'image'|'video', value: '...', url: '...'}. "
                        "For widgets: {type: 'widget', value: 'analog-clock'|'digital-clock'|'countdown', timezone: 'America/New_York'}"
                    ),
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["text", "markdown", "image", "video", "widget"],
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "Content value. For widgets, this is the widget type (analog-clock, digital-clock, countdown)",
                                    },
                                    "url": {"type": "string"},
                                    "timezone": {
                                        "type": "string",
                                        "description": "Timezone for clock widgets (e.g., 'America/New_York', 'Europe/London')",
                                    },
                                    "panel_color": {"type": "string"},
                                    "font_color": {"type": "string"},
                                    "font_family": {"type": "string"},
                                },
                            },
                        ]
                    },
                },
                "layout": {
                    "type": "string",
                    "description": "Layout preset name (e.g., 'vertical', 'grid-2x2', 'dashboard-header')",
                },
                "background_color": {
                    "type": "string",
                    "description": "Screen background color (CSS color or gradient)",
                },
                "panel_color": {
                    "type": "string",
                    "description": "Default panel background color",
                },
                "font_family": {
                    "type": "string",
                    "description": "Default font family (CSS font-family)",
                },
                "font_color": {
                    "type": "string",
                    "description": "Default text color",
                },
                "gap": {
                    "type": "string",
                    "description": "Gap between panels (CSS length)",
                },
                "border_radius": {
                    "type": "string",
                    "description": "Panel corner rounding (CSS length)",
                },
                "panel_shadow": {
                    "type": "string",
                    "description": "Panel drop shadow (CSS box-shadow)",
                },
            },
            "required": ["screen_id", "api_key", "content"],
        },
    )


def create_page_tool() -> Tool:
    """Tool definition for creating or updating a page."""
    return Tool(
        name="create_page",
        description=(
            "Create or update a named page on a screen. Pages are used for rotation/carousel. "
            "Each page can have its own content, layout, and styling. "
            "The 'default' page is the main page shown when rotation is disabled."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "screen_id": {
                    "type": "string",
                    "description": "The unique identifier of the screen",
                },
                "page_name": {
                    "type": "string",
                    "description": "Name of the page (e.g., 'welcome', 'stats', 'alerts')",
                },
                "api_key": {
                    "type": "string",
                    "description": "The screen's API key (sk_xxx) for authentication",
                },
                "content": {
                    "type": "array",
                    "description": "Array of content items for this page",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["text", "markdown", "image", "video", "widget"],
                                    },
                                    "value": {"type": "string"},
                                    "url": {"type": "string"},
                                },
                            },
                        ]
                    },
                },
                "layout": {
                    "type": "string",
                    "description": "Layout preset name or configuration for this page",
                },
                "duration": {
                    "type": "integer",
                    "description": "How long to display this page in seconds (overrides screen default)",
                    "minimum": 1,
                },
                "background_color": {
                    "type": "string",
                    "description": "Page-specific background color override",
                },
                "panel_color": {
                    "type": "string",
                    "description": "Page-specific panel color override",
                },
                "font_family": {
                    "type": "string",
                    "description": "Page-specific font family override",
                },
                "font_color": {
                    "type": "string",
                    "description": "Page-specific text color override",
                },
                "gap": {
                    "type": "string",
                    "description": "Page-specific gap override",
                },
                "border_radius": {
                    "type": "string",
                    "description": "Page-specific border radius override",
                },
                "panel_shadow": {
                    "type": "string",
                    "description": "Page-specific shadow override",
                },
                "transition": {
                    "type": "string",
                    "description": "Transition effect when entering this page",
                    "enum": ["none", "fade", "slide-left"],
                },
                "transition_duration": {
                    "type": "integer",
                    "description": "Transition duration in milliseconds",
                    "minimum": 0,
                    "maximum": 5000,
                },
            },
            "required": ["screen_id", "page_name", "api_key", "content"],
        },
    )


def list_layouts_tool() -> Tool:
    """Tool definition for listing available layouts."""
    return Tool(
        name="list_layouts",
        description=(
            "List all available layout presets. Layouts control how content panels "
            "are arranged on the screen. Returns preset names, descriptions, and "
            "configuration details."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    )
