"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class UploadResult:
    """Result of a successful file upload."""

    storage_path: str  # Path within the storage backend
    public_url: str  # Publicly accessible URL
    size_bytes: int  # File size in bytes


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        owner_id: str | None = None,
    ) -> UploadResult:
        """
        Upload a file to storage.

        Args:
            file_data: Raw file bytes
            filename: Original filename (will be sanitized)
            content_type: MIME type of the file
            owner_id: Optional owner ID for organizing files

        Returns:
            UploadResult with storage path, public URL, and size
        """
        pass

    @abstractmethod
    async def upload_stream(
        self,
        file_stream: AsyncIterator[bytes],
        filename: str,
        content_type: str,
        owner_id: str | None = None,
    ) -> UploadResult:
        """
        Upload a file to storage from an async byte stream.

        Args:
            file_stream: Async iterator yielding file chunks
            filename: Original filename (will be sanitized)
            content_type: MIME type of the file
            owner_id: Optional owner ID for organizing files

        Returns:
            UploadResult with storage path, public URL, and size
        """
        pass

    @abstractmethod
    async def delete(self, storage_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            storage_path: Path returned from upload

        Returns:
            True if deleted, False if file didn't exist
        """
        pass

    @abstractmethod
    def get_public_url(self, storage_path: str) -> str:
        """
        Get the public URL for a stored file.

        Args:
            storage_path: Path returned from upload

        Returns:
            Publicly accessible URL
        """
        pass

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            storage_path: Path to check

        Returns:
            True if file exists
        """
        pass
