"""Utility functions for content processing and theme resolution."""

import html
from html.parser import HTMLParser
from urllib.parse import urlparse

from .database import get_theme_from_db

_ALLOWED_HEAD_REL = {"stylesheet", "preconnect"}
_ALLOWED_HEAD_ATTRS = ("rel", "href", "crossorigin", "referrerpolicy", "as", "type", "media")


def _is_allowed_head_href(href: str) -> bool:
    if href.startswith("/static/"):
        return True
    parsed = urlparse(href)
    return parsed.scheme == "https" or (
        parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
    )


class _HeadHtmlSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "link":
            return

        attr_dict = {key.lower(): value for key, value in attrs if value is not None}
        rel_value = attr_dict.get("rel", "").lower()
        rel_tokens = {token for token in rel_value.split() if token}
        rel = next((token for token in _ALLOWED_HEAD_REL if token in rel_tokens), None)
        href = attr_dict.get("href", "")

        if not rel or not href or not _is_allowed_head_href(href):
            return

        filtered_attrs = []
        for key in _ALLOWED_HEAD_ATTRS:
            value = attr_dict.get(key)
            if value and key != "rel":
                filtered_attrs.append((key, value))

        filtered_attrs.insert(0, ("rel", rel))
        attr_str = " ".join(
            f'{key}="{html.escape(value, quote=True)}"' for key, value in filtered_attrs
        )
        self.links.append(f"<link {attr_str}>")


def sanitize_head_html(raw_html: str | None) -> str | None:
    """Allow only safe <link> tags for fonts/styles in head HTML."""
    if raw_html is None:
        return None
    sanitizer = _HeadHtmlSanitizer()
    sanitizer.feed(raw_html)
    sanitized = "\n".join(sanitizer.links)
    return sanitized


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
            elif item.type == "widget":
                entry = {
                    "type": "widget",
                    "widget_type": item.widget_type,
                    "widget_config": item.widget_config or {},
                }
            else:
                entry = {"type": item.type, "value": item.value}

            # Preserve per-panel styling if specified
            if item.panel_color:
                entry["panel_color"] = item.panel_color
            if item.panel_shadow is not None:
                entry["panel_shadow"] = item.panel_shadow
            if item.font_family:
                entry["font_family"] = item.font_family
            if item.font_color:
                entry["font_color"] = item.font_color
            if item.image_mode:
                entry["image_mode"] = item.image_mode
            if item.wrap is not None:
                entry["wrap"] = item.wrap
            if item.grid_column:
                entry["grid_column"] = item.grid_column
            if item.grid_row:
                entry["grid_row"] = item.grid_row

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


# ============== Template Serialization ==============


def serialize_screen_to_template(screen: dict, pages: list[dict]) -> dict:
    """Serialize a screen and its pages into a template-safe configuration.

    Extracts all screen settings, layout, and page content while excluding
    sensitive fields like id, api_key, owner_id, and org_id.

    Args:
        screen: Screen record from database (full dict from get_screen_by_id)
        pages: List of page dicts from get_all_pages

    Returns:
        Template configuration dict suitable for storing in templates.configuration
    """
    # Screen display settings to include
    config = {}

    # Style settings
    style_fields = [
        "background_color",
        "panel_color",
        "font_family",
        "font_color",
        "gap",
        "border_radius",
        "panel_shadow",
    ]
    for field in style_fields:
        if screen.get(field) is not None:
            config[field] = screen[field]

    # Theme reference
    if screen.get("theme"):
        config["theme"] = screen["theme"]

    # Custom head HTML (for fonts, etc.)
    if screen.get("head_html"):
        config["head_html"] = screen["head_html"]

    # Default layout
    if screen.get("default_layout"):
        config["default_layout"] = screen["default_layout"]

    # Rotation/carousel settings
    config["rotation_enabled"] = bool(screen.get("rotation_enabled", False))
    config["rotation_interval"] = screen.get("rotation_interval", 30)

    # Transition settings
    config["transition"] = screen.get("transition", "none")
    config["transition_duration"] = screen.get("transition_duration", 500)

    # Debug mode (useful for some templates)
    if screen.get("debug_enabled"):
        config["debug_enabled"] = True

    # Serialize pages
    config["pages"] = []
    for page in pages:
        page_config = _serialize_page(page)
        config["pages"].append(page_config)

    return config


