"""Application configuration with environment-based settings."""

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class AppMode(str, Enum):
    SELF_HOSTED = "self-hosted"
    SAAS = "saas"


# Storage backend type
StorageBackendType = Literal["local", "s3", "r2"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application mode
    APP_MODE: AppMode = AppMode.SELF_HOSTED

    # Database settings
    DATABASE_URL: str | None = None  # PostgreSQL connection string for SaaS
    SQLITE_PATH: str = "data/screens.db"  # SQLite path for self-hosted

    # Clerk settings (SaaS mode only)
    CLERK_SECRET_KEY: str | None = None
    CLERK_PUBLISHABLE_KEY: str | None = None
    CLERK_WEBHOOK_SECRET: str | None = None
    CLERK_SIGN_IN_URL: str | None = None  # e.g., https://your-app.accounts.dev/sign-in
    CLERK_JWKS_URL: str | None = None  # From Clerk Dashboard → API Keys

    # Feature flags
    REQUIRE_AUTH_FOR_ADMIN: bool = False  # Auto-set True in SaaS mode

    # Stripe billing
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PUBLISHABLE_KEY: str | None = None
    STRIPE_PRICING_TABLE_ID: str | None = None
    STRIPE_PRICE_STARTER_MONTHLY: str | None = None
    STRIPE_PRICE_STARTER_YEARLY: str | None = None
    STRIPE_PRICE_PREMIUM_MONTHLY: str | None = None
    STRIPE_PRICE_PREMIUM_YEARLY: str | None = None

    # Usage logging
    USAGE_LOG_DESTINATION: str = "stdout"  # stdout, file, or external
    USAGE_LOG_FILE_PATH: str = "logs/usage.log"

    # App URL (for Stripe redirects)
    APP_URL: str = "http://localhost:8000"

    # Media Storage Backend
    STORAGE_BACKEND: StorageBackendType = "local"

    # Local Storage Settings
    STORAGE_LOCAL_PATH: str = "data/media"

    # S3 Storage Settings
    STORAGE_S3_BUCKET: str | None = None
    STORAGE_S3_REGION: str = "us-east-1"
    STORAGE_S3_ACCESS_KEY: str | None = None
    STORAGE_S3_SECRET_KEY: str | None = None
    STORAGE_S3_ENDPOINT_URL: str | None = None  # Custom endpoint for S3-compatible services
    STORAGE_S3_PUBLIC_URL: str | None = None  # Custom domain/CDN for public URLs

    # Cloudflare R2 Storage Settings
    STORAGE_R2_BUCKET: str | None = None
    STORAGE_R2_ACCOUNT_ID: str | None = None
    STORAGE_R2_ACCESS_KEY: str | None = None
    STORAGE_R2_SECRET_KEY: str | None = None
    STORAGE_R2_PUBLIC_DOMAIN: str | None = None  # Required for public access

    # Media Upload Limits
    MAX_UPLOAD_SIZE_MB: int = 250

    # Help button (shown on admin pages)
    HELP_URL: str = "https://github.com/wrathagom/Big-Beautiful-Screens/issues"
    HELP_TEXT: str | None = None  # Auto-set based on mode if not specified

    # Debug logging
    AUTH_DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def is_saas(self) -> bool:
        """Check if running in SaaS mode."""
        return self.APP_MODE == AppMode.SAAS

    @property
    def is_self_hosted(self) -> bool:
        """Check if running in self-hosted mode."""
        return self.APP_MODE == AppMode.SELF_HOSTED

    def validate_saas_config(self) -> list[str]:
        """Validate that required SaaS settings are present. Returns list of missing settings."""
        if not self.is_saas:
            return []

        missing = []
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        if not self.CLERK_SECRET_KEY:
            missing.append("CLERK_SECRET_KEY")
        if not self.CLERK_PUBLISHABLE_KEY:
            missing.append("CLERK_PUBLISHABLE_KEY")
        return missing


# Plan limits lookup (includes resource counts and API quotas)
PLAN_LIMITS = {
    "free": {
        "screens": 3,
        "themes": 200,
        "pages_per_screen": 5,
        "api_calls_daily": 100,
        "media_enabled": False,
        "storage_bytes": 0,
    },
    "starter": {
        "screens": 25,
        "themes": 200,
        "pages_per_screen": 50,
        "api_calls_daily": 1000,
        "media_enabled": True,
        "storage_bytes": 1073741824,  # 1GB
    },
    "premium": {
        "screens": 100,
        "themes": 200,
        "pages_per_screen": 100,
        "api_calls_daily": -1,
        "media_enabled": True,
        "storage_bytes": 10737418240,  # 10GB
    },
}

# Allowed media file types
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
ALLOWED_MEDIA_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
