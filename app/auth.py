"""Authentication module for Big Beautiful Screens.

Handles Clerk JWT verification in SaaS mode.
In self-hosted mode, authentication is bypassed.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote

import httpx
from fastapi import Depends, Header, HTTPException, Request

from .config import AppMode, get_settings


def get_clerk_sign_in_url(redirect_url: str) -> str:
    """Get the Clerk sign-in URL with redirect."""
    settings = get_settings()

    if not settings.CLERK_SIGN_IN_URL:
        # Fallback if not configured
        return f"/sign-in?redirect_url={redirect_url}"

    app_url = settings.APP_URL.rstrip("/")
    full_redirect = f"{app_url}{redirect_url}"
    sign_in_base = settings.CLERK_SIGN_IN_URL.rstrip("/")

    return f"{sign_in_base}?redirect_url={quote(full_redirect)}"


@dataclass
class AuthUser:
    """Authenticated user information."""

    user_id: str
    email: str | None = None
    name: str | None = None
    org_id: str | None = None
    org_role: str | None = None  # 'owner', 'admin', 'member'


# Clerk JWKS cache
_jwks_cache: dict | None = None
_jwks_cache_time: datetime | None = None
JWKS_CACHE_TTL = 3600  # 1 hour


async def _get_clerk_jwks() -> dict:
    """Fetch Clerk's JWKS (JSON Web Key Set) for JWT verification."""
    global _jwks_cache, _jwks_cache_time

    now = datetime.now(UTC)

    # Return cached JWKS if still valid
    if _jwks_cache and _jwks_cache_time:
        age = (now - _jwks_cache_time).total_seconds()
        if age < JWKS_CACHE_TTL:
            return _jwks_cache

    settings = get_settings()
    if not settings.CLERK_PUBLISHABLE_KEY:
        raise ValueError("CLERK_PUBLISHABLE_KEY not configured")

    # Extract frontend API from publishable key (pk_live_xxx or pk_test_xxx)
    # The key contains the frontend API domain encoded in base64
    try:
        # Clerk publishable keys are formatted as pk_[env]_[base64_encoded_frontend_api]
        parts = settings.CLERK_PUBLISHABLE_KEY.split("_")
        if len(parts) >= 3:
            import base64

            encoded = parts[2]
            # Add padding if needed
            padding = 4 - len(encoded) % 4
            if padding != 4:
                encoded += "=" * padding
            frontend_api = base64.b64decode(encoded).decode("utf-8")
        else:
            raise ValueError("Invalid publishable key format")
    except Exception:
        # Fallback: Use standard Clerk API
        frontend_api = "clerk.accounts.dev"

    jwks_url = f"https://{frontend_api}/.well-known/jwks.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = now
        return _jwks_cache


async def _verify_clerk_jwt(token: str) -> dict | None:
    """Verify a Clerk JWT and return the claims.

    Returns None if verification fails.
    """
    try:
        # Import jwt library for verification
        import jwt

        # Get JWKS
        jwks = await _get_clerk_jwks()

        # Find the signing key
        # Clerk uses RS256
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        signing_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break

        if not signing_key:
            return None

        # Verify the token
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk doesn't always set aud
        )

        return claims

    except Exception as e:
        # Log error in production
        print(f"JWT verification failed: {e}")
        return None


def _extract_token(request: Request) -> str | None:
    """Extract JWT token from request (cookie or Authorization header)."""
    # Try cookie first (for browser sessions)
    token = request.cookies.get("__session")
    if token:
        return token

    # Try Authorization header (for API calls)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


async def get_current_user(request: Request) -> AuthUser | None:
    """Get the current authenticated user, or None if not authenticated.

    This is a soft auth check - it doesn't raise an error if not authenticated.
    Use this for endpoints that work differently for authenticated vs anonymous users.
    """
    settings = get_settings()

    # In self-hosted mode, return None (no authentication)
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return None

    token = _extract_token(request)
    if not token:
        return None

    claims = await _verify_clerk_jwt(token)
    if not claims:
        return None

    # Extract user info from claims
    user_id = claims.get("sub")
    if not user_id:
        return None

    # Get org info if present (from session claims)
    org_id = claims.get("org_id")
    org_role = claims.get("org_role")

    return AuthUser(
        user_id=user_id,
        email=claims.get("email"),
        name=claims.get("name"),
        org_id=org_id,
        org_role=org_role,
    )


