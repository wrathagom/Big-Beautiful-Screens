"""Database factory for Big Beautiful Screens.

Returns the appropriate database backend based on configuration.
"""

from ..config import AppMode, get_settings
from .base import DatabaseBackend

# Singleton instance
_db_instance: DatabaseBackend | None = None


def get_database() -> DatabaseBackend:
    """Get the database backend instance.

    Returns SQLite in self-hosted mode, PostgreSQL in SaaS mode.
    """
    global _db_instance

    if _db_instance is not None:
        return _db_instance

    settings = get_settings()

    if settings.APP_MODE == AppMode.SAAS:
        from .postgres import PostgresBackend

        _db_instance = PostgresBackend()
    else:
        from .sqlite import SQLiteBackend

        _db_instance = SQLiteBackend()

    return _db_instance


async def init_db() -> None:
    """Initialize the database.

    Creates tables and seeds data if needed.
    """
    db = get_database()
    await db.init()


def reset_database() -> None:
    """Reset the database instance.

    Useful for testing or when configuration changes.
    """
    global _db_instance
    _db_instance = None
