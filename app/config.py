"""Application configuration with environment-based settings."""

from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings


class AppMode(str, Enum):
    SELF_HOSTED = "self-hosted"
    SAAS = "saas"


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

    # Feature flags
    REQUIRE_AUTH_FOR_ADMIN: bool = False  # Auto-set True in SaaS mode

    # Billing tiers (future)
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None

    # Plan limits
    FREE_TIER_SCREEN_LIMIT: int = 3
    FREE_TIER_THEME_LIMIT: int = 5
    PRO_TIER_SCREEN_LIMIT: int = 25
    PRO_TIER_THEME_LIMIT: int = 50
    TEAM_TIER_SCREEN_LIMIT: int = 100
    TEAM_TIER_THEME_LIMIT: int = 200

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


# Plan limits lookup
PLAN_LIMITS = {
    "free": {"screens": 3, "themes": 5, "pages_per_screen": 5},
    "pro": {"screens": 25, "themes": 50, "pages_per_screen": 50},
    "team": {"screens": 100, "themes": 200, "pages_per_screen": 100},
}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
