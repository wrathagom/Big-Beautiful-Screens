"""Database abstraction layer for Big Beautiful Screens.

Supports SQLite (self-hosted) and PostgreSQL (SaaS) backends.
"""

from .factory import get_database, init_db

__all__ = ["get_database", "init_db"]
