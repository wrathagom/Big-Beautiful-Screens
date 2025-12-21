"""Utility functions for content processing and theme resolution."""

from .database import get_theme_from_db


async def resolve_theme_settings(rotation: dict) -> dict:
    """Resolve theme values and merge with screen-level overrides.

    Theme values are used as defaults; explicit screen values override them.
    """
    if not rotation:
        return rotation

    theme_name = rotation.get("theme")
    if not theme_name:
        return rotation

    # Look up theme from database
    theme = await get_theme_from_db(theme_name)
    if not theme:
        return rotation

    # Merge: screen values override theme values
    resolved = rotation.copy()
    for key in [
        "background_color",
        "panel_color",
        "font_family",
        "font_color",
        "gap",
        "border_radius",
        "panel_shadow",
    ]:
        # Use screen value if set, otherwise use theme value
        if resolved.get(key) is None:
            resolved[key] = theme.get(key)

    return resolved


def normalize_content(content: list) -> list:
    """Normalize content items to structured format with auto-detection."""
    normalized = []

    for item in content:
        if isinstance(item, str):
            normalized.append(detect_content_type(item))
        else:
            # Already structured (ContentItem)
            if item.type == "image":
                entry = {"type": "image", "url": item.url or item.value}
            elif item.type == "video":
                entry = {
                    "type": "video",
                    "url": item.url or item.value,
                    "autoplay": item.autoplay if item.autoplay is not None else True,
                    "loop": item.loop if item.loop is not None else True,
                    "muted": item.muted if item.muted is not None else True,
                }
            else:
                entry = {"type": item.type, "value": item.value}

            # Preserve per-panel styling if specified
            if item.panel_color:
                entry["panel_color"] = item.panel_color
            if item.font_family:
                entry["font_family"] = item.font_family
            if item.font_color:
                entry["font_color"] = item.font_color
            if item.image_mode:
                entry["image_mode"] = item.image_mode
            if item.wrap is not None:
                entry["wrap"] = item.wrap

            normalized.append(entry)

    return normalized


def detect_content_type(text: str) -> dict:
    """Auto-detect content type from a string."""
    text_lower = text.lower()

    # Check if it's a video URL
    video_extensions = (".mp4", ".webm", ".ogg", ".mov")
    if text_lower.startswith("http") and any(text_lower.endswith(ext) for ext in video_extensions):
        return {"type": "video", "url": text, "autoplay": True, "loop": True, "muted": True}

    # Check if it's an image URL
    image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp")
    if text_lower.startswith("http") and any(text_lower.endswith(ext) for ext in image_extensions):
        return {"type": "image", "url": text}

    # Check if it contains markdown syntax
    markdown_indicators = ["# ", "## ", "### ", "**", "__", "```", "- ", "* ", "1. ", "> "]
    if any(indicator in text for indicator in markdown_indicators):
        return {"type": "markdown", "value": text}

    # Default to plain text
    return {"type": "text", "value": text}