def _serialize_page(page: dict) -> dict:
    """Serialize a single page for template storage.

    Excludes: id, screen_id, created_at, updated_at, expires_at
    Includes: name, content, layout, styling, duration, display_order
    """
    page_config = {
        "name": page["name"],
        "content": page.get("content", []),
        "display_order": page.get("display_order", 0),
    }

    # Layout (can be string preset or dict)
    if page.get("layout"):
        page_config["layout"] = page["layout"]

    # Page-level style overrides
    style_fields = [
        "background_color",
        "panel_color",
        "font_family",
        "font_color",
        "gap",
        "border_radius",
        "panel_shadow",
    ]
    for field in style_fields:
        if page.get(field) is not None:
            page_config[field] = page[field]

    # Page-level transition overrides
    if page.get("transition") is not None:
        page_config["transition"] = page["transition"]
    if page.get("transition_duration") is not None:
        page_config["transition_duration"] = page["transition_duration"]

    # Duration (how long to show this page during rotation)
    if page.get("duration") is not None:
        page_config["duration"] = page["duration"]

    # Note: expires_at is intentionally excluded - templates shouldn't auto-expire

    return page_config


def deserialize_template_to_screen_config(template_config: dict) -> tuple[dict, list[dict]]:
    """Convert template configuration back to screen settings and pages.

    This prepares the data for creating a new screen from a template.

    Args:
        template_config: The configuration dict from a template

    Returns:
        Tuple of (screen_settings, pages) where:
        - screen_settings: dict of settings to apply to a new screen
        - pages: list of page dicts ready for upsert_page
    """
    # Extract screen-level settings
    screen_settings = {}

    # Style settings
    style_fields = [
        "background_color",
        "panel_color",
        "font_family",
        "font_color",
        "gap",
        "border_radius",
        "panel_shadow",
        "theme",
        "head_html",
        "default_layout",
        "transition",
        "transition_duration",
        "debug_enabled",
    ]
    for field in style_fields:
        if template_config.get(field) is not None:
            value = template_config[field]
            if field == "head_html":
                value = sanitize_head_html(value)
            screen_settings[field] = value

    # Rotation settings (map to screen field names)
    if template_config.get("rotation_enabled") is not None:
        screen_settings["enabled"] = template_config["rotation_enabled"]
    if template_config.get("rotation_interval") is not None:
        screen_settings["interval"] = template_config["rotation_interval"]

    # Extract pages
    pages = []
    for page_config in template_config.get("pages", []):
        page = _deserialize_page(page_config)
        pages.append(page)

    return screen_settings, pages


def _deserialize_page(page_config: dict) -> dict:
    """Convert a template page config to a page dict for upsert_page.

    Returns a dict structured for the upsert_page payload.
    """
    # Build the payload for upsert_page
    payload = {
        "content": page_config.get("content", []),
    }

    # Layout
    if page_config.get("layout"):
        payload["layout"] = page_config["layout"]

    # Style overrides
    style_fields = [
        "background_color",
        "panel_color",
        "font_family",
        "font_color",
        "gap",
        "border_radius",
        "panel_shadow",
    ]
    for field in style_fields:
        if page_config.get(field) is not None:
            payload[field] = page_config[field]

    # Transition overrides
    if page_config.get("transition") is not None:
        payload["transition"] = page_config["transition"]
    if page_config.get("transition_duration") is not None:
        payload["transition_duration"] = page_config["transition_duration"]

    return {
        "name": page_config["name"],
        "payload": payload,
        "duration": page_config.get("duration"),
        "display_order": page_config.get("display_order", 0),
    }


# ============== Thumbnail Generation ==============


def generate_template_thumbnail(configuration: dict) -> str:
    """Generate an SVG thumbnail for a template based on its configuration.

    Creates a simple visual representation showing the layout grid
    with the template's colors.

    Args:
        configuration: Template configuration dict

    Returns:
        Data URL string containing the SVG thumbnail
    """
    import urllib.parse

    # Extract colors with defaults - use simple solid colors for thumbnail
    bg_color = configuration.get("background_color", "#1a1a2e")
    panel_color = configuration.get("panel_color", "#16213e")

    # Simplify complex color values (gradients, rgba) to solid colors for thumbnail
    if bg_color.startswith("linear-gradient") or bg_color.startswith("radial-gradient"):
        bg_color = "#1a1a2e"  # Default dark background
    if bg_color.startswith("rgba"):
        bg_color = "#1a1a2e"
    if panel_color.startswith("rgba"):
        panel_color = "#16213e"

    # Parse gap value - handle CSS units like "1.25rem"
    gap_value = configuration.get("gap", 10)
    gap = _parse_css_number(gap_value, default=10)

    # Parse border radius - handle CSS units
    border_radius_value = configuration.get("border_radius", 8)
    border_radius = _parse_css_number(border_radius_value, default=8)

    # Get layout from first page or default_layout
    layout = configuration.get("default_layout", "1")
    if configuration.get("pages") and len(configuration["pages"]) > 0:
        first_page = configuration["pages"][0]
        layout = first_page.get("layout", layout)

    # SVG dimensions
    width = 200
    height = 150
    padding = 10

    # Parse layout to determine grid
    grid = _parse_layout_to_grid(layout)

    # Generate SVG
    svg = _generate_layout_svg(
        width=width,
        height=height,
        padding=padding,
        gap=gap,
        border_radius=border_radius,
        bg_color=bg_color,
        panel_color=panel_color,
        grid=grid,
    )

    # Convert to data URL
    encoded = urllib.parse.quote(svg)
    return f"data:image/svg+xml,{encoded}"


