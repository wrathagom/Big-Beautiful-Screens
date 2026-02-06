"""Theme API endpoints."""

from fastapi import APIRouter, HTTPException

from ..auth import AuthOrAccountKey
from ..config import PLAN_LIMITS, AppMode, get_settings
from ..database import (
    create_theme_in_db,
    delete_theme_from_db,
    get_all_themes,
    get_theme_from_db,
    get_theme_usage_counts,
    get_themes_count,
    update_theme_in_db,
)
from ..db import get_database
from ..models import ThemeCreate, ThemeUpdate

router = APIRouter(prefix="/api/v1/themes", tags=["Themes"])


@router.get("")
async def get_available_themes(page: int = 1, per_page: int = 20):
    """List all available themes with their properties and pagination."""
    per_page = min(per_page, 100)  # Cap at 100
    offset = (page - 1) * per_page

    total_count = await get_themes_count()
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    page = max(1, min(page, total_pages))

    themes = await get_all_themes(limit=per_page, offset=offset)
    usage_counts = await get_theme_usage_counts()

    # Add usage count to each theme
    for theme in themes:
        theme["usage_count"] = usage_counts.get(theme["name"], 0)

    return {
        "themes": themes,
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
    }


@router.get("/{theme_name}")
async def get_theme_by_name(theme_name: str):
    """Get a specific theme by name."""
    theme = await get_theme_from_db(theme_name)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme


@router.post("")
async def create_theme(request: ThemeCreate, user: AuthOrAccountKey):
    """Create a new custom theme.

    In SaaS mode, requires authentication (Clerk session or account API key with ak_ prefix),
    enforces plan limits, and sets ownership.
    """
    settings = get_settings()

    # Check plan limits in SaaS mode
    if settings.APP_MODE == AppMode.SAAS:
        db = get_database()
        user_data = await db.get_user(user.user_id)
        plan = user_data.get("plan", "free") if user_data else "free"
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["themes"]

        # Count user's custom themes (excluding built-in)
        all_themes = await get_all_themes(owner_id=user.user_id)
        custom_count = sum(1 for t in all_themes if not t.get("is_builtin"))
        if custom_count >= limit:
            raise HTTPException(
                status_code=402,
                detail=f"Theme limit reached ({limit}). Upgrade your plan for more themes.",
            )

    # Check if theme name already exists
    existing = await get_theme_from_db(request.name)
    if existing:
        raise HTTPException(status_code=400, detail="Theme with this name already exists")

    # Validate theme name (URL-safe)
    if not request.name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(
            status_code=400, detail="Theme name must be alphanumeric with hyphens/underscores only"
        )

    # Set owner in SaaS mode
    owner_id = user.user_id if settings.APP_MODE == AppMode.SAAS and user else None

    theme = await create_theme_in_db(
        name=request.name,
        display_name=request.display_name,
        background_color=request.background_color,
        panel_color=request.panel_color,
        font_family=request.font_family,
        font_color=request.font_color,
        gap=request.gap,
        border_radius=request.border_radius,
        panel_shadow=request.panel_shadow,
        owner_id=owner_id,
    )
    return {"success": True, "theme": theme}


@router.patch("/{theme_name}")
async def update_theme(theme_name: str, request: ThemeUpdate, user: AuthOrAccountKey):
    """Update a theme. All fields are optional for partial updates.

    In SaaS mode, only the theme owner can modify custom themes.
    Built-in themes cannot be modified.

    Requires authentication (Clerk session or account API key with ak_ prefix) in SaaS mode.
    """
    # Check if theme exists
    existing = await get_theme_from_db(theme_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Theme not found")

    # Cannot modify built-in themes
    if existing.get("is_builtin"):
        raise HTTPException(status_code=403, detail="Cannot modify built-in themes")

    # In SaaS mode, verify ownership
    settings = get_settings()
    if (
        settings.APP_MODE == AppMode.SAAS
        and existing.get("owner_id")
        and existing["owner_id"] != user.user_id
    ):
        raise HTTPException(status_code=403, detail="Not authorized to modify this theme")

    theme = await update_theme_in_db(
        name=theme_name,
        display_name=request.display_name,
        background_color=request.background_color,
        panel_color=request.panel_color,
        font_family=request.font_family,
        font_color=request.font_color,
        gap=request.gap,
        border_radius=request.border_radius,
        panel_shadow=request.panel_shadow,
    )

    return {"success": True, "theme": theme}


@router.delete("/{theme_name}")
async def delete_theme(theme_name: str, user: AuthOrAccountKey):
    """Delete a theme. Will fail if the theme is in use by any screens.

    In SaaS mode, only the theme owner can delete custom themes.
    Built-in themes cannot be deleted.

    Requires authentication (Clerk session or account API key with ak_ prefix) in SaaS mode.
    """
    # Check if theme exists
    existing = await get_theme_from_db(theme_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Theme not found")

    # Cannot delete built-in themes
    if existing.get("is_builtin"):
        raise HTTPException(status_code=403, detail="Cannot delete built-in themes")

    # In SaaS mode, verify ownership
    settings = get_settings()
    if (
        settings.APP_MODE == AppMode.SAAS
        and existing.get("owner_id")
        and existing["owner_id"] != user.user_id
    ):
        raise HTTPException(status_code=403, detail="Not authorized to delete this theme")

    success, error = await delete_theme_from_db(theme_name)
    if not success:
        raise HTTPException(status_code=400, detail=error)
    return {"success": True}
