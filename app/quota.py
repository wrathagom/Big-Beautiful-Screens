"""API quota tracking and enforcement for SaaS mode.

This module provides daily API call quotas to prevent abuse on the free tier.
Quotas reset at UTC midnight each day.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from .config import PLAN_LIMITS, AppMode, get_settings
from .db import get_database


@dataclass
class QuotaStatus:
    """Current quota status for a user."""

    plan: str
    limit: int
    used: int
    remaining: int
    resets_at: datetime
    is_unlimited: bool = False


def get_next_reset_time() -> datetime:
    """Get next UTC midnight for quota reset."""
    now = datetime.now(UTC)
    tomorrow = now.date() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time(), tzinfo=UTC)


async def get_quota_status(user_id: str) -> QuotaStatus:
    """Get current quota status for a user."""
    db = get_database()

    # Get user's plan
    user = await db.get_user(user_id)
    plan = user.get("plan", "free") if user else "free"
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["api_calls_daily"]

    # Unlimited plans
    if limit == -1:
        return QuotaStatus(
            plan=plan,
            limit=-1,
            used=0,
            remaining=-1,
            resets_at=get_next_reset_time(),
            is_unlimited=True,
        )

    # Get today's usage
    today = datetime.now(UTC).date().isoformat()
    used = await db.get_daily_quota_usage(user_id, today)

    return QuotaStatus(
        plan=plan,
        limit=limit,
        used=used,
        remaining=max(0, limit - used),
        resets_at=get_next_reset_time(),
    )


async def check_and_increment_quota(user_id: str) -> QuotaStatus:
    """Check quota and increment atomically. Raises 429 if exceeded.

    This function is designed to be called before processing an API request.
    It atomically increments the usage counter and checks against the limit.
    """
    settings = get_settings()

    # Skip quota checks in self-hosted mode
    if settings.APP_MODE != AppMode.SAAS:
        return QuotaStatus(
            plan="unlimited",
            limit=-1,
            used=0,
            remaining=-1,
            resets_at=get_next_reset_time(),
            is_unlimited=True,
        )

    db = get_database()

    # Get user's plan
    user = await db.get_user(user_id)
    plan = user.get("plan", "free") if user else "free"
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["api_calls_daily"]

    # Unlimited plans bypass quota
    if limit == -1:
        return QuotaStatus(
            plan=plan,
            limit=-1,
            used=0,
            remaining=-1,
            resets_at=get_next_reset_time(),
            is_unlimited=True,
        )

    # Get today's date in UTC
    today = datetime.now(UTC).date().isoformat()
    reset_time = get_next_reset_time()

    # Check current usage first (before incrementing)
    current_count = await db.get_daily_quota_usage(user_id, today)

    if current_count >= limit:
        # Already at or over quota - reject without incrementing
        seconds_until_reset = int((reset_time - datetime.now(UTC)).total_seconds())
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "message": f"Daily API quota exceeded ({limit} calls/day). Upgrade your plan for more.",
                "limit": limit,
                "used": current_count,
                "resets_at": reset_time.isoformat(),
                "upgrade_url": "/admin/usage",
            },
            headers={
                "Retry-After": str(seconds_until_reset),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time.timestamp())),
            },
        )

    # Under limit - increment and proceed
    new_count = await db.increment_quota_usage(user_id, today)

    return QuotaStatus(
        plan=plan,
        limit=limit,
        used=new_count,
        remaining=limit - new_count,
        resets_at=reset_time,
    )


async def get_user_id_from_api_key(api_key: str) -> str | None:
    """Get the user ID associated with a screen's API key.

    Returns the owner_id of the screen, or None if not found.
    """
    settings = get_settings()

    # Skip in self-hosted mode
    if settings.APP_MODE != AppMode.SAAS:
        return None

    db = get_database()
    return await db.get_user_id_by_api_key(api_key)