def _parse_css_number(value, default: int = 0) -> int:
    """Parse a CSS number value, stripping units like rem, px, etc.

    Args:
        value: The value to parse (int, float, or string like "1.25rem")
        default: Default value if parsing fails

    Returns:
        Integer value, scaled appropriately for thumbnail use
    """
    if value is None:
        return default
    if isinstance(value, int | float):
        return int(value)
    if isinstance(value, str):
        # Extract numeric portion
        import re

        match = re.match(r"^([\d.]+)", value.strip())
        if match:
            num = float(match.group(1))
            # Scale rem values (1rem ≈ 16px, scale down for thumbnail)
            if "rem" in value:
                return int(num * 8)  # Scale factor for thumbnail
            elif "em" in value:
                return int(num * 8)
            elif "px" in value:
                return int(num / 2)  # Scale down for thumbnail
            else:
                return int(num)
    return default


def _parse_layout_to_grid(layout) -> list[list[float]]:
    """Parse layout specification into a grid of rows and columns.

    Returns a list of rows, where each row is a list of column widths (as fractions).
    """
    # Handle dict layouts (custom grid)
    if isinstance(layout, dict):
        if "columns" in layout:
            # Single row with specific columns
            cols = layout["columns"]
            if isinstance(cols, list):
                return [cols]
            # Handle string like "1fr 2fr"
            return [_parse_fr_string(cols)]
        if "rows" in layout:
            # Multiple rows
            rows = layout.get("rows", [])
            grid = []
            for row in rows:
                if isinstance(row, dict) and "columns" in row:
                    cols = row["columns"]
                    if isinstance(cols, list):
                        grid.append(cols)
                    else:
                        grid.append(_parse_fr_string(cols))
                else:
                    grid.append([1])  # Single column
            return grid if grid else [[1]]
        return [[1]]

    # Handle string layouts (presets)
    layout_str = str(layout)

    # Common preset layouts
    presets = {
        "1": [[1]],
        "2": [[1], [1]],  # 2 rows
        "3": [[1], [1], [1]],  # 3 rows
        "4": [[1, 1], [1, 1]],  # 2x2 grid
        "1-2": [[1], [1, 1]],  # 1 on top, 2 on bottom
        "2-1": [[1, 1], [1]],  # 2 on top, 1 on bottom
        "1-3": [[1], [1, 1, 1]],
        "3-1": [[1, 1, 1], [1]],
        "2-2": [[1, 1], [1, 1]],
        "3-3": [[1, 1, 1], [1, 1, 1]],
        "sidebar": [[1, 2]],  # Sidebar layout
        "sidebar-left": [[1, 3]],
        "sidebar-right": [[3, 1]],
    }

    return presets.get(layout_str, [[1]])


def _parse_fr_string(fr_string: str) -> list[float]:
    """Parse a CSS grid fr string like '1fr 2fr 1fr' into ratios."""
    parts = str(fr_string).split()
    ratios = []
    for part in parts:
        try:
            if part.endswith("fr"):
                ratios.append(float(part[:-2]))
            else:
                ratios.append(float(part))
        except ValueError:
            ratios.append(1)
    return ratios if ratios else [1]


def _generate_layout_svg(
    width: int,
    height: int,
    padding: int,
    gap: int,
    border_radius: int,
    bg_color: str,
    panel_color: str,
    grid: list[list[float]],
) -> str:
    """Generate an SVG string representing the layout grid."""
    # Content area
    content_width = width - (2 * padding)
    content_height = height - (2 * padding)

    # Calculate row heights
    num_rows = len(grid)
    total_gap_height = gap * (num_rows - 1)
    available_height = content_height - total_gap_height
    row_height = available_height / num_rows if num_rows > 0 else available_height

    # Start SVG
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{bg_color}" rx="4"/>',
    ]

    # Draw panels for each row
    y = padding
    for row in grid:
        # Calculate column widths for this row
        num_cols = len(row)
        total_ratio = sum(row)
        total_gap_width = gap * (num_cols - 1)
        available_width = content_width - total_gap_width

        x = padding
        for ratio in row:
            col_width = (
                (ratio / total_ratio) * available_width if total_ratio > 0 else available_width
            )

            # Draw panel rectangle
            svg_parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{col_width:.1f}" height="{row_height:.1f}" '
                f'fill="{panel_color}" rx="{min(border_radius, 4)}"/>'
            )

            x += col_width + gap

        y += row_height + gap

    svg_parts.append("</svg>")
    return "".join(svg_parts)
