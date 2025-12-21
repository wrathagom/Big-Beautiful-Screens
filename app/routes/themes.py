"""Theme API endpoints."""

from fastapi import APIRouter, HTTPException

from ..auth import OptionalUser
from ..config import PLAN_LIMITS, AppMode, get_settings
from ..database import (
    create_theme_in_db,
    delete_theme_from_db,
    get_all_themes,
    get_theme_from_db,
    get_theme_usage_counts,
    update_theme_in_db,
)
from ..db import get_database
from ..models import ThemeCreate, ThemeUpdate

router = APIRouter(prefix="/api/themes", tags=["Themes"])


@router.get("")
async def get_available_themes():
    """List all available themes with their properties."""
    themes = await get_all_themes()
    usage_counts = await get_theme_usage_counts()
    # Add usage count to each theme
    for theme in themes:
        theme["usage_count"] = usage_counts.get(theme["name"], 0)
    return {"themes": themes}


@router.get("/{theme_name}")
async def get_theme_by_name(theme_name: str):
    """Get a specific theme by name."""
    theme = await get_theme_from_db(theme_name)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme


@router.post("")
async def create_theme(request: ThemeCreate, user: OptionalUser = None):
    """Create a new custom theme.

    In SaaS mode with authentication, enforces plan limits and sets ownership.
    """
    settings = get_settings()

    # Check plan limits in SaaS mode
    if settings.APP_MODE == AppMode.SAAS and user:
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
async def update_theme(theme_name: str, request: ThemeUpdate):
    """Update a theme. All fields are optional for partial updates."""
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
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    return {"success": True, "theme": theme}


@router.delete("/{theme_name}")
async def delete_theme(theme_name: str):
    """Delete a theme. Will fail if the theme is in use by any screens."""
    success, error = await delete_theme_from_db(theme_name)
    if not success:
        raise HTTPException(status_code=400, detail=error)
    return {"success": True}
