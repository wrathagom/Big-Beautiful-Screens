"""Pydantic models for MCP tool arguments.

These exist to avoid duplicating JSON Schema by hand in `app/mcp/tools.py`.
They are intentionally small wrappers around the app's existing request models,
adding MCP-specific fields like `screen_id` and `api_key` that are path/header
params in the REST API.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ..models import ContentItem, LayoutConfig


class ListScreensArgs(BaseModel):
    page: int = Field(default=1, description="Page number (default: 1)", ge=1)
    per_page: int = Field(
        default=20, description="Items per page (default: 20, max: 100)", ge=1, le=100
    )


class CreateScreenArgs(BaseModel):
    name: str | None = Field(default=None, description="Optional name for the new screen")
    template_id: str | None = Field(
        default=None,
        description="Optional template ID to initialize screen with template configuration",
    )


class GetScreenArgs(BaseModel):
    screen_id: str = Field(description="The unique identifier of the screen")


class UpdateScreenArgs(BaseModel):
    screen_id: str = Field(description="The unique identifier of the screen")
    api_key: str = Field(description="The screen's API key (sk_xxx) for authentication")

    name: str | None = Field(default=None, description="Human-readable screen name")
    theme: str | None = Field(
        default=None,
        description="Apply a theme by name (e.g., 'catppuccin-mocha', 'nord', 'dracula')",
    )
    rotation_enabled: bool | None = Field(default=None, description="Enable/disable page rotation")
    rotation_interval: int | None = Field(
        default=None, description="Seconds between page transitions", ge=1
    )
    gap: str | None = Field(
        default=None, description="Gap between panels (CSS length, e.g., '1rem')"
    )
    border_radius: str | None = Field(
        default=None, description="Panel corner rounding (CSS length)"
    )
    panel_shadow: str | None = Field(default=None, description="Panel shadow (CSS box-shadow)")
    background_color: str | None = Field(
        default=None, description="Screen background (CSS color/gradient)"
    )
    panel_color: str | None = Field(
        default=None, description="Default panel background (CSS color)"
    )
    font_family: str | None = Field(default=None, description="Default font (CSS font-family)")
    font_color: str | None = Field(default=None, description="Default text color (CSS color)")
    default_layout: str | LayoutConfig | None = Field(
        default=None,
        description="Default layout preset for all pages (e.g., 'vertical', 'grid-2x2')",
    )
    transition: Literal["none", "fade", "slide-left"] | None = Field(
        default=None,
        description="Transition effect between pages ('none', 'fade', 'slide-left')",
    )
    transition_duration: int | None = Field(
        default=None, description="Transition duration in milliseconds", ge=0, le=5000
    )


class DeleteScreenArgs(BaseModel):
    screen_id: str = Field(description="The unique identifier of the screen to delete")
    api_key: str = Field(description="The screen's API key (sk_xxx) for authentication")


class SendMessageArgs(BaseModel):
    screen_id: str = Field(description="The unique identifier of the screen")
    api_key: str = Field(description="The screen's API key (sk_xxx) for authentication")

    content: Annotated[
        list[str | ContentItem],
        Field(
            description=(
                "Array of content items. Strings are auto-detected. Use objects for explicit "
                "control (ContentItem)."
            ),
            min_length=1,
        ),
    ]

    layout: str | LayoutConfig | None = Field(
        default=None,
        description="Layout preset name (str) or configuration (object).",
    )
    background_color: str | None = Field(
        default=None, description="Screen background color (CSS color or gradient)"
    )
    panel_color: str | None = Field(default=None, description="Default panel background color")
    font_family: str | None = Field(
        default=None, description="Default font family (CSS font-family)"
    )
    font_color: str | None = Field(default=None, description="Default text color")
    gap: str | None = Field(default=None, description="Gap between panels (CSS length)")
    border_radius: str | None = Field(
        default=None, description="Panel corner rounding (CSS length)"
    )
    panel_shadow: str | None = Field(default=None, description="Panel drop shadow (CSS box-shadow)")


class CreatePageArgs(BaseModel):
    screen_id: str = Field(description="The unique identifier of the screen")
    page_name: str = Field(description="Name of the page (e.g., 'welcome', 'stats', 'alerts')")
    api_key: str = Field(description="The screen's API key (sk_xxx) for authentication")

    content: Annotated[
        list[str | ContentItem],
        Field(description="Array of content items for this page", min_length=1),
    ]

    layout: str | LayoutConfig | None = Field(
        default=None, description="Layout preset name or configuration for this page"
    )
    duration: int | None = Field(
        default=None,
        description="How long to display this page in seconds (overrides screen default)",
        ge=1,
    )
    background_color: str | None = Field(
        default=None, description="Page-specific background color override"
    )
    panel_color: str | None = Field(default=None, description="Page-specific panel color override")
    font_family: str | None = Field(default=None, description="Page-specific font family override")
    font_color: str | None = Field(default=None, description="Page-specific text color override")
    gap: str | None = Field(default=None, description="Page-specific gap override")
    border_radius: str | None = Field(
        default=None, description="Page-specific border radius override"
    )
    panel_shadow: str | None = Field(default=None, description="Page-specific shadow override")
    transition: Literal["none", "fade", "slide-left"] | None = Field(
        default=None, description="Transition effect when entering this page"
    )
    transition_duration: int | None = Field(
        default=None, description="Transition duration in milliseconds", ge=0, le=5000
    )


class ListLayoutsArgs(BaseModel):
    """No arguments."""
