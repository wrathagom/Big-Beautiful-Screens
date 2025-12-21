"""PostgreSQL database backend for Big Beautiful Screens.

Used in SaaS mode with Neon or other PostgreSQL providers.
"""

import json
from datetime import UTC, datetime

import asyncpg

from ..config import get_settings
from ..themes import get_builtin_themes, get_theme
from .base import DatabaseBackend


class PostgresBackend(DatabaseBackend):
    """PostgreSQL implementation of the database backend."""

    def __init__(self):
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""
        if self._pool is None:
            settings = get_settings()
            if not settings.DATABASE_URL:
                raise ValueError("DATABASE_URL is required for PostgreSQL backend")
            self._pool = await asyncpg.create_pool(settings.DATABASE_URL)
        return self._pool

    async def init(self) -> None:
        """Initialize the database and create tables."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Users table (synced from Clerk)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT,
                    plan TEXT DEFAULT 'free',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Organizations table (synced from Clerk)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    plan TEXT DEFAULT 'free',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Organization memberships
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS org_memberships (
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                    org_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
                    role TEXT DEFAULT 'member',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (user_id, org_id)
                )
            """)

            # Screens table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS screens (
                    id TEXT PRIMARY KEY,
                    api_key TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    last_updated TIMESTAMPTZ,
                    name TEXT,
                    owner_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                    org_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
                    rotation_enabled BOOLEAN DEFAULT FALSE,
                    rotation_interval INTEGER DEFAULT 30,
                    gap TEXT DEFAULT '1rem',
                    border_radius TEXT DEFAULT '1rem',
                    panel_shadow TEXT,
                    background_color TEXT,
                    panel_color TEXT,
                    font_family TEXT,
                    font_color TEXT,
                    theme TEXT,
                    head_html TEXT
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_screens_owner ON screens(owner_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_screens_org ON screens(org_id)
            """)

            # Pages table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id SERIAL PRIMARY KEY,
                    screen_id TEXT NOT NULL REFERENCES screens(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    content JSONB NOT NULL,
                    display_order INTEGER NOT NULL DEFAULT 0,
                    duration INTEGER,
                    expires_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    UNIQUE(screen_id, name)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_screen ON pages(screen_id)
            """)

            # Themes table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS themes (
                    name TEXT PRIMARY KEY,
                    display_name TEXT,
                    owner_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                    background_color TEXT NOT NULL,
                    panel_color TEXT NOT NULL,
                    font_family TEXT NOT NULL,
                    font_color TEXT NOT NULL,
                    gap TEXT NOT NULL DEFAULT '1rem',
                    border_radius TEXT NOT NULL DEFAULT '1rem',
                    panel_shadow TEXT,
                    is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_themes_owner ON themes(owner_id)
            """)

            # Seed built-in themes
            await self._seed_builtin_themes(conn)

    async def _seed_builtin_themes(self, conn) -> None:
        """Seed the database with built-in themes if not already present."""
        count = await conn.fetchval("SELECT COUNT(*) FROM themes WHERE is_builtin = TRUE")

        if count > 0:
            return

        now = datetime.now(UTC)
        builtin_themes = get_builtin_themes()

        for name, values in builtin_themes.items():
            display_name = name.replace("-", " ").title()
            await conn.execute(
                """
                INSERT INTO themes (name, display_name, background_color, panel_color, font_family,
                                  font_color, gap, border_radius, panel_shadow, is_builtin, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, TRUE, $10, $10)
                ON CONFLICT (name) DO NOTHING
            """,
                name,
                display_name,
                values["background_color"],
                values["panel_color"],
                values["font_family"],
                values["font_color"],
                values.get("gap", "1rem"),
                values.get("border_radius", "1rem"),
                values.get("panel_shadow"),
                now,
            )

    # ============== Screen Methods ==============

    async def create_screen(
        self,
        screen_id: str,
        api_key: str,
        created_at: str,
        name: str | None = None,
        owner_id: str | None = None,
        org_id: str | None = None,
    ) -> None:
        """Create a new screen with default theme applied."""
        default_theme = get_theme("default")
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO screens (
                    id, api_key, created_at, name, owner_id, org_id, theme,
                    background_color, panel_color, font_family, font_color,
                    gap, border_radius, panel_shadow
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                screen_id,
                api_key,
                created_at,
                name,
                owner_id,
                org_id,
                "default",
                default_theme["background_color"],
                default_theme["panel_color"],
                default_theme["font_family"],
                default_theme["font_color"],
                default_theme["gap"],
                default_theme["border_radius"],
                default_theme["panel_shadow"],
            )

    async def get_screen_by_id(self, screen_id: str) -> dict | None:
        """Get a screen by its ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM screens WHERE id = $1", screen_id)
            return dict(row) if row else None

    async def get_screen_by_api_key(self, api_key: str) -> dict | None:
        """Get a screen by its API key."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM screens WHERE api_key = $1", api_key)
            return dict(row) if row else None

    async def get_all_screens(
        self,
        limit: int | None = None,
        offset: int = 0,
        owner_id: str | None = None,
        org_id: str | None = None,
    ) -> list[dict]:
        """Get screens with optional pagination and ownership filtering."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if owner_id is not None:
                query = """
                    SELECT * FROM screens
                    WHERE owner_id = $1 OR org_id = $2
                    ORDER BY created_at DESC
                """
                params = [owner_id, org_id]
                if limit:
                    query += f" LIMIT {limit} OFFSET {offset}"
                rows = await conn.fetch(query, *params)
            else:
                query = "SELECT * FROM screens ORDER BY created_at DESC"
                if limit:
                    query += f" LIMIT {limit} OFFSET {offset}"
                rows = await conn.fetch(query)

            return [dict(row) for row in rows]

    async def get_screens_count(
        self, owner_id: str | None = None, org_id: str | None = None
    ) -> int:
        """Get total count of screens."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if owner_id is not None:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM screens WHERE owner_id = $1 OR org_id = $2",
                    owner_id,
                    org_id,
                )
            else:
                return await conn.fetchval("SELECT COUNT(*) FROM screens")

    async def delete_screen(self, screen_id: str) -> bool:
        """Delete a screen."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM screens WHERE id = $1", screen_id)
            return result == "DELETE 1"

    async def update_screen_name(self, screen_id: str, name: str | None) -> bool:
        """Update a screen's name."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE screens SET name = $1 WHERE id = $2", name, screen_id
            )
            return result == "UPDATE 1"

    async def get_rotation_settings(self, screen_id: str) -> dict | None:
        """Get rotation/display settings for a screen."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT rotation_enabled, rotation_interval, gap, border_radius, panel_shadow,
                       background_color, panel_color, font_family, font_color, theme, head_html
                FROM screens WHERE id = $1
            """,
                screen_id,
            )

            if not row:
                return None

            return {
                "enabled": row["rotation_enabled"] or False,
                "interval": row["rotation_interval"] or 30,
                "gap": row["gap"] or "1rem",
                "border_radius": row["border_radius"] or "1rem",
                "panel_shadow": row["panel_shadow"],
                "background_color": row["background_color"],
                "panel_color": row["panel_color"],
                "font_family": row["font_family"],
                "font_color": row["font_color"],
                "theme": row["theme"],
                "head_html": row["head_html"],
            }

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
        """Update rotation/display settings."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Check screen exists
            exists = await conn.fetchval("SELECT 1 FROM screens WHERE id = $1", screen_id)
            if not exists:
                return False

            updates = []
            params = []
            param_idx = 1

            if enabled is not None:
                updates.append(f"rotation_enabled = ${param_idx}")
                params.append(enabled)
                param_idx += 1
            if interval is not None:
                updates.append(f"rotation_interval = ${param_idx}")
                params.append(interval)
                param_idx += 1
            if gap is not None:
                updates.append(f"gap = ${param_idx}")
                params.append(gap)
                param_idx += 1
            if border_radius is not None:
                updates.append(f"border_radius = ${param_idx}")
                params.append(border_radius)
                param_idx += 1
            if panel_shadow is not None:
                updates.append(f"panel_shadow = ${param_idx}")
                params.append(panel_shadow)
                param_idx += 1
            if background_color is not None:
                updates.append(f"background_color = ${param_idx}")
                params.append(background_color)
                param_idx += 1
            if panel_color is not None:
                updates.append(f"panel_color = ${param_idx}")
                params.append(panel_color)
                param_idx += 1
            if font_family is not None:
                updates.append(f"font_family = ${param_idx}")
                params.append(font_family)
                param_idx += 1
            if font_color is not None:
                updates.append(f"font_color = ${param_idx}")
                params.append(font_color)
                param_idx += 1
            if theme is not None:
                updates.append(f"theme = ${param_idx}")
                params.append(theme)
                param_idx += 1
            if head_html is not None:
                updates.append(f"head_html = ${param_idx}")
                params.append(head_html)
                param_idx += 1

            if updates:
                params.append(screen_id)
                await conn.execute(
                    f"UPDATE screens SET {', '.join(updates)} WHERE id = ${param_idx}", *params
                )

            return True

    # ============== Page Methods ==============

    async def upsert_page(
        self,
        screen_id: str,
        name: str,
        payload: dict,
        duration: int | None = None,
        expires_at: str | None = None,
    ) -> dict:
        """Create or update a page."""
        now = datetime.now(UTC)
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, display_order FROM pages WHERE screen_id = $1 AND name = $2",
                screen_id,
                name,
            )

            if existing:
                await conn.execute(
                    """
                    UPDATE pages
                    SET content = $1, duration = $2, expires_at = $3, updated_at = $4
                    WHERE screen_id = $5 AND name = $6
                """,
                    json.dumps(payload),
                    duration,
                    expires_at,
                    now,
                    screen_id,
                    name,
                )
                display_order = existing["display_order"]
            else:
                max_order = await conn.fetchval(
                    "SELECT COALESCE(MAX(display_order), -1) + 1 FROM pages WHERE screen_id = $1",
                    screen_id,
                )
                display_order = max_order or 0

                await conn.execute(
                    """
                    INSERT INTO pages (screen_id, name, content, display_order, duration, expires_at, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
                """,
                    screen_id,
                    name,
                    json.dumps(payload),
                    display_order,
                    duration,
                    expires_at,
                    now,
                )

            await conn.execute("UPDATE screens SET last_updated = $1 WHERE id = $2", now, screen_id)

            return {
                "name": name,
                "content": payload.get("content", []),
                "background_color": payload.get("background_color"),
                "panel_color": payload.get("panel_color"),
                "font_family": payload.get("font_family"),
                "font_color": payload.get("font_color"),
                "gap": payload.get("gap"),
                "border_radius": payload.get("border_radius"),
                "panel_shadow": payload.get("panel_shadow"),
                "display_order": display_order,
                "duration": duration,
                "expires_at": expires_at,
            }

    async def get_all_pages(self, screen_id: str, include_expired: bool = False) -> list[dict]:
        """Get all pages for a screen."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if include_expired:
                rows = await conn.fetch(
                    "SELECT * FROM pages WHERE screen_id = $1 ORDER BY display_order", screen_id
                )
            else:
                now = datetime.now(UTC)
                rows = await conn.fetch(
                    """
                    SELECT * FROM pages
                    WHERE screen_id = $1 AND (expires_at IS NULL OR expires_at > $2)
                    ORDER BY display_order
                """,
                    screen_id,
                    now,
                )

            pages = []
            for row in rows:
                content_data = (
                    row["content"]
                    if isinstance(row["content"], dict)
                    else json.loads(row["content"])
                )
                pages.append(
                    {
                        "name": row["name"],
                        "content": content_data.get("content", []),
                        "background_color": content_data.get("background_color"),
                        "panel_color": content_data.get("panel_color"),
                        "font_family": content_data.get("font_family"),
                        "font_color": content_data.get("font_color"),
                        "gap": content_data.get("gap"),
                        "border_radius": content_data.get("border_radius"),
                        "panel_shadow": content_data.get("panel_shadow"),
                        "display_order": row["display_order"],
                        "duration": row["duration"],
                        "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                    }
                )
            return pages

    async def get_page(self, screen_id: str, name: str) -> dict | None:
        """Get a specific page by name."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM pages WHERE screen_id = $1 AND name = $2", screen_id, name
            )

            if not row:
                return None

            content_data = (
                row["content"] if isinstance(row["content"], dict) else json.loads(row["content"])
            )
            return {
                "name": row["name"],
                "content": content_data.get("content", []),
                "background_color": content_data.get("background_color"),
                "panel_color": content_data.get("panel_color"),
                "font_family": content_data.get("font_family"),
                "font_color": content_data.get("font_color"),
                "gap": content_data.get("gap"),
                "border_radius": content_data.get("border_radius"),
                "panel_shadow": content_data.get("panel_shadow"),
                "display_order": row["display_order"],
                "duration": row["duration"],
                "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
            }

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
        """Partially update a page."""
        now = datetime.now(UTC)
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM pages WHERE screen_id = $1 AND name = $2", screen_id, name
            )

            if not row:
                return None

            existing_data = (
                row["content"] if isinstance(row["content"], dict) else json.loads(row["content"])
            )

            if content is not None:
                existing_data["content"] = content
            if background_color is not None:
                existing_data["background_color"] = background_color
            if panel_color is not None:
                existing_data["panel_color"] = panel_color
            if font_family is not None:
                existing_data["font_family"] = font_family
            if font_color is not None:
                existing_data["font_color"] = font_color
            if gap is not None:
                existing_data["gap"] = gap
            if border_radius is not None:
                existing_data["border_radius"] = border_radius
            if panel_shadow is not None:
                existing_data["panel_shadow"] = panel_shadow

            new_duration = duration if duration is not None else row["duration"]
            new_expires_at = expires_at if expires_at is not None else row["expires_at"]

            await conn.execute(
                """
                UPDATE pages SET content = $1, duration = $2, expires_at = $3, updated_at = $4
                WHERE screen_id = $5 AND name = $6
            """,
                json.dumps(existing_data),
                new_duration,
                new_expires_at,
                now,
                screen_id,
                name,
            )

            await conn.execute("UPDATE screens SET last_updated = $1 WHERE id = $2", now, screen_id)

            return {
                "name": name,
                "content": existing_data.get("content", []),
                "background_color": existing_data.get("background_color"),
                "panel_color": existing_data.get("panel_color"),
                "font_family": existing_data.get("font_family"),
                "font_color": existing_data.get("font_color"),
                "gap": existing_data.get("gap"),
                "border_radius": existing_data.get("border_radius"),
                "panel_shadow": existing_data.get("panel_shadow"),
                "display_order": row["display_order"],
                "duration": new_duration,
                "expires_at": new_expires_at.isoformat()
                if hasattr(new_expires_at, "isoformat")
                else new_expires_at,
            }

    async def delete_page(self, screen_id: str, name: str) -> bool:
        """Delete a page. Cannot delete 'default'."""
        if name == "default":
            return False

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM pages WHERE screen_id = $1 AND name = $2", screen_id, name
            )
            return result == "DELETE 1"

    async def reorder_pages(self, screen_id: str, page_names: list[str]) -> bool:
        """Reorder pages."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            for order, name in enumerate(page_names):
                await conn.execute(
                    "UPDATE pages SET display_order = $1 WHERE screen_id = $2 AND name = $3",
                    order,
                    screen_id,
                    name,
                )
            return True

    async def cleanup_expired_pages(self) -> list[tuple[str, str]]:
        """Remove expired pages."""
        now = datetime.now(UTC)
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT screen_id, name FROM pages WHERE expires_at IS NOT NULL AND expires_at <= $1 AND name != 'default'",
                now,
            )

            if rows:
                await conn.execute(
                    "DELETE FROM pages WHERE expires_at IS NOT NULL AND expires_at <= $1 AND name != 'default'",
                    now,
                )

            return [(row["screen_id"], row["name"]) for row in rows]

    # ============== Theme Methods ==============

    async def get_all_themes(
        self, limit: int | None = None, offset: int = 0, owner_id: str | None = None
    ) -> list[dict]:
        """Get themes with optional pagination."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if owner_id is not None:
                query = "SELECT * FROM themes WHERE owner_id IS NULL OR owner_id = $1 ORDER BY is_builtin DESC, name"
                params = [owner_id]
            else:
                query = "SELECT * FROM themes ORDER BY is_builtin DESC, name"
                params = []

            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"

            rows = await conn.fetch(query, *params)

            return [
                {
                    "name": row["name"],
                    "display_name": row["display_name"],
                    "background_color": row["background_color"],
                    "panel_color": row["panel_color"],
                    "font_family": row["font_family"],
                    "font_color": row["font_color"],
                    "gap": row["gap"],
                    "border_radius": row["border_radius"],
                    "panel_shadow": row["panel_shadow"],
                    "is_builtin": row["is_builtin"],
                }
                for row in rows
            ]

    async def get_themes_count(self, owner_id: str | None = None) -> int:
        """Get total count of themes."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if owner_id is not None:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM themes WHERE owner_id IS NULL OR owner_id = $1", owner_id
                )
            else:
                return await conn.fetchval("SELECT COUNT(*) FROM themes")

    async def get_theme(self, name: str) -> dict | None:
        """Get a theme by name."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM themes WHERE name = $1", name)

            if not row:
                return None

            return {
                "name": row["name"],
                "display_name": row["display_name"],
                "background_color": row["background_color"],
                "panel_color": row["panel_color"],
                "font_family": row["font_family"],
                "font_color": row["font_color"],
                "gap": row["gap"],
                "border_radius": row["border_radius"],
                "panel_shadow": row["panel_shadow"],
                "is_builtin": row["is_builtin"],
            }

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
        """Create a new custom theme."""
        now = datetime.now(UTC)
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO themes (name, display_name, owner_id, background_color, panel_color, font_family,
                                  font_color, gap, border_radius, panel_shadow, is_builtin, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, FALSE, $11, $11)
            """,
                name,
                display_name or name.replace("-", " ").title(),
                owner_id,
                background_color,
                panel_color,
                font_family,
                font_color,
                gap,
                border_radius,
                panel_shadow,
                now,
            )

        return {
            "name": name,
            "display_name": display_name or name.replace("-", " ").title(),
            "background_color": background_color,
            "panel_color": panel_color,
            "font_family": font_family,
            "font_color": font_color,
            "gap": gap,
            "border_radius": border_radius,
            "panel_shadow": panel_shadow,
            "is_builtin": False,
        }

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
        """Update a theme."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            exists = await conn.fetchval("SELECT 1 FROM themes WHERE name = $1", name)
            if not exists:
                return None

            updates = []
            params = []
            param_idx = 1

            if display_name is not None:
                updates.append(f"display_name = ${param_idx}")
                params.append(display_name)
                param_idx += 1
            if background_color is not None:
                updates.append(f"background_color = ${param_idx}")
                params.append(background_color)
                param_idx += 1
            if panel_color is not None:
                updates.append(f"panel_color = ${param_idx}")
                params.append(panel_color)
                param_idx += 1
            if font_family is not None:
                updates.append(f"font_family = ${param_idx}")
                params.append(font_family)
                param_idx += 1
            if font_color is not None:
                updates.append(f"font_color = ${param_idx}")
                params.append(font_color)
                param_idx += 1
            if gap is not None:
                updates.append(f"gap = ${param_idx}")
                params.append(gap)
                param_idx += 1
            if border_radius is not None:
                updates.append(f"border_radius = ${param_idx}")
                params.append(border_radius)
                param_idx += 1
            if panel_shadow is not None:
                updates.append(f"panel_shadow = ${param_idx}")
                params.append(panel_shadow)
                param_idx += 1

            if updates:
                updates.append(f"updated_at = ${param_idx}")
                params.append(datetime.now(UTC))
                param_idx += 1
                params.append(name)
                await conn.execute(
                    f"UPDATE themes SET {', '.join(updates)} WHERE name = ${param_idx}", *params
                )

        return await self.get_theme(name)

    async def delete_theme(self, name: str) -> tuple[bool, str | None]:
        """Delete a theme if not in use."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT is_builtin FROM themes WHERE name = $1", name)

            if not row:
                return False, "Theme not found"

            usage_count = await conn.fetchval("SELECT COUNT(*) FROM screens WHERE theme = $1", name)

            if usage_count > 0:
                return False, f"Theme is in use by {usage_count} screen(s)"

            await conn.execute("DELETE FROM themes WHERE name = $1", name)

        return True, None

    async def get_theme_usage_counts(self) -> dict[str, int]:
        """Get usage count for all themes."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT theme, COUNT(*) as count FROM screens WHERE theme IS NOT NULL GROUP BY theme"
            )
        return {row["theme"]: row["count"] for row in rows}

    # ============== User Methods (SaaS only) ==============

    async def get_user(self, user_id: str) -> dict | None:
        """Get a user by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            return dict(row) if row else None

    async def create_or_update_user(
        self, user_id: str, email: str, name: str | None = None, plan: str = "free"
    ) -> dict:
        """Create or update a user (from Clerk webhook)."""
        now = datetime.now(UTC)
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, email, name, plan, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $5)
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    plan = EXCLUDED.plan,
                    updated_at = EXCLUDED.updated_at
            """,
                user_id,
                email,
                name,
                plan,
                now,
            )

        return await self.get_user(user_id)

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
            return result == "DELETE 1"

    # ============== Organization Methods (SaaS only) ==============

    async def get_organization(self, org_id: str) -> dict | None:
        """Get an organization by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM organizations WHERE id = $1", org_id)
            return dict(row) if row else None

    async def create_or_update_organization(
        self, org_id: str, name: str, slug: str, plan: str = "free"
    ) -> dict:
        """Create or update an organization (from Clerk webhook)."""
        now = datetime.now(UTC)
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO organizations (id, name, slug, plan, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $5)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    slug = EXCLUDED.slug,
                    plan = EXCLUDED.plan,
                    updated_at = EXCLUDED.updated_at
            """,
                org_id,
                name,
                slug,
                plan,
                now,
            )

        return await self.get_organization(org_id)

    async def delete_organization(self, org_id: str) -> bool:
        """Delete an organization."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM organizations WHERE id = $1", org_id)
            return result == "DELETE 1"

    async def add_org_member(self, user_id: str, org_id: str, role: str = "member") -> bool:
        """Add a user to an organization."""
        now = datetime.now(UTC)
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO org_memberships (user_id, org_id, role, created_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, org_id) DO UPDATE SET role = EXCLUDED.role
                """,
                    user_id,
                    org_id,
                    role,
                    now,
                )
                return True
            except Exception:
                return False

    async def remove_org_member(self, user_id: str, org_id: str) -> bool:
        """Remove a user from an organization."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM org_memberships WHERE user_id = $1 AND org_id = $2", user_id, org_id
            )
            return result == "DELETE 1"

    async def get_user_organizations(self, user_id: str) -> list[dict]:
        """Get organizations for a user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT o.*, m.role
                FROM organizations o
                JOIN org_memberships m ON o.id = m.org_id
                WHERE m.user_id = $1
            """,
                user_id,
            )
            return [dict(row) for row in rows]
