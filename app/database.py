import aiosqlite
import json
from pathlib import Path
from datetime import datetime, timezone

from .themes import get_theme

DB_PATH = Path(__file__).parent.parent / "data" / "screens.db"


async def init_db():
    """Initialize the database and create tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS screens (
                id TEXT PRIMARY KEY,
                api_key TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                name TEXT,
                last_updated TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screen_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (screen_id) REFERENCES screens(id)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_screen_id
            ON messages(screen_id)
        """)

        # Pages table for multi-page rotation support
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
                FOREIGN KEY (screen_id) REFERENCES screens(id),
                UNIQUE(screen_id, name)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_pages_screen_id
            ON pages(screen_id)
        """)

        # Migration: Add name and last_updated columns if they don't exist
        async with db.execute("PRAGMA table_info(screens)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if 'name' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN name TEXT")
        if 'last_updated' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN last_updated TEXT")
        if 'rotation_enabled' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN rotation_enabled INTEGER DEFAULT 0")
        if 'rotation_interval' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN rotation_interval INTEGER DEFAULT 30")
        if 'gap' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN gap TEXT DEFAULT '1rem'")
        if 'border_radius' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN border_radius TEXT DEFAULT '1rem'")
        if 'panel_shadow' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN panel_shadow TEXT")
        if 'background_color' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN background_color TEXT")
        if 'panel_color' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN panel_color TEXT")
        if 'font_family' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN font_family TEXT")
        if 'font_color' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN font_color TEXT")
        if 'theme' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN theme TEXT")
        if 'head_html' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN head_html TEXT")

        # Migration: Move existing messages to pages table as "default" page
        await _migrate_messages_to_pages(db)

        await db.commit()


async def _migrate_messages_to_pages(db):
    """Migrate existing messages to the pages table as default pages."""
    # Check if there are messages that haven't been migrated
    async with db.execute("""
        SELECT m.screen_id, m.content, m.created_at
        FROM messages m
        LEFT JOIN pages p ON m.screen_id = p.screen_id AND p.name = 'default'
        WHERE p.id IS NULL
    """) as cursor:
        messages_to_migrate = await cursor.fetchall()

    for screen_id, content, created_at in messages_to_migrate:
        await db.execute("""
            INSERT INTO pages (screen_id, name, content, display_order, created_at, updated_at)
            VALUES (?, 'default', ?, 0, ?, ?)
        """, (screen_id, content, created_at, created_at))


async def create_screen(screen_id: str, api_key: str, created_at: str, name: str | None = None) -> None:
    """Create a new screen with default theme applied."""
    default_theme = get_theme("default")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO screens (
                id, api_key, created_at, name, theme,
                background_color, panel_color, font_family, font_color,
                gap, border_radius, panel_shadow
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                screen_id, api_key, created_at, name, "default",
                default_theme["background_color"],
                default_theme["panel_color"],
                default_theme["font_family"],
                default_theme["font_color"],
                default_theme["gap"],
                default_theme["border_radius"],
                default_theme["panel_shadow"],
            )
        )
        await db.commit()


async def get_screen_by_id(screen_id: str) -> dict | None:
    """Get a screen by its ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM screens WHERE id = ?", (screen_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_screen_by_api_key(api_key: str) -> dict | None:
    """Get a screen by its API key."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM screens WHERE api_key = ?", (api_key,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def save_message(screen_id: str, payload: dict, created_at: str) -> None:
    """Save a message for a screen (replaces any existing message).

    payload should contain: content, background_color, panel_color
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Delete old messages for this screen (keep only the latest)
        await db.execute("DELETE FROM messages WHERE screen_id = ?", (screen_id,))
        # Insert new message
        await db.execute(
            "INSERT INTO messages (screen_id, content, created_at) VALUES (?, ?, ?)",
            (screen_id, json.dumps(payload), created_at)
        )
        # Update last_updated on the screen
        await db.execute(
            "UPDATE screens SET last_updated = ? WHERE id = ?",
            (created_at, screen_id)
        )
        await db.commit()


