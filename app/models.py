from pydantic import BaseModel
from typing import Union


class ContentItem(BaseModel):
    type: str  # "text", "image", "markdown", "video"
    value: str | None = None
    url: str | None = None
    color: str | None = None  # Per-panel background color override
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


class ScreenResponse(BaseModel):
    screen_id: str
    api_key: str
    screen_url: str
    api_url: str


class MessageResponse(BaseModel):
    success: bool
    viewers: int
