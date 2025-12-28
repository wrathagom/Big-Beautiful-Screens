"""AWS S3 storage backend."""

import uuid

import aioboto3

from app.config import get_settings
from app.storage.base import StorageBackend, UploadResult
from app.storage.local import sanitize_filename


class S3Storage(StorageBackend):
    """AWS S3 storage backend."""

    def __init__(
        self,
        bucket: str | None = None,
        region: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        public_url: str | None = None,
    ):
        """
        Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            region: AWS region (default: us-east-1)
            access_key: AWS access key ID
            secret_key: AWS secret access key
            endpoint_url: Custom endpoint URL (for S3-compatible services)
            public_url: Custom public URL for accessing files (CDN or custom domain)
        """
        settings = get_settings()

        self.bucket = bucket or settings.STORAGE_S3_BUCKET
        self.region = region or settings.STORAGE_S3_REGION
        self.access_key = access_key or settings.STORAGE_S3_ACCESS_KEY
        self.secret_key = secret_key or settings.STORAGE_S3_SECRET_KEY
        self.endpoint_url = endpoint_url or settings.STORAGE_S3_ENDPOINT_URL
        self.public_url = public_url or settings.STORAGE_S3_PUBLIC_URL

        if not self.bucket:
            raise ValueError("S3 bucket name is required (STORAGE_S3_BUCKET)")

        self._session = aioboto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

    def _get_client_kwargs(self) -> dict:
        """Get kwargs for creating S3 client."""
        kwargs = {}
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        return kwargs

    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        owner_id: str | None = None,
    ) -> UploadResult:
        """Upload a file to S3."""
        # Generate unique path
        file_id = str(uuid.uuid4())
        safe_filename = sanitize_filename(filename)

        # Create storage path: {owner_id}/{file_id}/{filename}
        if owner_id:
            storage_path = f"{owner_id}/{file_id}/{safe_filename}"
        else:
            storage_path = f"{file_id}/{safe_filename}"

        # Upload to S3
        async with self._session.client("s3", **self._get_client_kwargs()) as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=storage_path,
                Body=file_data,
                ContentType=content_type,
            )

        return UploadResult(
            storage_path=storage_path,
            public_url=self.get_public_url(storage_path),
            size_bytes=len(file_data),
        )

    async def delete(self, storage_path: str) -> bool:
        """Delete a file from S3."""
        async with self._session.client("s3", **self._get_client_kwargs()) as s3:
            try:
                await s3.delete_object(Bucket=self.bucket, Key=storage_path)
                return True
            except Exception:
                return False

    def get_public_url(self, storage_path: str) -> str:
        """Get the public URL for a stored file."""
        if self.public_url:
            # Use custom public URL (CDN or custom domain)
            return f"{self.public_url.rstrip('/')}/{storage_path}"

        # Use default S3 URL
        if self.endpoint_url:
            # Custom endpoint (e.g., MinIO)
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket}/{storage_path}"

        # Standard AWS S3 URL
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{storage_path}"

    async def exists(self, storage_path: str) -> bool:
        """Check if a file exists in S3."""
        async with self._session.client("s3", **self._get_client_kwargs()) as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=storage_path)
                return True
            except Exception:
                return False
