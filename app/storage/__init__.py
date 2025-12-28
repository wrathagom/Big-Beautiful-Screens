"""Storage backend module with factory function."""

from functools import lru_cache

from app.config import StorageBackendType, get_settings
from app.storage.base import StorageBackend, UploadResult
from app.storage.local import LocalStorage

__all__ = [
    "StorageBackend",
    "UploadResult",
    "get_storage",
    "LocalStorage",
    "S3Storage",
    "R2Storage",
]


# Lazy imports for S3 and R2 to avoid requiring boto3 when not used
def __getattr__(name: str):
    if name == "S3Storage":
        from app.storage.s3 import S3Storage

        return S3Storage
    elif name == "R2Storage":
        from app.storage.r2 import R2Storage

        return R2Storage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@lru_cache
def get_storage() -> StorageBackend:
    """
    Get the configured storage backend.

    Returns the appropriate storage backend based on STORAGE_BACKEND setting.
    Result is cached for the lifetime of the application.
    """
    settings = get_settings()
    backend_type: StorageBackendType = settings.STORAGE_BACKEND

    if backend_type == "local":
        return LocalStorage()
    elif backend_type == "s3":
        # Import here to avoid requiring boto3 when not using S3
        from app.storage.s3 import S3Storage

        return S3Storage()
    elif backend_type == "r2":
        # Import here to avoid requiring boto3 when not using R2
        from app.storage.r2 import R2Storage

        return R2Storage()
    else:
        raise ValueError(f"Unknown storage backend: {backend_type}")


def clear_storage_cache() -> None:
    """Clear the storage backend cache. Useful for testing."""
    get_storage.cache_clear()
