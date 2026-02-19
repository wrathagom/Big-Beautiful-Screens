"""Account API Key management endpoints.

These endpoints allow users to create, list, and delete account-level API keys
for MCP integration and programmatic access to account-level operations.
"""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import RequiredUser
from ..config import AppMode, get_settings
from ..db import get_database
from ..security import make_api_key_preview

router = APIRouter(prefix="/api/v1/account/keys", tags=["Account Keys"])


class AccountKeyCreate(BaseModel):
    """Request body for creating an account API key."""

    name: str = Field(..., min_length=1, max_length=100, description="Name for the API key")
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Number of days until the key expires (1-365). Leave empty for no expiration.",
    )


class AccountKeyResponse(BaseModel):
    """Response for a newly created account API key."""

    id: str
    key: str = Field(..., description="The API key value. Only shown once at creation time.")
    name: str
    scopes: list[str]
    expires_at: str | None
    created_at: str


class AccountKeyListItem(BaseModel):
    """Account API key info for listing (without the key value)."""

    id: str
    name: str
    key_preview: str = Field(..., description="First and last 4 characters of the key")
    scopes: list[str]
    expires_at: str | None
    created_at: str
    last_used_at: str | None


def generate_account_key_id() -> str:
    """Generate a unique account key ID."""
    return f"akid_{secrets.token_hex(8)}"


def generate_account_api_key() -> str:
    """Generate a new account API key with ak_ prefix."""
    return f"ak_{secrets.token_urlsafe(32)}"


@router.post("", response_model=AccountKeyResponse)
async def create_account_key(request: AccountKeyCreate, user: RequiredUser):
    """Create a new account-level API key.

    Account keys can be used to authenticate account-level operations like:
    - Listing screens
    - Creating screens
    - Managing templates
    - Managing themes
    - Managing media

    The key value is only shown once at creation time. Store it securely.

    **SaaS mode only** - This endpoint is not available in self-hosted mode.
    """
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        raise HTTPException(
            status_code=403,
            detail="Account API keys are only available in SaaS mode",
        )

    db = get_database()

    # Calculate expiration if specified
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=request.expires_in_days)

    # Generate key ID and value
    key_id = generate_account_key_id()
    key_value = generate_account_api_key()

    # Create the key in the database
    key_data = await db.create_account_api_key(
        key_id=key_id,
        key=key_value,
        user_id=user.user_id,
        name=request.name,
        scopes=["*"],  # Default to superuser scope
        expires_at=expires_at,
    )

    return AccountKeyResponse(
        id=key_data["id"],
        key=key_data["key"],
        name=key_data["name"],
        scopes=key_data["scopes"],
        expires_at=key_data["expires_at"],
        created_at=key_data["created_at"],
    )


@router.get("")
async def list_account_keys(
    user: RequiredUser,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List all account API keys for the current user.

    The key values are not included in the response for security.

    **SaaS mode only** - This endpoint is not available in self-hosted mode.
    """
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        raise HTTPException(
            status_code=403,
            detail="Account API keys are only available in SaaS mode",
        )

    db = get_database()

    # Get pagination values
    offset = (page - 1) * per_page

    # Get total count
    total_count = await db.get_account_api_keys_count(user.user_id)
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    page = max(1, min(page, total_pages))

    # Get keys
    keys = await db.get_account_api_keys_by_user(
        user_id=user.user_id,
        limit=per_page,
        offset=offset,
    )

    return {
        "keys": [
            AccountKeyListItem(
                id=k["id"],
                name=k["name"],
                key_preview=k.get("key_preview") or make_api_key_preview(k.get("key", "")),
                scopes=k["scopes"],
                expires_at=k["expires_at"],
                created_at=k["created_at"],
                last_used_at=k["last_used_at"],
            )
            for k in keys
        ],
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
    }


@router.delete("/{key_id}")
async def delete_account_key(key_id: str, user: RequiredUser):
    """Delete an account API key.

    The key will immediately stop working for authentication.

    **SaaS mode only** - This endpoint is not available in self-hosted mode.
    """
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        raise HTTPException(
            status_code=403,
            detail="Account API keys are only available in SaaS mode",
        )

    db = get_database()

    # Get all keys for the user to verify ownership
    keys = await db.get_account_api_keys_by_user(user.user_id)
    key_ids = [k["id"] for k in keys]

    if key_id not in key_ids:
        raise HTTPException(status_code=404, detail="API key not found")

    # Delete the key
    success = await db.delete_account_api_key(key_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete API key")

    return {"success": True, "message": "API key deleted"}
