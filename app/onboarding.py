"""Onboarding module for creating demo screens for new users.

This module provides functionality to create a demo screen that showcases
all the features of Big Beautiful Screens when a user first signs up or
on first localhost startup.
"""

import json
import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .database import create_screen, update_rotation_settings, update_screen_name, upsert_page

# Load demo screen config from JSON file
_demo_config_path = Path(__file__).parent / "demo_screen.json"


def _load_demo_config() -> dict:
    """Load demo screen configuration from JSON file."""
    with open(_demo_config_path) as f:
        return json.load(f)


async def create_demo_screen(owner_id: str | None = None) -> dict:
    """Create a demo screen for onboarding purposes.

    Args:
        owner_id: Optional user ID for SaaS mode. None for self-hosted.

    Returns:
        dict with screen_id, api_key, and screen_url
    """
    config = _load_demo_config()

    # Generate screen credentials
    screen_id = uuid.uuid4().hex[:12]
    api_key = f"sk_{secrets.token_urlsafe(24)}"
    created_at = datetime.now(UTC).isoformat()

    # Create the screen in database
    await create_screen(screen_id, api_key, created_at, owner_id=owner_id)

    # Set screen name
    await update_screen_name(screen_id, config.get("name", "Welcome Demo"))

    # Get rotation settings
    rotation_config = config.get("rotation", {})

    # Update rotation settings with styling
    await update_rotation_settings(
        screen_id,
        enabled=rotation_config.get("enabled", False),
        interval=rotation_config.get("interval", 10),
        background_color=config.get("background_color"),
        panel_color=config.get("panel_color"),
        font_color=config.get("font_color"),
        font_family=config.get("font_family"),
        gap=config.get("gap"),
        border_radius=config.get("border_radius"),
    )

    # Create pages
    pages = config.get("pages", [])

    # If no pages defined, fall back to single-page content
    if not pages and "content" in config:
        pages = [{"name": "default", "content": config["content"]}]

    # Create each page
    for page in pages:
        page_name = page.get("name", "default")
        message_payload = {
            "content": page.get("content", []),
            "background_color": config.get("background_color"),
            "panel_color": config.get("panel_color"),
            "font_family": config.get("font_family"),
            "font_color": config.get("font_color"),
            "gap": config.get("gap"),
            "border_radius": config.get("border_radius"),
        }
        await upsert_page(screen_id, page_name, message_payload)

    return {
        "screen_id": screen_id,
        "api_key": api_key,
        "screen_url": f"/screen/{screen_id}",
    }
