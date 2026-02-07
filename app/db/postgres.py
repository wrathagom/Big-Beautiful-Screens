"""PostgreSQL database backend for Big Beautiful Screens.

Used in SaaS mode with Neon or other PostgreSQL providers.
"""

import json
from datetime import UTC, datetime
from datetime import date as date_type

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
                    head_html TEXT,
                    default_layout TEXT,
                    transition TEXT DEFAULT 'none',
                    transition_duration INTEGER DEFAULT 500
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

            # API usage tracking table (for daily quotas)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    usage_date DATE NOT NULL,
                    call_count INTEGER NOT NULL DEFAULT 0,
                    last_call_at TIMESTAMPTZ,
                    UNIQUE(user_id, usage_date)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_usage_user_date ON api_usage(user_id, usage_date)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_usage_date ON api_usage(usage_date)
            """)

            # Add Stripe billing columns to users table
            await conn.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT UNIQUE
            """)
            await conn.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT
            """)
            await conn.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'inactive'
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON users(stripe_customer_id)
            """)

            # Add transition columns to screens table
            await conn.execute("""
                ALTER TABLE screens ADD COLUMN IF NOT EXISTS default_layout TEXT
            """)
            await conn.execute("""
                ALTER TABLE screens ADD COLUMN IF NOT EXISTS transition TEXT DEFAULT 'none'
            """)
            await conn.execute("""
                ALTER TABLE screens ADD COLUMN IF NOT EXISTS transition_duration INTEGER DEFAULT 500
            """)
            await conn.execute("""
                ALTER TABLE screens ADD COLUMN IF NOT EXISTS debug_enabled BOOLEAN DEFAULT FALSE
            """)

            # Media table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS media (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                    org_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size_bytes BIGINT NOT NULL,
                    storage_path TEXT NOT NULL,
                    storage_backend TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_media_owner ON media(owner_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_media_org ON media(org_id)
            """)

            # Templates table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    thumbnail_url TEXT,
                    type TEXT NOT NULL CHECK (type IN ('system', 'user')),
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                    configuration JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_templates_user ON templates(user_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_templates_type ON templates(type)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category)
            """)

            # Webhook events table (idempotency)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_events (
                    provider TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    received_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (provider, event_id)
                )
            """)

            # Account API keys table (for MCP integration)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS account_api_keys (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    scopes TEXT NOT NULL DEFAULT '["*"]',
                    expires_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL,
                    last_used_at TIMESTAMPTZ
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_account_api_keys_key ON account_api_keys(key)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_account_api_keys_user ON account_api_keys(user_id)
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
        created_at: str | datetime,
        name: str | None = None,
        owner_id: str | None = None,
        org_id: str | None = None,
    ) -> None:
        """Create a new screen with default theme applied."""
        default_theme = get_theme("default")
        # PostgreSQL needs datetime object
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
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
                       background_color, panel_color, font_family, font_color, theme, head_html,
                       default_layout, transition, transition_duration, debug_enabled
                FROM screens WHERE id = $1
            """,
                screen_id,
            )

            if not row:
                return None

            # Parse default_layout from JSON if present
            default_layout = None
            if row["default_layout"]:
                try:
                    default_layout = json.loads(row["default_layout"])
                except (json.JSONDecodeError, TypeError):
                    default_layout = row["default_layout"]  # Treat as preset name string

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
                "default_layout": default_layout,
                "transition": row["transition"] or "none",
                "transition_duration": row["transition_duration"] or 500,
                "debug_enabled": row["debug_enabled"] or False,
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
        default_layout: str | dict | None = None,
        transition: str | None = None,
        transition_duration: int | None = None,
        debug_enabled: bool | None = None,
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
            if default_layout is not None:
                updates.append(f"default_layout = ${param_idx}")
                # Store as JSON string if dict, otherwise as string (preset name)
                if isinstance(default_layout, dict):
                    params.append(json.dumps(default_layout))
                else:
                    params.append(default_layout)
                param_idx += 1
            if transition is not None:
                updates.append(f"transition = ${param_idx}")
                params.append(transition)
                param_idx += 1
            if transition_duration is not None:
                updates.append(f"transition_duration = ${param_idx}")
                params.append(transition_duration)
                param_idx += 1
            if debug_enabled is not None:
                updates.append(f"debug_enabled = ${param_idx}")
                params.append(debug_enabled)
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
                "layout": payload.get("layout"),
                "background_color": payload.get("background_color"),
                "panel_color": payload.get("panel_color"),
                "font_family": payload.get("font_family"),
                "font_color": payload.get("font_color"),
                "gap": payload.get("gap"),
                "border_radius": payload.get("border_radius"),
                "panel_shadow": payload.get("panel_shadow"),
                "transition": payload.get("transition"),
                "transition_duration": payload.get("transition_duration"),
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
                        "layout": content_data.get("layout"),
                        "background_color": content_data.get("background_color"),
                        "panel_color": content_data.get("panel_color"),
                        "font_family": content_data.get("font_family"),
                        "font_color": content_data.get("font_color"),
                        "gap": content_data.get("gap"),
                        "border_radius": content_data.get("border_radius"),
                        "panel_shadow": content_data.get("panel_shadow"),
                        "transition": content_data.get("transition"),
                        "transition_duration": content_data.get("transition_duration"),
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
                "layout": content_data.get("layout"),
                "background_color": content_data.get("background_color"),
                "panel_color": content_data.get("panel_color"),
                "font_family": content_data.get("font_family"),
                "font_color": content_data.get("font_color"),
                "gap": content_data.get("gap"),
                "border_radius": content_data.get("border_radius"),
                "panel_shadow": content_data.get("panel_shadow"),
                "transition": content_data.get("transition"),
                "transition_duration": content_data.get("transition_duration"),
                "display_order": row["display_order"],
                "duration": row["duration"],
                "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
            }

    async def update_page(
        self,
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
        transition: str | None = None,
        transition_duration: int | None = None,
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
            if layout is not None:
                existing_data["layout"] = layout
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
            if transition is not None:
                existing_data["transition"] = transition
            if transition_duration is not None:
                existing_data["transition_duration"] = transition_duration

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
                "layout": existing_data.get("layout"),
                "background_color": existing_data.get("background_color"),
                "panel_color": existing_data.get("panel_color"),
                "font_family": existing_data.get("font_family"),
                "font_color": existing_data.get("font_color"),
                "gap": existing_data.get("gap"),
                "border_radius": existing_data.get("border_radius"),
                "panel_shadow": existing_data.get("panel_shadow"),
                "transition": existing_data.get("transition"),
                "transition_duration": existing_data.get("transition_duration"),
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
                    updated_at = EXCLUDED.updated_at
                -- NOTE: plan is intentionally NOT updated to preserve Stripe subscription
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

    # ============== API Quota Methods (SaaS only) ==============

    async def get_daily_quota_usage(self, user_id: str, date: str | date_type) -> int:
        """Get API calls used for a specific date."""
        # Convert string to date if needed (PostgreSQL requires date object)
        if isinstance(date, str):
            date = date_type.fromisoformat(date)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT call_count FROM api_usage WHERE user_id = $1 AND usage_date = $2",
                user_id,
                date,
            )
            return result or 0

    async def increment_quota_usage(self, user_id: str, date: str | date_type) -> int:
        """Atomically increment and return new usage count."""
        # Convert string to date if needed (PostgreSQL requires date object)
        if isinstance(date, str):
            date = date_type.fromisoformat(date)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                """
                INSERT INTO api_usage (user_id, usage_date, call_count, last_call_at)
                VALUES ($1, $2, 1, NOW())
                ON CONFLICT (user_id, usage_date)
                DO UPDATE SET call_count = api_usage.call_count + 1, last_call_at = NOW()
                RETURNING call_count
            """,
                user_id,
                date,
            )
            return result

    async def get_user_id_by_api_key(self, api_key: str) -> str | None:
        """Get the owner user ID for a screen's API key."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT owner_id FROM screens WHERE api_key = $1",
                api_key,
            )
            return result

    # ============== Stripe Billing Methods (SaaS only) ==============

    async def get_stripe_customer_id(self, user_id: str) -> str | None:
        """Get Stripe customer ID for a user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT stripe_customer_id FROM users WHERE id = $1",
                user_id,
            )
            return result

    async def set_stripe_customer_id(self, user_id: str, customer_id: str) -> bool:
        """Set Stripe customer ID for a user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET stripe_customer_id = $1 WHERE id = $2",
                customer_id,
                user_id,
            )
            return result == "UPDATE 1"

    async def update_user_plan(
        self,
        user_id: str,
        plan: str,
        subscription_id: str | None = None,
        subscription_status: str = "active",
    ) -> bool:
        """Update user's plan after subscription change."""
        now = datetime.now(UTC)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE users
                SET plan = $1, stripe_subscription_id = $2, subscription_status = $3, updated_at = $4
                WHERE id = $5
            """,
                plan,
                subscription_id,
                subscription_status,
                now,
                user_id,
            )
            return result == "UPDATE 1"

    async def get_user_by_stripe_customer(self, customer_id: str) -> dict | None:
        """Get a user by their Stripe customer ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE stripe_customer_id = $1",
                customer_id,
            )
            return dict(row) if row else None

    # ============== Media Methods ==============

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
        """Create a media record."""
        now = datetime.now(UTC)
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO media (id, owner_id, org_id, filename, original_filename,
                                   content_type, size_bytes, storage_path, storage_backend,
                                   created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10)
            """,
                media_id,
                owner_id,
                org_id,
                filename,
                original_filename,
                content_type,
                size_bytes,
                storage_path,
                storage_backend,
                now,
            )

        return {
            "id": media_id,
            "owner_id": owner_id,
            "org_id": org_id,
            "filename": filename,
            "original_filename": original_filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "storage_path": storage_path,
            "storage_backend": storage_backend,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    async def get_media_by_id(self, media_id: str) -> dict | None:
        """Get a media record by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM media WHERE id = $1", media_id)
            if not row:
                return None
            result = dict(row)
            # Convert timestamps to ISO format strings
            if result.get("created_at"):
                result["created_at"] = result["created_at"].isoformat()
            if result.get("updated_at"):
                result["updated_at"] = result["updated_at"].isoformat()
            return result

    async def get_all_media(
        self,
        limit: int | None = None,
        offset: int = 0,
        owner_id: str | None = None,
        org_id: str | None = None,
        content_type_filter: str | None = None,
    ) -> list[dict]:
        """Get media with optional pagination and filtering."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            conditions = []
            params = []
            param_idx = 1

            if owner_id is not None:
                conditions.append(f"(owner_id = ${param_idx} OR org_id = ${param_idx + 1})")
                params.extend([owner_id, org_id])
                param_idx += 2

            if content_type_filter == "image":
                conditions.append("content_type LIKE 'image/%'")
            elif content_type_filter == "video":
                conditions.append("content_type LIKE 'video/%'")

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            query = f"SELECT * FROM media {where_clause} ORDER BY created_at DESC"

            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"

            rows = await conn.fetch(query, *params)

            results = []
            for row in rows:
                result = dict(row)
                if result.get("created_at"):
                    result["created_at"] = result["created_at"].isoformat()
                if result.get("updated_at"):
                    result["updated_at"] = result["updated_at"].isoformat()
                results.append(result)
            return results

    async def get_media_count(
        self,
        owner_id: str | None = None,
        org_id: str | None = None,
    ) -> int:
        """Get total count of media records."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if owner_id is not None:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM media WHERE owner_id = $1 OR org_id = $2",
                    owner_id,
                    org_id,
                )
            else:
                return await conn.fetchval("SELECT COUNT(*) FROM media")

    async def get_storage_used(
        self,
        owner_id: str | None = None,
        org_id: str | None = None,
    ) -> int:
        """Get total storage used in bytes."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if owner_id is not None:
                result = await conn.fetchval(
                    "SELECT COALESCE(SUM(size_bytes), 0) FROM media WHERE owner_id = $1 OR org_id = $2",
                    owner_id,
                    org_id,
                )
            else:
                result = await conn.fetchval("SELECT COALESCE(SUM(size_bytes), 0) FROM media")
            return result or 0

    async def delete_media(self, media_id: str) -> dict | None:
        """Delete a media record and return its data for storage cleanup."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM media WHERE id = $1", media_id)

            if not row:
                return None

            media_data = dict(row)
            if media_data.get("created_at"):
                media_data["created_at"] = media_data["created_at"].isoformat()
            if media_data.get("updated_at"):
                media_data["updated_at"] = media_data["updated_at"].isoformat()

            await conn.execute("DELETE FROM media WHERE id = $1", media_id)

            return media_data

    # ============== Template Methods ==============

    async def create_template(
        self,
        template_id: str,
        name: str,
        description: str | None,
        category: str,
        template_type: str,
        configuration: dict,
        user_id: str | None = None,
        thumbnail_url: str | None = None,
    ) -> dict:
        """Create a new template."""
        now = datetime.now(UTC)
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO templates (id, name, description, category, thumbnail_url,
                                       type, user_id, configuration, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)
            """,
                template_id,
                name,
                description,
                category,
                thumbnail_url,
                template_type,
                user_id,
                json.dumps(configuration),
                now,
            )

        return {
            "id": template_id,
            "name": name,
            "description": description,
            "category": category,
            "thumbnail_url": thumbnail_url,
            "type": template_type,
            "user_id": user_id,
            "configuration": configuration,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    async def get_template(self, template_id: str) -> dict | None:
        """Get a template by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM templates WHERE id = $1", template_id)

            if not row:
                return None

            result = dict(row)
            # JSONB is returned as dict, but may be string if stored as text
            if result.get("configuration") and isinstance(result["configuration"], str):
                result["configuration"] = json.loads(result["configuration"])
            # Convert timestamps to ISO strings
            if result.get("created_at"):
                result["created_at"] = result["created_at"].isoformat()
            if result.get("updated_at"):
                result["updated_at"] = result["updated_at"].isoformat()
            return result

    async def get_all_templates(
        self,
        template_type: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict]:
        """Get templates with optional filtering and pagination."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            conditions = []
            params = []
            param_idx = 1

            # Filter by type
            if template_type is not None:
                conditions.append(f"type = ${param_idx}")
                params.append(template_type)
                param_idx += 1

            # Filter by category
            if category is not None:
                conditions.append(f"category = ${param_idx}")
                params.append(category)
                param_idx += 1

            # Filter by user: show system templates + user's own templates
            if user_id is not None:
                conditions.append(f"(type = 'system' OR user_id = ${param_idx})")
                params.append(user_id)
                param_idx += 1

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Select without configuration for list efficiency
            query = f"""
                SELECT id, name, description, category, thumbnail_url, type, user_id,
                       created_at, updated_at
                FROM templates
                {where_clause}
                ORDER BY type DESC, created_at DESC
            """

            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"

            rows = await conn.fetch(query, *params)

            results = []
            for row in rows:
                result = dict(row)
                if result.get("created_at"):
                    result["created_at"] = result["created_at"].isoformat()
                if result.get("updated_at"):
                    result["updated_at"] = result["updated_at"].isoformat()
                results.append(result)
            return results

    async def get_templates_count(
        self,
        template_type: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> int:
        """Get total count of templates matching the filters."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            conditions = []
            params = []
            param_idx = 1

            if template_type is not None:
                conditions.append(f"type = ${param_idx}")
                params.append(template_type)
                param_idx += 1

            if category is not None:
                conditions.append(f"category = ${param_idx}")
                params.append(category)
                param_idx += 1

            if user_id is not None:
                conditions.append(f"(type = 'system' OR user_id = ${param_idx})")
                params.append(user_id)
                param_idx += 1

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            query = f"SELECT COUNT(*) FROM templates {where_clause}"

            return await conn.fetchval(query, *params)

    async def update_template(
        self,
        template_id: str,
        name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        thumbnail_url: str | None = None,
    ) -> dict | None:
        """Update template metadata."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Check if template exists
            exists = await conn.fetchval("SELECT 1 FROM templates WHERE id = $1", template_id)
            if not exists:
                return None

            updates = []
            params = []
            param_idx = 1

            if name is not None:
                updates.append(f"name = ${param_idx}")
                params.append(name)
                param_idx += 1
            if description is not None:
                updates.append(f"description = ${param_idx}")
                params.append(description)
                param_idx += 1
            if category is not None:
                updates.append(f"category = ${param_idx}")
                params.append(category)
                param_idx += 1
            if thumbnail_url is not None:
                updates.append(f"thumbnail_url = ${param_idx}")
                params.append(thumbnail_url)
                param_idx += 1

            if updates:
                updates.append(f"updated_at = ${param_idx}")
                params.append(datetime.now(UTC))
                param_idx += 1
                params.append(template_id)
                await conn.execute(
                    f"UPDATE templates SET {', '.join(updates)} WHERE id = ${param_idx}",
                    *params,
                )

            # Return updated template
            return await self.get_template(template_id)

    async def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM templates WHERE id = $1", template_id)
            return result == "DELETE 1"

    async def record_webhook_event(self, provider: str, event_id: str) -> bool:
        """Record a webhook event idempotently."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO webhook_events (provider, event_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """,
                provider,
                event_id,
            )
            return result.endswith("1")

    # ============== Account API Keys ==============

    async def create_account_api_key(
        self,
        key_id: str,
        key: str,
        user_id: str,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> dict:
        """Create a new account-level API key."""
        pool = await self._get_pool()
        now = datetime.now(UTC)
        scopes_json = json.dumps(scopes or ["*"])

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO account_api_keys (id, key, user_id, name, scopes, expires_at, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                key_id,
                key,
                user_id,
                name,
                scopes_json,
                expires_at,
                now,
            )

            return {
                "id": key_id,
                "key": key,
                "user_id": user_id,
                "name": name,
                "scopes": scopes or ["*"],
                "expires_at": expires_at.isoformat() if expires_at else None,
                "created_at": now.isoformat(),
                "last_used_at": None,
            }

    async def get_account_api_key_by_key(self, key: str) -> dict | None:
        """Get an account API key by its key value."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM account_api_keys WHERE key = $1", key)
            if not row:
                return None

            return {
                "id": row["id"],
                "key": row["key"],
                "user_id": row["user_id"],
                "name": row["name"],
                "scopes": json.loads(row["scopes"]) if row["scopes"] else ["*"],
                "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
            }

    async def get_account_api_keys_by_user(
        self, user_id: str, limit: int | None = None, offset: int = 0
    ) -> list[dict]:
        """Get all account API keys for a user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT id, key, user_id, name, scopes, expires_at, created_at, last_used_at
                FROM account_api_keys
                WHERE user_id = $1
                ORDER BY created_at DESC
            """
            params = [user_id]
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"

            rows = await conn.fetch(query, *params)

            return [
                {
                    "id": row["id"],
                    "key": row["key"],
                    "user_id": row["user_id"],
                    "name": row["name"],
                    "scopes": json.loads(row["scopes"]) if row["scopes"] else ["*"],
                    "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "last_used_at": row["last_used_at"].isoformat()
                    if row["last_used_at"]
                    else None,
                }
                for row in rows
            ]

    async def get_account_api_keys_count(self, user_id: str) -> int:
        """Get count of account API keys for a user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM account_api_keys WHERE user_id = $1", user_id
            )

    async def update_account_api_key_last_used(self, key_id: str) -> bool:
        """Update the last_used_at timestamp for an account API key."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE account_api_keys SET last_used_at = $1 WHERE id = $2",
                datetime.now(UTC),
                key_id,
            )
            return result == "UPDATE 1"

    async def delete_account_api_key(self, key_id: str) -> bool:
        """Delete an account API key."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM account_api_keys WHERE id = $1", key_id)
            return result == "DELETE 1"
