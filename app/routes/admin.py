"""Admin dashboard routes with Jinja2 template rendering."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_clerk_sign_in_url, get_current_user
from ..config import PLAN_LIMITS, AppMode, get_settings
from ..connection_manager import manager
from ..database import (
    get_all_screens,
    get_all_themes,
    get_screens_count,
    get_theme_usage_counts,
    get_themes_count,
)
from ..db import get_database

router = APIRouter(include_in_schema=False)

# Set up Jinja2 templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=templates_path)


@router.get("/admin/screens", response_class=HTMLResponse)
async def admin_screens(request: Request, page: int = 1):
    """Admin page listing all screens with pagination.

    In SaaS mode, requires authentication and shows only user's screens.
    In self-hosted mode, shows all screens without authentication.
    """
    settings = get_settings()
    user = None

    # In SaaS mode, require authentication
    if settings.APP_MODE == AppMode.SAAS:
        user = await get_current_user(request)
        if not user:
            return RedirectResponse(url=get_clerk_sign_in_url("/admin/screens"), status_code=302)

    per_page = 10
    offset = (page - 1) * per_page

    # Filter by ownership in SaaS mode
    if settings.APP_MODE == AppMode.SAAS and user:
        total_count = await get_screens_count(owner_id=user.user_id, org_id=user.org_id)
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        page = max(1, min(page, total_pages))
        screens = await get_all_screens(
            limit=per_page, offset=offset, owner_id=user.user_id, org_id=user.org_id
        )
    else:
        total_count = await get_screens_count()
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        page = max(1, min(page, total_pages))
        screens = await get_all_screens(limit=per_page, offset=offset)

    # Enrich screen data for template
    enriched_screens = []
    for screen in screens:
        enriched_screens.append(
            {
                **screen,
                "screen_url": f"/screen/{screen['id']}",
                "api_url": f"/api/screens/{screen['id']}/message",
                "viewer_count": manager.get_viewer_count(screen["id"]),
                "created_display": screen["created_at"][:19].replace("T", " "),
                "last_updated_display": (
                    screen["last_updated"][:19].replace("T", " ")
                    if screen.get("last_updated")
                    else "Never"
                ),
                "name_display": screen.get("name") or "Unnamed Screen",
                "is_unnamed": not screen.get("name"),
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_screens.html",
        context={
            "screens": enriched_screens,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
        },
    )


@router.get("/admin/themes", response_class=HTMLResponse)
async def admin_themes(request: Request, page: int = 1):
    """Admin page for managing themes with pagination.

    In SaaS mode, requires authentication and shows only accessible themes.
    In self-hosted mode, shows all themes without authentication.
    """
    settings = get_settings()
    user = None

    # In SaaS mode, require authentication
    if settings.APP_MODE == AppMode.SAAS:
        user = await get_current_user(request)
        if not user:
            return RedirectResponse(url=get_clerk_sign_in_url("/admin/themes"), status_code=302)

    per_page = 10
    offset = (page - 1) * per_page

    # Get themes
    if settings.APP_MODE == AppMode.SAAS and user:
        total_count = await get_themes_count(owner_id=user.user_id)
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        page = max(1, min(page, total_pages))
        themes = await get_all_themes(limit=per_page, offset=offset, owner_id=user.user_id)
    else:
        total_count = await get_themes_count()
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        page = max(1, min(page, total_pages))
        themes = await get_all_themes(limit=per_page, offset=offset)

    usage_counts = await get_theme_usage_counts()

    # Enrich theme data for template
    enriched_themes = []
    for theme in themes:
        enriched_themes.append(
            {
                **theme,
                "usage_count": usage_counts.get(theme["name"], 0),
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_themes.html",
        context={
            "themes": enriched_themes,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
        },
    )


@router.get("/admin/usage", response_class=HTMLResponse)
async def admin_usage(request: Request, checkout: str | None = None):
    """Admin page showing usage statistics and billing information.

    Only available in SaaS mode. Requires authentication.
    """
    settings = get_settings()

    # Only available in SaaS mode
    if settings.APP_MODE != AppMode.SAAS:
        return RedirectResponse(url="/admin/screens", status_code=302)

    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url=get_clerk_sign_in_url("/admin/usage"), status_code=302)

    db = get_database()
    user_data = await db.get_user(user.user_id)
    plan = user_data.get("plan", "free") if user_data else "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    # Count usage
    screen_count = await get_screens_count(owner_id=user.user_id)
    all_themes = await get_all_themes(owner_id=user.user_id)
    custom_theme_count = sum(1 for t in all_themes if not t.get("is_builtin"))

    # Get API quota usage for today
    from datetime import UTC, datetime

    today = datetime.now(UTC).date()
    api_calls_today = await db.get_daily_quota_usage(user.user_id, today)

    # Subscription info
    subscription_status = user_data.get("subscription_status") if user_data else None
    subscription_id = user_data.get("stripe_subscription_id") if user_data else None
    customer_id = user_data.get("stripe_customer_id") if user_data else None
    has_subscription = bool(customer_id)

    return templates.TemplateResponse(
        request=request,
        name="admin_usage.html",
        context={
            "plan": plan,
            "limits": limits,
            "usage": {
                "screens": screen_count,
                "themes": custom_theme_count,
                "api_calls_today": api_calls_today,
            },
            "subscription_status": subscription_status,
            "subscription_id": subscription_id,
            "customer_id": customer_id,
            "has_subscription": has_subscription,
            "checkout": checkout,
        },
    )