async def get_last_message(screen_id: str) -> dict | None:
    """Get the last message for a screen.

    Returns dict with: content, background_color, panel_color
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT content FROM messages WHERE screen_id = ? ORDER BY id DESC LIMIT 1",
            (screen_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else None


async def get_all_screens() -> list[dict]:
    """Get all screens."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM screens ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def delete_screen(screen_id: str) -> bool:
    """Delete a screen and its messages.

    Returns True if deleted, False if screen not found.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if screen exists
        async with db.execute(
            "SELECT id FROM screens WHERE id = ?", (screen_id,)
        ) as cursor:
            if not await cursor.fetchone():
                return False

        # Delete messages first (foreign key)
        await db.execute("DELETE FROM messages WHERE screen_id = ?", (screen_id,))
        # Delete screen
        await db.execute("DELETE FROM screens WHERE id = ?", (screen_id,))
        await db.commit()
        return True


async def update_screen_name(screen_id: str, name: str | None) -> bool:
    """Update a screen's name.

    Returns True if updated, False if screen not found.
    """
    async with aiosqlite.connect(DB_PATH) as db:
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


# ============== Page Functions ==============

async def upsert_page(
    screen_id: str,
    name: str,
    payload: dict,
    duration: int | None = None,
    expires_at: str | None = None
) -> dict:
    """Create or update a page.

    payload should contain: content, background_color, panel_color, font_family, font_color
    Returns the page data.
    """
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Check if page exists
        async with db.execute(
            "SELECT id, display_order FROM pages WHERE screen_id = ? AND name = ?",
            (screen_id, name)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            # Update existing page
            await db.execute("""
                UPDATE pages
                SET content = ?, duration = ?, expires_at = ?, updated_at = ?
                WHERE screen_id = ? AND name = ?
            """, (json.dumps(payload), duration, expires_at, now, screen_id, name))
            display_order = existing['display_order']
        else:
            # Get next display_order
            async with db.execute(
                "SELECT COALESCE(MAX(display_order), -1) + 1 FROM pages WHERE screen_id = ?",
                (screen_id,)
            ) as cursor:
                row = await cursor.fetchone()
                display_order = row[0] if row else 0

            # Insert new page
            await db.execute("""
                INSERT INTO pages (screen_id, name, content, display_order, duration, expires_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (screen_id, name, json.dumps(payload), display_order, duration, expires_at, now, now))

        # Update screen's last_updated
        await db.execute(
            "UPDATE screens SET last_updated = ? WHERE id = ?",
            (now, screen_id)
        )

        await db.commit()

        # Return the page data
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


async def get_all_pages(screen_id: str, include_expired: bool = False) -> list[dict]:
    """Get all pages for a screen, ordered by display_order.

    By default, excludes expired pages.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if include_expired:
            query = """
                SELECT * FROM pages
                WHERE screen_id = ?
                ORDER BY display_order
            """
            params = (screen_id,)
        else:
            now = datetime.now(timezone.utc).isoformat()
            query = """
                SELECT * FROM pages
                WHERE screen_id = ?
                AND (expires_at IS NULL OR expires_at > ?)
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


async def get_page(screen_id: str, name: str) -> dict | None:
    """Get a specific page by name."""
    async with aiosqlite.connect(DB_PATH) as db:
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
    """Partially update a page. Only provided fields are updated.

    Returns the updated page data, or None if page not found.
    """
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get existing page
        async with db.execute(
            "SELECT * FROM pages WHERE screen_id = ? AND name = ?",
            (screen_id, name)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        # Parse existing content
        existing_data = json.loads(row['content'])

        # Merge updates (only update fields that are explicitly provided)
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

        # Build update query
        new_duration = duration if duration is not None else row['duration']
        new_expires_at = expires_at if expires_at is not None else row['expires_at']

        await db.execute("""
            UPDATE pages
            SET content = ?, duration = ?, expires_at = ?, updated_at = ?
            WHERE screen_id = ? AND name = ?
        """, (json.dumps(existing_data), new_duration, new_expires_at, now, screen_id, name))

        # Update screen's last_updated
        await db.execute(
            "UPDATE screens SET last_updated = ? WHERE id = ?",
            (now, screen_id)
        )

        await db.commit()

        # Return updated page data
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


async def delete_page(screen_id: str, name: str) -> bool:
    """Delete a page. Cannot delete the 'default' page.

    Returns True if deleted, False if not found or is default.
    """
    if name == "default":
        return False

    async with aiosqlite.connect(DB_PATH) as db:
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


async def reorder_pages(screen_id: str, page_names: list[str]) -> bool:
    """Reorder pages by setting display_order based on position in list.

    Returns True if successful.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        for order, name in enumerate(page_names):
            await db.execute(
                "UPDATE pages SET display_order = ? WHERE screen_id = ? AND name = ?",
                (order, screen_id, name)
            )
        await db.commit()
        return True


async def get_rotation_settings(screen_id: str) -> dict | None:
    """Get rotation/display settings for a screen."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            """SELECT rotation_enabled, rotation_interval, gap, border_radius, panel_shadow,
                      background_color, panel_color, font_family, font_color, theme, head_html
               FROM screens WHERE id = ?""",
            (screen_id,)
        ) as cursor:
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
    """Update rotation/display settings for a screen.

    Returns True if updated, False if screen not found.
    """
    async with aiosqlite.connect(DB_PATH) as db:
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


async def cleanup_expired_pages() -> list[tuple[str, str]]:
    """Remove expired pages from all screens.

    Returns list of (screen_id, page_name) tuples for deleted pages.
    """
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        # Find expired pages
        async with db.execute(
            "SELECT screen_id, name FROM pages WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,)
        ) as cursor:
            expired = await cursor.fetchall()

        if expired:
            # Delete expired pages (but never delete 'default')
            await db.execute(
                "DELETE FROM pages WHERE expires_at IS NOT NULL AND expires_at <= ? AND name != 'default'",
                (now,)
            )
            await db.commit()

        return [(row[0], row[1]) for row in expired if row[1] != 'default']
