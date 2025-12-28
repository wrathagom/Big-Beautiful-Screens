"""Cloudflare R2 storage backend.

R2 is S3-compatible, so this extends the S3 storage backend with R2-specific
configuration defaults.
"""

from app.config import get_settings
from app.storage.s3 import S3Storage


class R2Storage(S3Storage):
    """Cloudflare R2 storage backend.

    R2 is S3-compatible but uses Cloudflare's global network.
    Requires a public domain to be configured for public access.
    """

    def __init__(
        self,
        bucket: str | None = None,
        account_id: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        public_domain: str | None = None,
    ):
        """
        Initialize R2 storage.

        Args:
            bucket: R2 bucket name
            account_id: Cloudflare account ID
            access_key: R2 access key ID
            secret_key: R2 secret access key
            public_domain: Public domain for accessing files (required for public access)
        """
        settings = get_settings()

        bucket = bucket or settings.STORAGE_R2_BUCKET
        account_id = account_id or settings.STORAGE_R2_ACCOUNT_ID
        access_key = access_key or settings.STORAGE_R2_ACCESS_KEY
        secret_key = secret_key or settings.STORAGE_R2_SECRET_KEY
        public_domain = public_domain or settings.STORAGE_R2_PUBLIC_DOMAIN

        if not bucket:
            raise ValueError("R2 bucket name is required (STORAGE_R2_BUCKET)")
        if not account_id:
            raise ValueError("Cloudflare account ID is required (STORAGE_R2_ACCOUNT_ID)")

        # R2 endpoint format
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

        # Public URL from custom domain
        public_url = None
        if public_domain:
            # Ensure https:// prefix
            if not public_domain.startswith("http"):
                public_domain = f"https://{public_domain}"
            public_url = public_domain

        # Initialize parent S3 storage
        super().__init__(
            bucket=bucket,
            region="auto",  # R2 uses "auto" for region
            access_key=access_key,
            secret_key=secret_key,
            endpoint_url=endpoint_url,
            public_url=public_url,
        )

        # Store for reference
        self.account_id = account_id
        self.public_domain = public_domain

    def get_public_url(self, storage_path: str) -> str:
        """Get the public URL for a stored file.

        R2 requires a custom domain for public access.
        """
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{storage_path}"

        # R2 without public domain - files are not publicly accessible
        # Return the internal path; the app will need to proxy or generate signed URLs
        return f"/media/files/{storage_path}"
