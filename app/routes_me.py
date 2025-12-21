"""User-specific API routes for SaaS mode.

These endpoints are under /api/me/* and require authentication.
"""

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header

from .auth import RequiredUser, OptionalUser, can_access_screen, can_modify_screen
from .config import get_settings, AppMode, PLAN_LIMITS
from .database import (
    create_screen, get_screen_by_id, get_all_screens, get_screens_count,
    delete_screen, get_all_themes, get_themes_count
)
from .db import get_database
from .models import ScreenResponse

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("/screens")
async def list_my_screens(
    user: RequiredUser,
    page: int = 1,
    per_page: int = 20
):
    """List screens owned by the current user or their organization.

    In SaaS mode, returns only screens the user has access to.
    In self-hosted mode, returns all screens (no ownership filtering).
    """
    settings = get_settings()
    offset = (page - 1) * per_page

    if settings.APP_MODE == AppMode.SAAS:
        # Filter by ownership
        screens = await get_all_screens(
            limit=per_page,
            offset=offset,
            owner_id=user.user_id,
            org_id=user.org_id
        )
        total = await get_screens_count(owner_id=user.user_id, org_id=user.org_id)
    else:
        # Self-hosted: return all
        screens = await get_all_screens(limit=per_page, offset=offset)
        total = await get_screens_count()

    return {
        "screens": screens,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
    }


@router.post("/screens", response_model=ScreenResponse)
async def create_my_screen(user: RequiredUser):
    """Create a new screen owned by the current user.

    In SaaS mode, enforces plan limits and sets ownership.
    In self-hosted mode, creates screen without ownership.
    """
    settings = get_settings()

    # Check plan limits in SaaS mode
    if settings.APP_MODE == AppMode.SAAS:
        db = get_database()
        user_data = await db.get_user(user.user_id)
        plan = user_data.get("plan", "free") if user_data else "free"
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["screens"]

        current_count = await get_screens_count(owner_id=user.user_id)
        if current_count >= limit:
            raise HTTPException(
                status_code=402,
                detail=f"Screen limit reached ({limit}). Upgrade your plan for more screens."
            )

    screen_id = uuid.uuid4().hex[:12]
    api_key = f"sk_{secrets.token_urlsafe(24)}"
    created_at = datetime.now(timezone.utc).isoformat()

    # Set ownership in SaaS mode
    owner_id = user.user_id if settings.APP_MODE == AppMode.SAAS else None
    org_id = user.org_id if settings.APP_MODE == AppMode.SAAS and user.org_id else None

    await create_screen(screen_id, api_key, created_at, owner_id=owner_id, org_id=org_id)

    return ScreenResponse(
        screen_id=screen_id,
        api_key=api_key,
        screen_url=f"/screen/{screen_id}",
        api_url=f"/api/screens/{screen_id}/message"
    )


@router.get("/screens/{screen_id}")
async def get_my_screen(screen_id: str, user: RequiredUser):
    """Get details of a screen owned by the current user."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if not can_access_screen(user, screen):
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "screen_id": screen["id"],
        "api_key": screen["api_key"],
        "name": screen.get("name"),
        "created_at": screen.get("created_at"),
        "last_updated": screen.get("last_updated"),
        "owner_id": screen.get("owner_id"),
        "org_id": screen.get("org_id")
    }


@router.delete("/screens/{screen_id}")
async def delete_my_screen(screen_id: str, user: RequiredUser):
    """Delete a screen owned by the current user."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if not can_modify_screen(user, screen):
        raise HTTPException(status_code=403, detail="Access denied")

    await delete_screen(screen_id)
    return {"success": True, "message": "Screen deleted"}


@router.post("/screens/{screen_id}/transfer")
async def transfer_screen(
    screen_id: str,
    user: RequiredUser,
    to_org: bool = False
):
    """Transfer a screen to/from the user's organization.

    - to_org=True: Transfer personal screen to current org
    - to_org=False: Transfer org screen to personal ownership
    """
    settings = get_settings()
    if settings.APP_MODE != AppMode.SAAS:
        raise HTTPException(status_code=404, detail="Not available in self-hosted mode")

    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # Must be owner or org admin to transfer
    if not can_modify_screen(user, screen):
        raise HTTPException(status_code=403, detail="Access denied")

    db = get_database()

    if to_org:
        # Transfer to org
        if not user.org_id:
            raise HTTPException(status_code=400, detail="You are not in an organization")

        # Update screen ownership
        async with db._get_pool() as pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE screens SET org_id = $1, owner_id = NULL WHERE id = $2",
                    user.org_id, screen_id
                )
    else:
        # Transfer to personal
        async with db._get_pool() as pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE screens SET owner_id = $1, org_id = NULL WHERE id = $2",
                    user.user_id, screen_id
                )

    return {"success": True, "message": f"Screen transferred {'to organization' if to_org else 'to personal'}"}


@router.get("/themes")
async def list_my_themes(
    user: RequiredUser,
    page: int = 1,
    per_page: int = 20
):
    """List themes accessible to the current user.

    Returns built-in themes + user's custom themes.
    """
    settings = get_settings()
    offset = (page - 1) * per_page

    if settings.APP_MODE == AppMode.SAAS:
        themes = await get_all_themes(limit=per_page, offset=offset, owner_id=user.user_id)
        total = await get_themes_count(owner_id=user.user_id)
    else:
        themes = await get_all_themes(limit=per_page, offset=offset)
        total = await get_themes_count()

    return {
        "themes": themes,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
    }


@router.get("/usage")
async def get_my_usage(user: RequiredUser):
    """Get usage statistics and limits for the current user."""
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        return {
            "plan": "unlimited",
            "limits": None,
            "usage": None
        }

    db = get_database()
    user_data = await db.get_user(user.user_id)
    plan = user_data.get("plan", "free") if user_data else "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    # Count usage
    screen_count = await get_screens_count(owner_id=user.user_id)
    theme_count = await get_themes_count(owner_id=user.user_id)
    # Subtract built-in themes from count
    all_themes = await get_all_themes(owner_id=user.user_id)
    custom_theme_count = sum(1 for t in all_themes if not t.get("is_builtin"))

    return {
        "plan": plan,
        "limits": {
            "screens": limits["screens"],
            "themes": limits["themes"],
            "pages_per_screen": limits["pages_per_screen"]
        },
        "usage": {
            "screens": screen_count,
            "themes": custom_theme_count
        }
    }


@router.get("/profile")
async def get_my_profile(user: RequiredUser):
    """Get the current user's profile information."""
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        return {
            "user_id": "self-hosted",
            "email": None,
            "name": "Self-Hosted User",
            "plan": "unlimited",
            "organization": None
        }

    db = get_database()
    user_data = await db.get_user(user.user_id)

    org_data = None
    if user.org_id:
        org_data = await db.get_organization(user.org_id)
        if org_data:
            org_data = {
                "id": org_data["id"],
                "name": org_data["name"],
                "slug": org_data["slug"],
                "role": user.org_role
            }

    return {
        "user_id": user.user_id,
        "email": user.email or (user_data.get("email") if user_data else None),
        "name": user.name or (user_data.get("name") if user_data else None),
        "plan": user_data.get("plan", "free") if user_data else "free",
        "organization": org_data
    }
