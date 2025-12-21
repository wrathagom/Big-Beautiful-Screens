from pydantic import BaseModel
from typing import Union
from datetime import datetime


class ContentItem(BaseModel):
    type: str  # "text", "image", "markdown", "video"
    value: str | None = None
    url: str | None = None
    panel_color: str | None = None  # Per-panel background color override
    font_family: str | None = None  # Per-panel font override
    font_color: str | None = None  # Per-panel text color override
    image_mode: str | None = None  # contain, cover, cover-width, cover-height
    autoplay: bool | None = None  # Video autoplay (default True)
    loop: bool | None = None  # Video loop (default True)
    muted: bool | None = None  # Video muted (default True)
    wrap: bool | None = None  # Text wrapping (default True for text, allows larger text)


class MessageRequest(BaseModel):
    content: list[Union[str, ContentItem]]
    background_color: str | None = None  # Screen background color
    panel_color: str | None = None  # Default panel background color
    font_family: str | None = None  # Default font family
    font_color: str | None = None  # Default text color
    gap: str | None = None  # Gap between panels (CSS value, e.g., "1rem", "10px", "0")
    border_radius: str | None = None  # Panel corner rounding (CSS value, e.g., "1rem", "0")
    panel_shadow: str | None = None  # CSS box-shadow for panels (e.g., "0 4px 12px rgba(0,0,0,0.3)")


class PageRequest(BaseModel):
    """Request to create/update a specific page."""
    content: list[Union[str, ContentItem]]
    background_color: str | None = None
    panel_color: str | None = None
    font_family: str | None = None
    font_color: str | None = None
    gap: str | None = None  # Gap between panels (overrides screen default)
    border_radius: str | None = None  # Panel corner rounding (overrides screen default)
    panel_shadow: str | None = None  # Panel shadow (overrides screen default)
    duration: int | None = None  # Per-page duration override in seconds
    expires_at: datetime | None = None  # Expiration time for ephemeral pages


class PageUpdateRequest(BaseModel):
    """Request to partially update a page (all fields optional)."""
    content: list[Union[str, ContentItem]] | None = None
    background_color: str | None = None
    panel_color: str | None = None
    font_family: str | None = None
    font_color: str | None = None
    gap: str | None = None
    border_radius: str | None = None
    panel_shadow: str | None = None
    duration: int | None = None
    expires_at: datetime | None = None


class RotationSettings(BaseModel):
    """Screen rotation settings."""
    enabled: bool
    interval: int  # seconds


class ScreenUpdateRequest(BaseModel):
    """Request to update screen settings."""
    name: str | None = None
    theme: str | None = None  # Apply a pre-defined theme (values can be overridden below)
    rotation_enabled: bool | None = None
    rotation_interval: int | None = None
    gap: str | None = None
    border_radius: str | None = None
    panel_shadow: str | None = None
    background_color: str | None = None
    panel_color: str | None = None
    font_family: str | None = None
    font_color: str | None = None
    head_html: str | None = None  # Custom HTML for <head> (e.g., Google Fonts links)


class PageOrderRequest(BaseModel):
    """Request to reorder pages."""
    page_names: list[str]


class ScreenResponse(BaseModel):
    screen_id: str
    api_key: str
    screen_url: str
    api_url: str


class MessageResponse(BaseModel):
    success: bool
    viewers: int


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
    """Request to create a new theme."""
    name: str  # URL-safe identifier (e.g., "my-custom-theme")
    display_name: str | None = None  # Human-readable name
    background_color: str
    panel_color: str
    font_family: str = "system-ui, -apple-system, sans-serif"
    font_color: str
    gap: str = "1rem"
    border_radius: str = "1rem"
    panel_shadow: str | None = None


class ThemeUpdate(BaseModel):
    """Request to update a theme. All fields optional for partial updates."""
    display_name: str | None = None
    background_color: str | None = None
    panel_color: str | None = None
    font_family: str | None = None
    font_color: str | None = None
    gap: str | None = None
    border_radius: str | None = None
    panel_shadow: str | None = None


class ThemeResponse(BaseModel):
    """Response for theme operations."""
    name: str
    display_name: str | None
    background_color: str
    panel_color: str
    font_family: str
    font_color: str
    gap: str
    border_radius: str
    panel_shadow: str | None
    is_builtin: bool
