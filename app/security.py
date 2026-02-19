"""Security utilities for API key handling."""

import hashlib
import hmac

from .config import get_settings


def hash_account_api_key(api_key: str) -> str:
    """Hash an account API key for at-rest storage and lookup."""
    settings = get_settings()
    secret = (settings.ACCOUNT_API_KEY_PEPPER or settings.CLERK_SECRET_KEY or "").encode("utf-8")
    digest = hmac.new(secret, api_key.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"v1:{digest}"


def make_api_key_preview(api_key: str) -> str:
    """Create a non-sensitive key preview for UI display."""
    if len(api_key) <= 12:
        return api_key[:4] + "..." + api_key[-4:]
    return api_key[:7] + "..." + api_key[-4:]
