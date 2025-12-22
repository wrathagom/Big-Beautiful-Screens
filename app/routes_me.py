"""User-specific API routes for SaaS mode.

These endpoints are under /api/v1/me/* and require authentication.
They provide user account information, not screen operations.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter

from .auth import RequiredUser
from .config import PLAN_LIMITS, AppMode, get_settings
from .database import get_all_themes, get_screens_count, get_themes_count
from .db import get_database

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.get("/themes")
async def list_my_themes(user: RequiredUser, page: int = 1, per_page: int = 20):
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
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1,
    }


@router.get("/usage")
async def get_my_usage(user: RequiredUser):
    """Get usage statistics and limits for the current user.

    Returns:
        plan: Current plan name
        limits: Resource limits for the plan
        usage: Current resource usage
        quota: API quota status (limit, used, remaining, resets_at)
    """
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        return {"plan": "unlimited", "limits": None, "usage": None, "quota": None}

    db = get_database()
    user_data = await db.get_user(user.user_id)
    plan = user_data.get("plan", "free") if user_data else "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    # Count usage
    screen_count = await get_screens_count(owner_id=user.user_id)
    # Subtract built-in themes from count
    all_themes = await get_all_themes(owner_id=user.user_id)
    custom_theme_count = sum(1 for t in all_themes if not t.get("is_builtin"))

    # Get API quota status
    today = datetime.now(UTC).date()
    api_calls_today = await db.get_daily_quota_usage(user.user_id, today)
    daily_limit = limits.get("api_calls_daily", 100)

    # Calculate reset time (midnight UTC)
    tomorrow_midnight = datetime.combine(today + timedelta(days=1), datetime.min.time()).replace(
        tzinfo=UTC
    )
    resets_at = tomorrow_midnight.isoformat()

    quota = {
        "limit": daily_limit,
        "used": api_calls_today,
        "remaining": max(0, daily_limit - api_calls_today) if daily_limit != -1 else -1,
        "resets_at": resets_at,
        "is_unlimited": daily_limit == -1,
    }

    return {
        "plan": plan,
        "limits": {
            "screens": limits["screens"],
            "themes": limits["themes"],
            "pages_per_screen": limits["pages_per_screen"],
            "api_calls_daily": daily_limit,
        },
        "usage": {
            "screens": screen_count,
            "themes": custom_theme_count,
            "api_calls_today": api_calls_today,
        },
        "quota": quota,
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
            "organization": None,
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
                "role": user.org_role,
            }

    return {
        "user_id": user.user_id,
        "email": user.email or (user_data.get("email") if user_data else None),
        "name": user.name or (user_data.get("name") if user_data else None),
        "plan": user_data.get("plan", "free") if user_data else "free",
        "organization": org_data,
    }
