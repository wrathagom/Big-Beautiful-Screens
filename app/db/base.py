"""Abstract database interface for Big Beautiful Screens.

All database backends must implement this interface.
"""

from abc import ABC, abstractmethod
from datetime import datetime


class DatabaseBackend(ABC):
    """Abstract base class for database backends."""

    @abstractmethod
    async def init(self) -> None:
        """Initialize the database (create tables, seed data, etc.)."""
        pass

    # ============== Screen Methods ==============

    @abstractmethod
    async def create_screen(
        self,
        screen_id: str,
        api_key: str,
        created_at: str | datetime,
        name: str | None = None,
        owner_id: str | None = None,
        org_id: str | None = None,
    ) -> None:
        """Create a new screen."""
        pass

    @abstractmethod
    async def get_screen_by_id(self, screen_id: str) -> dict | None:
        """Get a screen by its ID."""
        pass

    @abstractmethod
    async def get_screen_by_api_key(self, api_key: str) -> dict | None:
        """Get a screen by its API key."""
        pass

    @abstractmethod
    async def get_all_screens(
        self,
        limit: int | None = None,
        offset: int = 0,
        owner_id: str | None = None,
        org_id: str | None = None,
    ) -> list[dict]:
        """Get screens with optional pagination and ownership filtering."""
        pass

    @abstractmethod
    async def get_screens_count(
        self, owner_id: str | None = None, org_id: str | None = None
    ) -> int:
        """Get total count of screens."""
        pass

    @abstractmethod
    async def delete_screen(self, screen_id: str) -> bool:
        """Delete a screen. Returns True if deleted."""
        pass

    @abstractmethod
    async def update_screen_name(self, screen_id: str, name: str | None) -> bool:
        """Update a screen's name. Returns True if updated."""
        pass

    @abstractmethod
    async def get_rotation_settings(self, screen_id: str) -> dict | None:
        """Get rotation/display settings for a screen."""
        pass

    @abstractmethod
    async def update_rotation_settings(
        self,
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
    ) -> bool:
        """Update rotation/display settings. Returns True if updated."""
        pass

    # ============== Page Methods ==============

    @abstractmethod
    async def upsert_page(
        self,
        screen_id: str,
        name: str,
        payload: dict,
        duration: int | None = None,
        expires_at: str | None = None,
    ) -> dict:
        """Create or update a page. Returns the page data."""
        pass

    @abstractmethod
    async def get_all_pages(self, screen_id: str, include_expired: bool = False) -> list[dict]:
        """Get all pages for a screen."""
        pass

    @abstractmethod
    async def get_page(self, screen_id: str, name: str) -> dict | None:
        """Get a specific page by name."""
        pass

    @abstractmethod
    async def update_page(
        self,
        screen_id: str,
        name: str,
        content: list | None = None,
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
        pass

    @abstractmethod
    async def delete_page(self, screen_id: str, name: str) -> bool:
        """Delete a page. Returns True if deleted."""
        pass

    @abstractmethod
    async def reorder_pages(self, screen_id: str, page_names: list[str]) -> bool:
        """Reorder pages. Returns True on success."""
        pass

    @abstractmethod
    async def cleanup_expired_pages(self) -> list[tuple[str, str]]:
        """Remove expired pages. Returns list of (screen_id, page_name) deleted."""
        pass

    # ============== Theme Methods ==============

    @abstractmethod
    async def get_all_themes(
        self, limit: int | None = None, offset: int = 0, owner_id: str | None = None
    ) -> list[dict]:
        """Get themes with optional pagination."""
        pass

    @abstractmethod
    async def get_themes_count(self, owner_id: str | None = None) -> int:
        """Get total count of themes."""
        pass

    @abstractmethod
    async def get_theme(self, name: str) -> dict | None:
        """Get a theme by name."""
        pass

    @abstractmethod
    async def create_theme(
        self,
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
        """Create a new theme."""
        pass

    @abstractmethod
    async def update_theme(
        self,
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
        pass

    @abstractmethod
    async def delete_theme(self, name: str) -> tuple[bool, str | None]:
        """Delete a theme. Returns (success, error_message)."""
        pass

    @abstractmethod
    async def get_theme_usage_counts(self) -> dict[str, int]:
        """Get usage count for all themes."""
        pass

    # ============== User Methods (SaaS only) ==============

    async def get_user(self, user_id: str) -> dict | None:
        """Get a user by ID. Only implemented in SaaS backends."""
        return None

    async def create_or_update_user(
        self, user_id: str, email: str, name: str | None = None, plan: str = "free"
    ) -> dict:
        """Create or update a user. Only implemented in SaaS backends."""
        raise NotImplementedError("User management not available in this backend")

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user. Only implemented in SaaS backends."""
        raise NotImplementedError("User management not available in this backend")

    # ============== Organization Methods (SaaS only) ==============

    async def get_organization(self, org_id: str) -> dict | None:
        """Get an organization by ID. Only implemented in SaaS backends."""
        return None

    async def create_or_update_organization(
        self, org_id: str, name: str, slug: str, plan: str = "free"
    ) -> dict:
        """Create or update an organization. Only implemented in SaaS backends."""
        raise NotImplementedError("Organization management not available in this backend")

    async def delete_organization(self, org_id: str) -> bool:
        """Delete an organization. Only implemented in SaaS backends."""
        raise NotImplementedError("Organization management not available in this backend")

    async def add_org_member(self, user_id: str, org_id: str, role: str = "member") -> bool:
        """Add a user to an organization. Only implemented in SaaS backends."""
        raise NotImplementedError("Organization management not available in this backend")

    async def remove_org_member(self, user_id: str, org_id: str) -> bool:
        """Remove a user from an organization. Only implemented in SaaS backends."""
        raise NotImplementedError("Organization management not available in this backend")

    async def get_user_organizations(self, user_id: str) -> list[dict]:
        """Get organizations for a user. Only implemented in SaaS backends."""
        return []

    # ============== Media Methods ==============

    @abstractmethod
    async def create_media(
        self,
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
        """Create a media record. Returns the media data."""
        pass

    @abstractmethod
    async def get_media_by_id(self, media_id: str) -> dict | None:
        """Get a media record by ID."""
        pass

    @abstractmethod
    async def get_all_media(
        self,
        limit: int | None = None,
        offset: int = 0,
        owner_id: str | None = None,
        org_id: str | None = None,
        content_type_filter: str | None = None,
    ) -> list[dict]:
        """
        Get media with optional pagination and filtering.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            owner_id: Filter by owner ID
            org_id: Filter by organization ID
            content_type_filter: Filter by type ('image' or 'video')
        """
        pass

    @abstractmethod
    async def get_media_count(
        self,
        owner_id: str | None = None,
        org_id: str | None = None,
    ) -> int:
        """Get total count of media records."""
        pass

    @abstractmethod
    async def get_storage_used(
        self,
        owner_id: str | None = None,
        org_id: str | None = None,
    ) -> int:
        """Get total storage used in bytes."""
        pass

    @abstractmethod
    async def delete_media(self, media_id: str) -> dict | None:
        """
        Delete a media record.

        Returns the deleted media data (for storage cleanup) or None if not found.
        """
        pass
