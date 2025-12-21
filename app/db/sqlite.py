"""SQLite database backend for Big Beautiful Screens.

Used in self-hosted mode.
"""

import aiosqlite
import json
from datetime import datetime, timezone
from pathlib import Path

from .base import DatabaseBackend
from ..config import get_settings
from ..themes import get_theme, get_builtin_themes


class SQLiteBackend(DatabaseBackend):
    """SQLite implementation of the database backend."""

    def __init__(self):
        self._db_path: Path | None = None

    @property
    def db_path(self) -> Path:
        """Get the database path from config."""
        if self._db_path is None:
            settings = get_settings()
            path = Path(settings.SQLITE_PATH)
            if not path.is_absolute():
                path = Path(__file__).parent.parent.parent / path
            self._db_path = path
        return self._db_path

    async def init(self) -> None:
        """Initialize the database and create tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            # Screens table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS screens (
                    id TEXT PRIMARY KEY,
                    api_key TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    last_updated TEXT,
                    name TEXT,
                    owner_id TEXT,
                    org_id TEXT,
                    rotation_enabled INTEGER DEFAULT 0,
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

            # Pages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    screen_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    display_order INTEGER NOT NULL DEFAULT 0,
                    duration INTEGER,
                    expires_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE,
                    UNIQUE(screen_id, name)
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_screen_id ON pages(screen_id)
            """)

            # Themes table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS themes (
                    name TEXT PRIMARY KEY,
                    display_name TEXT,
                    owner_id TEXT,
                    background_color TEXT NOT NULL,
                    panel_color TEXT NOT NULL,
                    font_family TEXT NOT NULL,
                    font_color TEXT NOT NULL,
                    gap TEXT NOT NULL DEFAULT '1rem',
                    border_radius TEXT NOT NULL DEFAULT '1rem',
                    panel_shadow TEXT,
                    is_builtin INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_themes_owner ON themes(owner_id)
            """)

            # Seed built-in themes if table is empty
            await self._seed_builtin_themes(db)

            await db.commit()

    async def _seed_builtin_themes(self, db) -> None:
        """Seed the database with built-in themes if not already present."""
        async with db.execute("SELECT COUNT(*) FROM themes WHERE is_builtin = 1") as cursor:
            count = (await cursor.fetchone())[0]

        if count > 0:
            return

        now = datetime.now(timezone.utc).isoformat()
        builtin_themes = get_builtin_themes()

        for name, values in builtin_themes.items():
            display_name = name.replace("-", " ").title()
            await db.execute("""
                INSERT INTO themes (name, display_name, background_color, panel_color, font_family,
                                  font_color, gap, border_radius, panel_shadow, is_builtin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
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
                now
            ))

    # ============== Screen Methods ==============

    async def create_screen(
        self,
        screen_id: str,
        api_key: str,
        created_at: str,
        name: str | None = None,
        owner_id: str | None = None,
        org_id: str | None = None
    ) -> None:
        """Create a new screen with default theme applied."""
        default_theme = get_theme("default")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO screens (
                    id, api_key, created_at, name, owner_id, org_id, theme,
                    background_color, panel_color, font_family, font_color,
                    gap, border_radius, panel_shadow
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                screen_id, api_key, created_at, name, owner_id, org_id, "default",
                default_theme["background_color"],
                default_theme["panel_color"],
                default_theme["font_family"],
                default_theme["font_color"],
                default_theme["gap"],
                default_theme["border_radius"],
                default_theme["panel_shadow"],
            ))
            await db.commit()

    async def get_screen_by_id(self, screen_id: str) -> dict | None:
        """Get a screen by its ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM screens WHERE id = ?", (screen_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_screen_by_api_key(self, api_key: str) -> dict | None:
        """Get a screen by its API key."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM screens WHERE api_key = ?", (api_key,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_screens(
        self,
        limit: int | None = None,
        offset: int = 0,
        owner_id: str | None = None,
        org_id: str | None = None
    ) -> list[dict]:
        """Get screens with optional pagination and ownership filtering."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            conditions = []
            params = []

            if owner_id is not None:
                conditions.append("(owner_id = ? OR org_id = ?)")
                params.extend([owner_id, org_id])

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            query = f"SELECT * FROM screens {where_clause} ORDER BY created_at DESC"

            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_screens_count(
        self,
        owner_id: str | None = None,
        org_id: str | None = None
    ) -> int:
        """Get total count of screens."""
        async with aiosqlite.connect(self.db_path) as db:
            if owner_id is not None:
                query = "SELECT COUNT(*) FROM screens WHERE owner_id = ? OR org_id = ?"
                params = (owner_id, org_id)
            else:
                query = "SELECT COUNT(*) FROM screens"
                params = ()

            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def delete_screen(self, screen_id: str) -> bool:
        """Delete a screen and its pages."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id FROM screens WHERE id = ?", (screen_id,)
            ) as cursor:
                if not await cursor.fetchone():
                    return False

            await db.execute("DELETE FROM pages WHERE screen_id = ?", (screen_id,))
            await db.execute("DELETE FROM screens WHERE id = ?", (screen_id,))
            await db.commit()
            return True

    async def update_screen_name(self, screen_id: str, name: str | None) -> bool:
        """Update a screen's name."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id FROM screens WHERE id = ?", (screen_id,)
            ) as cursor:
                if not await cursor.fetchone():
                    return False

            await db.execute(
                "UPDATE screens SET name = ? WHERE id = ?",
                (name, screen_id)
            )
            await db.commit()
            return True

    async def get_rotation_settings(self, screen_id: str) -> dict | None:
        """Get rotation/display settings for a screen."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT rotation_enabled, rotation_interval, gap, border_radius, panel_shadow,
                       background_color, panel_color, font_family, font_color, theme, head_html
                FROM screens WHERE id = ?
            """, (screen_id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                return None

            return {
                "enabled": bool(row['rotation_enabled']),
                "interval": row['rotation_interval'] or 30,
                "gap": row['gap'] or '1rem',
                "border_radius": row['border_radius'] or '1rem',
                "panel_shadow": row['panel_shadow'],
                "background_color": row['background_color'],
                "panel_color": row['panel_color'],
                "font_family": row['font_family'],
                "font_color": row['font_color'],
                "theme": row['theme'],
                "head_html": row['head_html']
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
        head_html: str | None = None
    ) -> bool:
        """Update rotation/display settings."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id FROM screens WHERE id = ?", (screen_id,)
            ) as cursor:
                if not await cursor.fetchone():
                    return False

            updates = []
            params = []

            if enabled is not None:
                updates.append("rotation_enabled = ?")
                params.append(1 if enabled else 0)
            if interval is not None:
                updates.append("rotation_interval = ?")
                params.append(interval)
            if gap is not None:
                updates.append("gap = ?")
                params.append(gap)
            if border_radius is not None:
                updates.append("border_radius = ?")
                params.append(border_radius)
            if panel_shadow is not None:
                updates.append("panel_shadow = ?")
                params.append(panel_shadow)
            if background_color is not None:
                updates.append("background_color = ?")
                params.append(background_color)
            if panel_color is not None:
                updates.append("panel_color = ?")
                params.append(panel_color)
            if font_family is not None:
                updates.append("font_family = ?")
                params.append(font_family)
            if font_color is not None:
                updates.append("font_color = ?")
                params.append(font_color)
            if theme is not None:
                updates.append("theme = ?")
                params.append(theme)
            if head_html is not None:
                updates.append("head_html = ?")
                params.append(head_html)

            if updates:
                params.append(screen_id)
                await db.execute(
                    f"UPDATE screens SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                await db.commit()

            return True

    # ============== Page Methods ==============

    async def upsert_page(
        self,
        screen_id: str,
        name: str,
        payload: dict,
        duration: int | None = None,
        expires_at: str | None = None
    ) -> dict:
        """Create or update a page."""
        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                "SELECT id, display_order FROM pages WHERE screen_id = ? AND name = ?",
                (screen_id, name)
            ) as cursor:
                existing = await cursor.fetchone()

            if existing:
                await db.execute("""
                    UPDATE pages
                    SET content = ?, duration = ?, expires_at = ?, updated_at = ?
                    WHERE screen_id = ? AND name = ?
                """, (json.dumps(payload), duration, expires_at, now, screen_id, name))
                display_order = existing['display_order']
            else:
                async with db.execute(
                    "SELECT COALESCE(MAX(display_order), -1) + 1 FROM pages WHERE screen_id = ?",
                    (screen_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    display_order = row[0] if row else 0

                await db.execute("""
                    INSERT INTO pages (screen_id, name, content, display_order, duration, expires_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (screen_id, name, json.dumps(payload), display_order, duration, expires_at, now, now))

            await db.execute(
                "UPDATE screens SET last_updated = ? WHERE id = ?",
                (now, screen_id)
            )
            await db.commit()

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
                "expires_at": expires_at
            }

    async def get_all_pages(
        self,
        screen_id: str,
        include_expired: bool = False
    ) -> list[dict]:
        """Get all pages for a screen."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if include_expired:
                query = "SELECT * FROM pages WHERE screen_id = ? ORDER BY display_order"
                params = (screen_id,)
            else:
                now = datetime.now(timezone.utc).isoformat()
                query = """
                    SELECT * FROM pages
                    WHERE screen_id = ? AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY display_order
                """
                params = (screen_id, now)

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

            pages = []
            for row in rows:
                content_data = json.loads(row['content'])
                pages.append({
                    "name": row['name'],
                    "content": content_data.get("content", []),
                    "background_color": content_data.get("background_color"),
                    "panel_color": content_data.get("panel_color"),
                    "font_family": content_data.get("font_family"),
                    "font_color": content_data.get("font_color"),
                    "gap": content_data.get("gap"),
                    "border_radius": content_data.get("border_radius"),
                    "panel_shadow": content_data.get("panel_shadow"),
                    "display_order": row['display_order'],
                    "duration": row['duration'],
                    "expires_at": row['expires_at']
                })
            return pages

    async def get_page(self, screen_id: str, name: str) -> dict | None:
        """Get a specific page by name."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM pages WHERE screen_id = ? AND name = ?",
                (screen_id, name)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return None

            content_data = json.loads(row['content'])
            return {
                "name": row['name'],
                "content": content_data.get("content", []),
                "background_color": content_data.get("background_color"),
                "panel_color": content_data.get("panel_color"),
                "font_family": content_data.get("font_family"),
                "font_color": content_data.get("font_color"),
                "gap": content_data.get("gap"),
                "border_radius": content_data.get("border_radius"),
                "panel_shadow": content_data.get("panel_shadow"),
                "display_order": row['display_order'],
                "duration": row['duration'],
                "expires_at": row['expires_at']
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
        expires_at: str | None = None
    ) -> dict | None:
        """Partially update a page."""
        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM pages WHERE screen_id = ? AND name = ?",
                (screen_id, name)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return None

            existing_data = json.loads(row['content'])

            if content is not None:
                existing_data['content'] = content
            if background_color is not None:
                existing_data['background_color'] = background_color
            if panel_color is not None:
                existing_data['panel_color'] = panel_color
            if font_family is not None:
                existing_data['font_family'] = font_family
            if font_color is not None:
                existing_data['font_color'] = font_color
            if gap is not None:
                existing_data['gap'] = gap
            if border_radius is not None:
                existing_data['border_radius'] = border_radius
            if panel_shadow is not None:
                existing_data['panel_shadow'] = panel_shadow

            new_duration = duration if duration is not None else row['duration']
            new_expires_at = expires_at if expires_at is not None else row['expires_at']

            await db.execute("""
                UPDATE pages SET content = ?, duration = ?, expires_at = ?, updated_at = ?
                WHERE screen_id = ? AND name = ?
            """, (json.dumps(existing_data), new_duration, new_expires_at, now, screen_id, name))

            await db.execute(
                "UPDATE screens SET last_updated = ? WHERE id = ?",
                (now, screen_id)
            )
            await db.commit()

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
                "display_order": row['display_order'],
                "duration": new_duration,
                "expires_at": new_expires_at
            }

    async def delete_page(self, screen_id: str, name: str) -> bool:
        """Delete a page. Cannot delete 'default'."""
        if name == "default":
            return False

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id FROM pages WHERE screen_id = ? AND name = ?",
                (screen_id, name)
            ) as cursor:
                if not await cursor.fetchone():
                    return False

            await db.execute(
                "DELETE FROM pages WHERE screen_id = ? AND name = ?",
                (screen_id, name)
            )
            await db.commit()
            return True

    async def reorder_pages(self, screen_id: str, page_names: list[str]) -> bool:
        """Reorder pages by setting display_order based on position in list."""
        async with aiosqlite.connect(self.db_path) as db:
            for order, name in enumerate(page_names):
                await db.execute(
                    "UPDATE pages SET display_order = ? WHERE screen_id = ? AND name = ?",
                    (order, screen_id, name)
                )
            await db.commit()
            return True

    async def cleanup_expired_pages(self) -> list[tuple[str, str]]:
        """Remove expired pages."""
        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT screen_id, name FROM pages WHERE expires_at IS NOT NULL AND expires_at <= ? AND name != 'default'",
                (now,)
            ) as cursor:
                expired = await cursor.fetchall()

            if expired:
                await db.execute(
                    "DELETE FROM pages WHERE expires_at IS NOT NULL AND expires_at <= ? AND name != 'default'",
                    (now,)
                )
                await db.commit()

            return [(row[0], row[1]) for row in expired]

    # ============== Theme Methods ==============

    async def get_all_themes(
        self,
        limit: int | None = None,
        offset: int = 0,
        owner_id: str | None = None
    ) -> list[dict]:
        """Get themes with optional pagination."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if owner_id is not None:
                query = "SELECT * FROM themes WHERE owner_id IS NULL OR owner_id = ? ORDER BY is_builtin DESC, name"
                params = [owner_id]
            else:
                query = "SELECT * FROM themes ORDER BY is_builtin DESC, name"
                params = []

            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

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
                    "is_builtin": bool(row["is_builtin"]),
                }
                for row in rows
            ]

    async def get_themes_count(self, owner_id: str | None = None) -> int:
        """Get total count of themes."""
        async with aiosqlite.connect(self.db_path) as db:
            if owner_id is not None:
                query = "SELECT COUNT(*) FROM themes WHERE owner_id IS NULL OR owner_id = ?"
                params = (owner_id,)
            else:
                query = "SELECT COUNT(*) FROM themes"
                params = ()

            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_theme(self, name: str) -> dict | None:
        """Get a theme by name."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM themes WHERE name = ?", (name,)
            ) as cursor:
                row = await cursor.fetchone()

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
                "is_builtin": bool(row["is_builtin"]),
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
        owner_id: str | None = None
    ) -> dict:
        """Create a new custom theme."""
        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO themes (name, display_name, owner_id, background_color, panel_color, font_family,
                                  font_color, gap, border_radius, panel_shadow, is_builtin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (
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
                now
            ))
            await db.commit()

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
        panel_shadow: str | None = None
    ) -> dict | None:
        """Update a theme."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM themes WHERE name = ?", (name,)
            ) as cursor:
                if not await cursor.fetchone():
                    return None

            updates = []
            params = []

            if display_name is not None:
                updates.append("display_name = ?")
                params.append(display_name)
            if background_color is not None:
                updates.append("background_color = ?")
                params.append(background_color)
            if panel_color is not None:
                updates.append("panel_color = ?")
                params.append(panel_color)
            if font_family is not None:
                updates.append("font_family = ?")
                params.append(font_family)
            if font_color is not None:
                updates.append("font_color = ?")
                params.append(font_color)
            if gap is not None:
                updates.append("gap = ?")
                params.append(gap)
            if border_radius is not None:
                updates.append("border_radius = ?")
                params.append(border_radius)
            if panel_shadow is not None:
                updates.append("panel_shadow = ?")
                params.append(panel_shadow)

            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())
                params.append(name)
                await db.execute(
                    f"UPDATE themes SET {', '.join(updates)} WHERE name = ?",
                    params
                )
                await db.commit()

        return await self.get_theme(name)

    async def delete_theme(self, name: str) -> tuple[bool, str | None]:
        """Delete a theme if not in use."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT is_builtin FROM themes WHERE name = ?", (name,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return False, "Theme not found"

            async with db.execute(
                "SELECT COUNT(*) FROM screens WHERE theme = ?", (name,)
            ) as cursor:
                usage_count = (await cursor.fetchone())[0]

            if usage_count > 0:
                return False, f"Theme is in use by {usage_count} screen(s)"

            await db.execute("DELETE FROM themes WHERE name = ?", (name,))
            await db.commit()

        return True, None

    async def get_theme_usage_counts(self) -> dict[str, int]:
        """Get usage count for all themes."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT theme, COUNT(*) FROM screens WHERE theme IS NOT NULL GROUP BY theme"
            ) as cursor:
                rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}