async def require_auth(request: Request) -> AuthUser:
    """Require authentication - raises 401 if not authenticated.

    Use this as a dependency for endpoints that require a logged-in user.
    """
    settings = get_settings()

    # In self-hosted mode, authentication is not required
    # Return a dummy user for compatibility
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return AuthUser(user_id="self-hosted", email=None, name="Self-Hosted User")

    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_auth_or_api_key(
    request: Request, x_api_key: str | None = Header(default=None, alias="X-API-Key")
) -> AuthUser | str:
    """Require either Clerk authentication or API key.

    Returns AuthUser if authenticated via Clerk, or the API key string if using API key.
    Raises 401 if neither is provided.
    """
    settings = get_settings()

    # Try API key first (works in both modes)
    if x_api_key:
        return x_api_key

    # In self-hosted mode, API key is the only auth method
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        raise HTTPException(
            status_code=401, detail="API key required", headers={"X-API-Key": "Required"}
        )

    # In SaaS mode, try Clerk auth
    user = await get_current_user(request)
    if user:
        return user

    raise HTTPException(
        status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"}
    )


# FastAPI dependency types
OptionalUser = Annotated[AuthUser | None, Depends(get_current_user)]
RequiredUser = Annotated[AuthUser, Depends(require_auth)]
AuthOrApiKey = Annotated[AuthUser | str, Depends(require_auth_or_api_key)]


# ============== Access Control Helpers ==============


def can_access_screen(user: AuthUser | None, screen: dict) -> bool:
    """Check if a user can access (view) a screen.

    Rules:
    - In self-hosted mode: everyone can access all screens
    - Screen viewer (/screen/{id}) is always public
    - Owner can access their screens
    - Org members can access org screens
    """
    settings = get_settings()

    # Self-hosted mode: no restrictions
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True

    # No ownership set (legacy/public screen)
    if not screen.get("owner_id") and not screen.get("org_id"):
        return True

    # Not authenticated
    if not user:
        return False

    # User is owner
    if screen.get("owner_id") == user.user_id:
        return True

    # User is in the org that owns the screen
    return bool(screen.get("org_id") and screen.get("org_id") == user.org_id)


def can_modify_screen(user: AuthUser | None, screen: dict, api_key: str | None = None) -> bool:
    """Check if a user can modify a screen.

    Rules:
    - Valid API key always grants access
    - Owner can modify their screens
    - Org admins/owners can modify org screens
    """
    settings = get_settings()

    # Valid API key always works
    if api_key and screen.get("api_key") == api_key:
        return True

    # Self-hosted mode with no API key: check not allowed
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return False

    # Not authenticated
    if not user:
        return False

    # User is owner
    if screen.get("owner_id") == user.user_id:
        return True

    # User is admin/owner of the org that owns the screen
    return bool(
        screen.get("org_id")
        and screen.get("org_id") == user.org_id
        and user.org_role in ("admin", "owner")
    )


def can_access_theme(user: AuthUser | None, theme: dict) -> bool:
    """Check if a user can access (view) a theme.

    Rules:
    - Built-in themes are accessible to everyone
    - Global themes (no owner) are accessible to everyone
    - User can access their own themes
    """
    settings = get_settings()

    # Self-hosted mode: no restrictions
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True

    # Built-in or global theme
    if theme.get("is_builtin") or not theme.get("owner_id"):
        return True

    # Not authenticated
    if not user:
        return False

    # User owns the theme
    return theme.get("owner_id") == user.user_id


def can_modify_theme(user: AuthUser | None, theme: dict) -> bool:
    """Check if a user can modify a theme.

    Rules:
    - Built-in themes can be modified in self-hosted mode
    - User can modify their own themes
    - In SaaS mode, built-in themes cannot be modified by users
    """
    settings = get_settings()

    # Self-hosted mode: all themes can be modified
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True

    # Not authenticated in SaaS mode
    if not user:
        return False

    # Built-in themes cannot be modified in SaaS mode
    if theme.get("is_builtin"):
        return False

    # User owns the theme
    return theme.get("owner_id") == user.user_id
