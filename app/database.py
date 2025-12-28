"""Database operations for Big Beautiful Screens.

This module provides a compatibility layer for the new database abstraction.
It exposes the same function signatures as before, but delegates to the
appropriate backend (SQLite or PostgreSQL) based on configuration.
"""

from .db import get_database, init_db

# Re-export init_db for startup
__all__ = [
    "init_db",
    "create_screen",
    "get_screen_by_id",
    "get_screen_by_api_key",
    "get_all_screens",
    "get_screens_count",
    "delete_screen",
    "update_screen_name",
    "get_rotation_settings",
    "update_rotation_settings",
    "upsert_page",
    "get_all_pages",
    "get_page",
    "update_page",
    "delete_page",
    "reorder_pages",
    "cleanup_expired_pages",
    "get_all_themes",
    "get_themes_count",
    "get_theme_from_db",
    "create_theme_in_db",
    "update_theme_in_db",
    "delete_theme_from_db",
    "get_theme_usage_counts",
    # Media functions
    "create_media",
    "get_media_by_id",
    "get_all_media",
    "get_media_count",
    "get_storage_used",
    "delete_media",
]


# ============== Screen Functions ==============


async def create_screen(
    screen_id: str,
    api_key: str,
    created_at: str,
    name: str | None = None,
    owner_id: str | None = None,
    org_id: str | None = None,
) -> None:
    """Create a new screen with default theme applied."""
    db = get_database()
    await db.create_screen(screen_id, api_key, created_at, name, owner_id, org_id)


async def get_screen_by_id(screen_id: str) -> dict | None:
    """Get a screen by its ID."""
    db = get_database()
    return await db.get_screen_by_id(screen_id)


async def get_screen_by_api_key(api_key: str) -> dict | None:
    """Get a screen by its API key."""
    db = get_database()
    return await db.get_screen_by_api_key(api_key)


async def get_all_screens(
    limit: int | None = None,
    offset: int = 0,
    owner_id: str | None = None,
    org_id: str | None = None,
) -> list[dict]:
    """Get screens with optional pagination and ownership filtering."""
    db = get_database()
    return await db.get_all_screens(limit, offset, owner_id, org_id)


async def get_screens_count(owner_id: str | None = None, org_id: str | None = None) -> int:
    """Get total count of screens, optionally filtered by owner."""
    db = get_database()
    return await db.get_screens_count(owner_id, org_id)


async def delete_screen(screen_id: str) -> bool:
    """Delete a screen and its pages. Returns True if deleted."""
    db = get_database()
    return await db.delete_screen(screen_id)


async def update_screen_name(screen_id: str, name: str | None) -> bool:
    """Update a screen's name. Returns True if updated."""
    db = get_database()
    return await db.update_screen_name(screen_id, name)


async def get_rotation_settings(screen_id: str) -> dict | None:
    """Get rotation/display settings for a screen."""
    db = get_database()
    return await db.get_rotation_settings(screen_id)


async def update_rotation_settings(
    screen_id: str,
    enabled: bool | None = None,
    interval: int | None = None,
    gap: str | None = None,
    border_radius: str | None = None,
    panel_shadow: str | None = None,
    background_color: str | None = None,
    panel_color: str | None = None,
    font_family: str | None = None,
    font_color: str | None = None,
    theme: str | None = None,
    head_html: str | None = None,
    default_layout: str | dict | None = None,
) -> bool:
    """Update rotation/display settings. Returns True if updated."""
    db = get_database()
    return await db.update_rotation_settings(
        screen_id,
        enabled,
        interval,
        gap,
        border_radius,
        panel_shadow,
        background_color,
        panel_color,
        font_family,
        font_color,
        theme,
        head_html,
        default_layout,
    )


# ============== Page Functions ==============


async def upsert_page(
    screen_id: str,
    name: str,
    payload: dict,
    duration: int | None = None,
    expires_at: str | None = None,
) -> dict:
    """Create or update a page. Returns the page data."""
    db = get_database()
    return await db.upsert_page(screen_id, name, payload, duration, expires_at)


async def get_all_pages(screen_id: str, include_expired: bool = False) -> list[dict]:
    """Get all pages for a screen, ordered by display_order."""
    db = get_database()
    return await db.get_all_pages(screen_id, include_expired)


async def get_page(screen_id: str, name: str) -> dict | None:
    """Get a specific page by name."""
    db = get_database()
    return await db.get_page(screen_id, name)


