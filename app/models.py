from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """Structured content item with explicit type and styling options."""

    type: Literal["text", "markdown", "image", "video", "widget"] = Field(
        description="Content type: 'text' for plain text, 'markdown' for formatted text, "
        "'image' for images, 'video' for video files, 'widget' for interactive widgets"
    )
    value: str | None = Field(
        default=None,
        description="Content value for text/markdown types",
        examples=["Hello, World!", "# Heading\n\nParagraph with **bold** text"],
    )
    url: str | None = Field(
        default=None,
        description="URL for image/video types",
        examples=["https://example.com/image.png", "https://example.com/video.mp4"],
    )
    panel_color: str | None = Field(
        default=None,
        description="Override panel background color for this item (CSS color)",
        examples=[
            "#ff6b6b",
            "rgba(255, 107, 107, 0.8)",
            "linear-gradient(135deg, #667eea, #764ba2)",
        ],
    )
    panel_shadow: str | None = Field(
        default=None,
        description="Override panel shadow for this item. Use 'none' to disable shadow.",
        examples=["none", "0 4px 12px rgba(0,0,0,0.3)"],
    )
    font_family: str | None = Field(
        default=None,
        description="Override font family for this item",
        examples=["'Roboto Mono', monospace", "Georgia, serif"],
    )
    font_color: str | None = Field(
        default=None,
        description="Override text color for this item (CSS color)",
        examples=["#ffffff", "rgb(255, 255, 255)"],
    )
    image_mode: Literal["contain", "cover", "cover-width", "cover-height"] | None = Field(
        default=None,
        description="How images fill the panel: 'contain' (fit inside), 'cover' (fill and crop), "
        "'cover-width' (fill width), 'cover-height' (fill height)",
    )
    autoplay: bool | None = Field(default=None, description="Auto-play video (default: true)")
    loop: bool | None = Field(default=None, description="Loop video playback (default: true)")
    muted: bool | None = Field(default=None, description="Mute video audio (default: true)")
    wrap: bool | None = Field(
        default=None,
        description="Enable text wrapping. When false, text auto-sizes to fit without wrapping "
        "(default: true for text, allows larger display)",
    )
    widget_type: str | None = Field(
        default=None,
        description="Widget type for type='widget': 'clock', 'countdown', 'chart'",
        examples=["clock", "countdown", "chart"],
    )
    widget_config: dict | None = Field(
        default=None,
        description="Widget-specific configuration. See widget documentation for options.",
        examples=[
            {"style": "digital", "timezone": "America/New_York", "format": "12h"},
            {"target": "2025-01-01T00:00:00Z", "expired_text": "Happy New Year!"},
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"type": "text", "value": "Hello, World!"},
                {"type": "markdown", "value": "# Title\n\n**Bold** and *italic*"},
                {"type": "image", "url": "https://example.com/photo.jpg", "image_mode": "cover"},
                {
                    "type": "video",
                    "url": "https://example.com/clip.mp4",
                    "autoplay": True,
                    "loop": True,
                },
                {
                    "type": "text",
                    "value": "No shadow",
                    "panel_color": "transparent",
                    "panel_shadow": "none",
                },
                {
                    "type": "widget",
                    "widget_type": "clock",
                    "widget_config": {"style": "digital", "timezone": "local", "format": "12h"},
                },
            ]
        }
    }


class MessageRequest(BaseModel):
    """Send content to a screen. Content can be simple strings (auto-detected) or structured ContentItems."""

    content: list[str | ContentItem] = Field(
        description="Array of content items. Strings are auto-detected as text/markdown/image/video. "
        "Use ContentItem objects for explicit control.",
        examples=[
            ["Hello, World!", "https://example.com/image.png"],
            [{"type": "text", "value": "Custom panel", "panel_color": "#ff6b6b"}],
        ],
    )
    background_color: str | None = Field(
        default=None,
        description="Screen background color (CSS color or gradient)",
        examples=["#1e1e2e", "linear-gradient(135deg, #1a1a2e, #16213e)"],
    )
    panel_color: str | None = Field(
        default=None,
        description="Default panel background color",
        examples=["#313244", "rgba(49, 50, 68, 0.9)"],
    )
    font_family: str | None = Field(
        default=None,
        description="Default font family (CSS font-family)",
        examples=["system-ui, sans-serif", "'Inter', 'Helvetica Neue', sans-serif"],
    )
    font_color: str | None = Field(
        default=None,
        description="Default text color",
        examples=["#cdd6f4", "#ffffff"],
    )
    gap: str | None = Field(
        default=None,
        description="Gap between panels (CSS length)",
        examples=["1rem", "16px", "0"],
    )
    border_radius: str | None = Field(
        default=None,
        description="Panel corner rounding (CSS length)",
        examples=["1rem", "8px", "0"],
    )
    panel_shadow: str | None = Field(
        default=None,
        description="Panel drop shadow (CSS box-shadow)",
        examples=["0 4px 12px rgba(0,0,0,0.3)", "none"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "content": [
                    "# Dashboard",
                    "Current status: **Online**",
                    "https://example.com/chart.png",
                ],
                "background_color": "#1e1e2e",
                "panel_color": "#313244",
                "font_color": "#cdd6f4",
            }
        }
    }


class PageRequest(BaseModel):
    """Create or update a named page for rotation."""

    content: list[str | ContentItem] = Field(description="Array of content items for this page")
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
    duration: int | None = Field(
        default=None,
        description="How long to display this page in seconds (overrides screen default)",
        examples=[10, 30, 60],
        ge=1,
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Auto-delete this page after this time (ISO 8601 format). "
        "Useful for temporary alerts.",
        examples=["2024-12-31T23:59:59Z"],
    )


