import aiosqlite
import json
from pathlib import Path

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

        # Migration: Add name and last_updated columns if they don't exist
        async with db.execute("PRAGMA table_info(screens)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if 'name' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN name TEXT")
        if 'last_updated' not in columns:
            await db.execute("ALTER TABLE screens ADD COLUMN last_updated TEXT")

        await db.commit()


async def create_screen(screen_id: str, api_key: str, created_at: str, name: str | None = None) -> None:
    """Create a new screen."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO screens (id, api_key, created_at, name) VALUES (?, ?, ?, ?)",
            (screen_id, api_key, created_at, name)
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