async def update_page(
    screen_id: str,
    name: str,
    content: list | None = None,
    layout: str | dict | None = None,
    background_color: str | None = None,
    panel_color: str | None = None,
    font_family: str | None = None,
    font_color: str | None = None,
    gap: str | None = None,
    border_radius: str | None = None,
    panel_shadow: str | None = None,
    duration: int | None = None,
    expires_at: str | None = None,
) -> dict | None:
    """Partially update a page. Returns updated data or None."""
    db = get_database()
    return await db.update_page(
        screen_id,
        name,
        content,
        layout,
        background_color,
        panel_color,
        font_family,
        font_color,
        gap,
        border_radius,
        panel_shadow,
        duration,
        expires_at,
    )


async def delete_page(screen_id: str, name: str) -> bool:
    """Delete a page. Cannot delete 'default'. Returns True if deleted."""
    db = get_database()
    return await db.delete_page(screen_id, name)


async def reorder_pages(screen_id: str, page_names: list[str]) -> bool:
    """Reorder pages by setting display_order based on position in list."""
    db = get_database()
    return await db.reorder_pages(screen_id, page_names)


async def cleanup_expired_pages() -> list[tuple[str, str]]:
    """Remove expired pages. Returns list of (screen_id, page_name) deleted."""
    db = get_database()
    return await db.cleanup_expired_pages()


# ============== Theme Functions ==============


async def get_all_themes(
    limit: int | None = None, offset: int = 0, owner_id: str | None = None
) -> list[dict]:
    """Get themes with optional pagination. Includes global + user's themes."""
    db = get_database()
    return await db.get_all_themes(limit, offset, owner_id)


async def get_themes_count(owner_id: str | None = None) -> int:
    """Get total count of themes accessible to a user."""
    db = get_database()
    return await db.get_themes_count(owner_id)


async def get_theme_from_db(name: str) -> dict | None:
    """Get a theme by name."""
    db = get_database()
    return await db.get_theme(name)


async def create_theme_in_db(
    name: str,
    background_color: str,
    panel_color: str,
    font_family: str,
    font_color: str,
    display_name: str | None = None,
    gap: str = "1rem",
    border_radius: str = "1rem",
    panel_shadow: str | None = None,
    owner_id: str | None = None,
) -> dict:
    """Create a new custom theme."""
    db = get_database()
    return await db.create_theme(
        name,
        background_color,
        panel_color,
        font_family,
        font_color,
        display_name,
        gap,
        border_radius,
        panel_shadow,
        owner_id,
    )


async def update_theme_in_db(
    name: str,
    display_name: str | None = None,
    background_color: str | None = None,
    panel_color: str | None = None,
    font_family: str | None = None,
    font_color: str | None = None,
    gap: str | None = None,
    border_radius: str | None = None,
    panel_shadow: str | None = None,
) -> dict | None:
    """Update a theme. Returns None if not found."""
    db = get_database()
    return await db.update_theme(
        name,
        display_name,
        background_color,
        panel_color,
        font_family,
        font_color,
        gap,
        border_radius,
        panel_shadow,
    )


async def delete_theme_from_db(name: str) -> tuple[bool, str | None]:
    """Delete a theme if not in use. Returns (success, error_message)."""
    db = get_database()
    return await db.delete_theme(name)


async def get_theme_usage_counts() -> dict[str, int]:
    """Get usage count for all themes."""
    db = get_database()
    return await db.get_theme_usage_counts()


# ============== Media Functions ==============


async def create_media(
    media_id: str,
    filename: str,
    original_filename: str,
    content_type: str,
    size_bytes: int,
    storage_path: str,
    storage_backend: str,
    owner_id: str | None = None,
    org_id: str | None = None,
) -> dict:
    """Create a media record."""
    db = get_database()
    return await db.create_media(
        media_id,
        filename,
        original_filename,
        content_type,
        size_bytes,
        storage_path,
        storage_backend,
        owner_id,
        org_id,
    )


async def get_media_by_id(media_id: str) -> dict | None:
    """Get a media record by ID."""
    db = get_database()
    return await db.get_media_by_id(media_id)


async def get_all_media(
    limit: int | None = None,
    offset: int = 0,
    owner_id: str | None = None,
    org_id: str | None = None,
    content_type_filter: str | None = None,
) -> list[dict]:
    """Get media with optional pagination and filtering."""
    db = get_database()
    return await db.get_all_media(limit, offset, owner_id, org_id, content_type_filter)


async def get_media_count(
    owner_id: str | None = None,
    org_id: str | None = None,
) -> int:
    """Get total count of media records."""
    db = get_database()
    return await db.get_media_count(owner_id, org_id)


async def get_storage_used(
    owner_id: str | None = None,
    org_id: str | None = None,
) -> int:
    """Get total storage used in bytes."""
    db = get_database()
    return await db.get_storage_used(owner_id, org_id)


async def delete_media(media_id: str) -> dict | None:
    """Delete a media record. Returns the deleted data for storage cleanup."""
    db = get_database()
    return await db.delete_media(media_id)