class PageUpdateRequest(BaseModel):
    """Partially update a page. Only provided fields are modified."""

    content: list[str | ContentItem] | None = Field(
        default=None, description="New content (replaces existing)"
    )
    background_color: str | None = Field(default=None, description="Background color")
    panel_color: str | None = Field(default=None, description="Panel color")
    font_family: str | None = Field(default=None, description="Font family")
    font_color: str | None = Field(default=None, description="Text color")
    gap: str | None = Field(default=None, description="Gap between panels")
    border_radius: str | None = Field(default=None, description="Corner rounding")
    panel_shadow: str | None = Field(default=None, description="Panel shadow")
    duration: int | None = Field(default=None, description="Display duration in seconds", ge=1)
    expires_at: datetime | None = Field(default=None, description="Expiration time")


class RotationSettings(BaseModel):
    """Screen rotation/carousel settings."""

    enabled: bool = Field(description="Whether page rotation is enabled")
    interval: int = Field(description="Seconds between page transitions", ge=1)


class ScreenUpdateRequest(BaseModel):
    """Update screen settings. Apply a theme and/or override specific values."""

    name: str | None = Field(
        default=None,
        description="Human-readable screen name",
        examples=["Living Room Display", "Office Dashboard"],
    )
    theme: str | None = Field(
        default=None,
        description="Apply a theme by name. Theme values can be overridden by other fields.",
        examples=["catppuccin-mocha", "nord", "dracula"],
    )
    rotation_enabled: bool | None = Field(default=None, description="Enable/disable page rotation")
    rotation_interval: int | None = Field(
        default=None, description="Seconds between page transitions", ge=1
    )
    gap: str | None = Field(default=None, description="Gap between panels (CSS length)")
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
    head_html: str | None = Field(
        default=None,
        description="Custom HTML injected into <head>. Useful for loading Google Fonts.",
        examples=[
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet">'
        ],
    )


class PageOrderRequest(BaseModel):
    """Reorder pages by specifying the desired order."""

    page_names: list[str] = Field(
        description="Page names in desired display order",
        examples=[["welcome", "stats", "alerts", "default"]],
    )


class ScreenResponse(BaseModel):
    """Response when creating a new screen."""

    screen_id: str = Field(description="Unique screen identifier")
    api_key: str = Field(description="API key for authenticating updates (keep secret!)")
    screen_url: str = Field(
        description="URL to view this screen", examples=["/screen/abc123def456"]
    )
    api_url: str = Field(
        description="API endpoint for sending messages",
        examples=["/api/screens/abc123def456/message"],
    )


class MessageResponse(BaseModel):
    """Response after sending a message."""

    success: bool = Field(description="Whether the operation succeeded")
    viewers: int = Field(description="Number of connected viewers who received the update")


class PageResponse(BaseModel):
    """Response for page operations."""

    success: bool
    page: dict | None = None
    viewers: int = 0


class PagesListResponse(BaseModel):
    """Response for listing all pages."""

    pages: list[dict]
    rotation: RotationSettings


# ============== Theme Models ==============


class ThemeCreate(BaseModel):
    """Create a new color theme."""

    name: str = Field(
        description="URL-safe identifier (lowercase, hyphens, underscores)",
        examples=["my-dark-theme", "corporate_blue"],
        pattern=r"^[a-z0-9_-]+$",
    )
    display_name: str | None = Field(
        default=None,
        description="Human-readable name",
        examples=["My Dark Theme", "Corporate Blue"],
    )
    background_color: str = Field(
        description="Screen background color",
        examples=["#1e1e2e", "linear-gradient(135deg, #0f0f23, #1a1a2e)"],
    )
    panel_color: str = Field(
        description="Panel background color",
        examples=["#313244", "rgba(49, 50, 68, 0.95)"],
    )
    font_family: str = Field(
        default="system-ui, -apple-system, sans-serif",
        description="Font family stack",
    )
    font_color: str = Field(
        description="Text color",
        examples=["#cdd6f4", "#ffffff"],
    )
    gap: str = Field(default="1rem", description="Gap between panels")
    border_radius: str = Field(default="1rem", description="Panel corner rounding")
    panel_shadow: str | None = Field(
        default=None,
        description="Panel shadow",
        examples=["0 4px 12px rgba(0,0,0,0.3)"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "midnight-blue",
                "display_name": "Midnight Blue",
                "background_color": "#0d1b2a",
                "panel_color": "#1b263b",
                "font_color": "#e0e1dd",
                "gap": "1rem",
                "border_radius": "0.75rem",
            }
        }
    }


class ThemeUpdate(BaseModel):
    """Update a theme. All fields optional for partial updates."""

    display_name: str | None = Field(default=None, description="Human-readable name")
    background_color: str | None = Field(default=None, description="Screen background")
    panel_color: str | None = Field(default=None, description="Panel background")
    font_family: str | None = Field(default=None, description="Font family")
    font_color: str | None = Field(default=None, description="Text color")
    gap: str | None = Field(default=None, description="Gap between panels")
    border_radius: str | None = Field(default=None, description="Corner rounding")
    panel_shadow: str | None = Field(default=None, description="Panel shadow")


class ThemeResponse(BaseModel):
    """Theme details."""

    name: str = Field(description="Theme identifier")
    display_name: str | None = Field(description="Human-readable name")
    background_color: str = Field(description="Screen background color")
    panel_color: str = Field(description="Panel background color")
    font_family: str = Field(description="Font family")
    font_color: str = Field(description="Text color")
    gap: str = Field(description="Gap between panels")
    border_radius: str = Field(description="Corner rounding")
    panel_shadow: str | None = Field(description="Panel shadow")
    is_builtin: bool = Field(description="Whether this is a built-in theme")
