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


class PageRequest(BaseModel):
    """Request to create/update a specific page."""
    content: list[Union[str, ContentItem]]
    background_color: str | None = None
    panel_color: str | None = None
    font_family: str | None = None
    font_color: str | None = None
    duration: int | None = None  # Per-page duration override in seconds
    expires_at: datetime | None = None  # Expiration time for ephemeral pages


class RotationSettings(BaseModel):
    """Screen rotation settings."""
    enabled: bool
    interval: int  # seconds


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
