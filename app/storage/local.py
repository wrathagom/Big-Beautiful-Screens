"""Local filesystem storage backend."""

import os
import re
import uuid
from pathlib import Path

import aiofiles
import aiofiles.os

from app.config import get_settings
from app.storage.base import StorageBackend, UploadResult


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other issues."""
    # Remove path components
    filename = os.path.basename(filename)
    # Remove potentially dangerous characters, keep only safe ones
    filename = re.sub(r"[^\w\-_\.]", "_", filename)
    # Prevent empty filenames
    if not filename or filename.startswith("."):
        filename = f"file_{filename}"
    return filename


class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str | None = None, base_url: str | None = None):
        """
        Initialize local storage.

        Args:
            base_path: Base directory for file storage
            base_url: Base URL for serving files (e.g., http://localhost:8000)
        """
        settings = get_settings()
        self.base_path = Path(base_path or settings.STORAGE_LOCAL_PATH)
        self.base_url = (base_url or settings.APP_URL).rstrip("/")

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._resolved_base_path = self.base_path.resolve()

    def _resolve_storage_path(self, storage_path: str) -> Path:
        """Resolve and validate that path stays under the storage base directory."""
        candidate = (self._resolved_base_path / storage_path).resolve()
        if not str(candidate).startswith(str(self._resolved_base_path) + os.sep):
            raise ValueError("Invalid storage path")
        return candidate

    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        owner_id: str | None = None,
    ) -> UploadResult:
        """Upload a file to local storage."""
        # Generate unique ID and sanitize filename
        file_id = str(uuid.uuid4())
        safe_filename = sanitize_filename(filename)

        # Create storage path: {owner_id}/{file_id}/{filename}
        # This structure allows easy organization and prevents collisions
        storage_dir = self.base_path / owner_id / file_id if owner_id else self.base_path / file_id

        await aiofiles.os.makedirs(storage_dir, exist_ok=True)

        file_path = storage_dir / safe_filename
        storage_path = str(file_path.relative_to(self.base_path))

        # Write file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_data)

        return UploadResult(
            storage_path=storage_path,
            public_url=self.get_public_url(storage_path),
            size_bytes=len(file_data),
        )

    async def delete(self, storage_path: str) -> bool:
        """Delete a file from local storage."""
        try:
            file_path = self._resolve_storage_path(storage_path)
        except ValueError:
            return False

        if not file_path.exists():
            return False

        # Delete the file
        await aiofiles.os.remove(file_path)

        # Try to clean up empty parent directories
        parent = file_path.parent
        try:
            while parent != self._resolved_base_path:
                if not any(parent.iterdir()):
                    await aiofiles.os.rmdir(parent)
                    parent = parent.parent
                else:
                    break
        except OSError:
            # Directory not empty or other issue, ignore
            pass

        return True

    def get_public_url(self, storage_path: str) -> str:
        """Get the public URL for a stored file."""
        # URL format: /media/files/{storage_path}
        return f"{self.base_url}/media/files/{storage_path}"

    async def exists(self, storage_path: str) -> bool:
        """Check if a file exists in local storage."""
        try:
            file_path = self._resolve_storage_path(storage_path)
        except ValueError:
            return False
        return file_path.exists() and file_path.is_file()

    def get_file_path(self, storage_path: str) -> Path:
        """Get the full filesystem path for a stored file."""
        return self._resolve_storage_path(storage_path)
