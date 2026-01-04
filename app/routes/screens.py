"""Screen and Page API endpoints."""

import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ..auth import OptionalUser, RequiredUser, can_modify_screen
from ..config import AppMode, get_settings
from ..connection_manager import manager
from ..database import (
    create_screen,
    delete_page,
    delete_screen,
    get_all_pages,
    get_all_screens,
    get_rotation_settings,
    get_screen_by_id,
    get_screens_count,
    reorder_pages,
    update_page,
    update_rotation_settings,
    update_screen_name,
    upsert_page,
)
from ..db import get_database
from ..layouts import list_layout_presets
from ..models import (
    MessageRequest,
    MessageResponse,
    PageOrderRequest,
    PageRequest,
    PageUpdateRequest,
    ScreenResponse,
    ScreenUpdateRequest,
)
from ..quota import check_and_increment_quota, get_user_id_from_api_key
from ..rate_limit import RATE_LIMIT_CREATE, RATE_LIMIT_MUTATE, limiter
from ..themes import get_theme
from ..utils import normalize_content, resolve_theme_settings

router = APIRouter(tags=["Screens"])

static_path = Path(__file__).parent.parent.parent / "static"


# ============== Screen Endpoints ==============


@router.post("/api/v1/screens", response_model=ScreenResponse)
@limiter.limit(RATE_LIMIT_CREATE)
async def create_new_screen(request: Request, user: OptionalUser = None):
    """Create a new screen and return its ID and API key.

    In SaaS mode, requires authentication and sets the current user as owner.
    Screen creation is limited based on the user's plan.
    In self-hosted mode, creates anonymous screens with no limits.
    """
    settings = get_settings()

    # In SaaS mode, require authentication to prevent orphan screens
    if settings.APP_MODE == AppMode.SAAS and not user:
        raise HTTPException(status_code=401, detail="Authentication required to create screens")

    # Set ownership if user is authenticated in SaaS mode
    owner_id = None
    org_id = None
    if settings.APP_MODE == AppMode.SAAS and user:
        owner_id = user.user_id
        org_id = user.org_id

        # Ensure user exists in database (handles case where webhook didn't fire)
        db = get_database()
        user_data = await db.get_user(user.user_id)

        # Only create user if they don't exist AND we have a valid email
        if not user_data and user.email:
            await db.create_or_update_user(
                user_id=user.user_id,
                email=user.email,
                name=user.name,
                plan="free",
            )
            user_data = await db.get_user(user.user_id)

        # Check plan limits (free=3, pro=25, team=100 screens)
        from ..config import PLAN_LIMITS

        plan = user_data.get("plan", "free") if user_data else "free"
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
        screen_limit = limits.get("screens", 3)

        current_count = await get_screens_count(owner_id=user.user_id)
        if current_count >= screen_limit:
            raise HTTPException(
                status_code=403,
                detail=f"Screen limit reached ({screen_limit} screens on {plan} plan). Upgrade to create more.",
            )

    screen_id = uuid.uuid4().hex[:12]
    api_key = f"sk_{secrets.token_urlsafe(24)}"
    created_at = datetime.now(UTC).isoformat()

    await create_screen(screen_id, api_key, created_at, owner_id=owner_id, org_id=org_id)

    return ScreenResponse(
        screen_id=screen_id,
        api_key=api_key,
        screen_url=f"/screen/{screen_id}",
        api_url=f"/api/v1/screens/{screen_id}/message",
    )


@router.get("/api/v1/screens")
async def list_screens(user: OptionalUser, page: int = 1, per_page: int = 20):
    """List screens with pagination.

    In SaaS mode, requires authentication and returns only user's screens.
    In self-hosted mode, returns all screens.
    """
    settings = get_settings()

    # In SaaS mode, require authentication
    if settings.APP_MODE == AppMode.SAAS:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        owner_id = user.user_id
        org_id = user.org_id
    else:
        owner_id = None
        org_id = None

    per_page = min(per_page, 100)  # Cap at 100
    offset = (page - 1) * per_page

    total_count = await get_screens_count(owner_id=owner_id, org_id=org_id)
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    page = max(1, min(page, total_pages))

    screens = await get_all_screens(limit=per_page, offset=offset, owner_id=owner_id, org_id=org_id)

    # Return screen info without exposing API keys
    return {
        "screens": [
            {
                "screen_id": s["id"],
                "name": s.get("name"),
                "created_at": s.get("created_at"),
                "last_updated": s.get("last_updated"),
                "screen_url": f"/screen/{s['id']}",
                "viewer_count": manager.get_viewer_count(s["id"]),
            }
            for s in screens
        ],
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
    }


@router.post("/api/v1/screens/{screen_id}/message", response_model=MessageResponse)
async def send_message(
    screen_id: str, request: MessageRequest, x_api_key: str = Header(alias="X-API-Key")
):
    """Send a message to a screen (updates the 'default' page). Requires API key authentication.

    Rate-limited in SaaS mode (daily quota based on plan).
    """
    # Validate screen exists
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # Validate API key
    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check and increment quota in SaaS mode
    user_id = await get_user_id_from_api_key(x_api_key)
    if user_id:
        await check_and_increment_quota(user_id)

    # Normalize content to structured format
    normalized_content = normalize_content(request.content)

    # Serialize layout if it's a LayoutConfig object
    layout_value = request.layout
    if layout_value is not None and hasattr(layout_value, "model_dump"):
        layout_value = layout_value.model_dump(exclude_none=True)

    # Build full message payload with styling
    message_payload = {
        "content": normalized_content,
        "background_color": request.background_color,
        "panel_color": request.panel_color,
        "font_family": request.font_family,
        "font_color": request.font_color,
        "gap": request.gap,
        "border_radius": request.border_radius,
        "panel_shadow": request.panel_shadow,
        "layout": layout_value,
    }

    # Save to pages table as "default" page
    page_data = await upsert_page(screen_id, "default", message_payload)

    # Broadcast page update to all connected viewers
    viewers = await manager.broadcast(screen_id, {"type": "page_update", "page": page_data})

    return MessageResponse(success=True, viewers=viewers)


@router.get("/api/v1/screens/{screen_id}")
async def get_screen(screen_id: str):
    """Get screen details including display settings."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    settings = await get_rotation_settings(screen_id)

    return {
        "screen_id": screen["id"],
        "name": screen.get("name"),
        "created_at": screen.get("created_at"),
        "last_updated": screen.get("last_updated"),
        "settings": settings,
    }


@router.delete("/api/v1/screens/{screen_id}")
@limiter.limit(RATE_LIMIT_MUTATE)
async def delete_screen_endpoint(
    request: Request, screen_id: str, x_api_key: str = Header(alias="X-API-Key")
):
    """Delete a screen and its messages. Requires API key authentication."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    await delete_screen(screen_id)
    return {"success": True, "message": "Screen deleted"}


@router.post("/api/v1/screens/{screen_id}/reload")
async def reload_screen(screen_id: str, x_api_key: str = Header(alias="X-API-Key")):
    """Send reload command to all viewers of a screen. Requires API key authentication."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    viewers = await manager.broadcast(screen_id, {"type": "reload"})
    return {"success": True, "viewers_reloaded": viewers}


@router.post("/api/v1/screens/{screen_id}/debug")
async def toggle_debug(
    screen_id: str, enabled: bool = True, x_api_key: str = Header(alias="X-API-Key")
):
    """Toggle debug mode on all viewers of a screen. Requires API key authentication."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    viewers = await manager.broadcast(screen_id, {"type": "debug", "enabled": enabled})
    return {"success": True, "debug_enabled": enabled, "viewers": viewers}


@router.patch("/api/v1/screens/{screen_id}")
async def update_screen(
    screen_id: str,
    request: ScreenUpdateRequest,
    x_api_key: str = Header(alias="X-API-Key"),
):
    """Update a screen's properties via JSON body. Requires API key authentication.

    You can apply a theme and override specific values in the same request.
    """
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # Resolve theme if specified
    theme_values = {}
    theme_name = None
    if request.theme:
        theme_values = get_theme(request.theme)
        if not theme_values:
            raise HTTPException(status_code=400, detail=f"Unknown theme: {request.theme}")
        theme_name = request.theme

    # Extract values from request, with theme as fallback
    name = request.name
    rotation_enabled = request.rotation_enabled
    rotation_interval = request.rotation_interval
    # For visual settings, use explicit value if provided, else theme value if theme specified
    gap = request.gap if request.gap is not None else theme_values.get("gap")
    border_radius = (
        request.border_radius
        if request.border_radius is not None
        else theme_values.get("border_radius")
    )
    panel_shadow = (
        request.panel_shadow
        if request.panel_shadow is not None
        else theme_values.get("panel_shadow")
    )
    background_color = (
        request.background_color
        if request.background_color is not None
        else theme_values.get("background_color")
    )
    panel_color = (
        request.panel_color if request.panel_color is not None else theme_values.get("panel_color")
    )
    font_family = (
        request.font_family if request.font_family is not None else theme_values.get("font_family")
    )
    font_color = (
        request.font_color if request.font_color is not None else theme_values.get("font_color")
    )
    head_html = request.head_html
    transition = request.transition
    transition_duration = request.transition_duration

    # Serialize default_layout if it's a LayoutConfig object
    default_layout = request.default_layout
    if default_layout is not None and hasattr(default_layout, "model_dump"):
        default_layout = default_layout.model_dump(exclude_none=True)

    # Validate API key
    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    has_display_settings = (
        request.theme is not None
        or rotation_enabled is not None
        or rotation_interval is not None
        or gap is not None
        or border_radius is not None
        or panel_shadow is not None
        or background_color is not None
        or panel_color is not None
        or font_family is not None
        or font_color is not None
        or head_html is not None
        or default_layout is not None
        or transition is not None
        or transition_duration is not None
    )

    # Update name if provided
    if name is not None:
        await update_screen_name(screen_id, name)

    # Update rotation/display settings if any provided
    if has_display_settings:
        await update_rotation_settings(
            screen_id,
            enabled=rotation_enabled,
            interval=rotation_interval,
            gap=gap,
            border_radius=border_radius,
            panel_shadow=panel_shadow,
            background_color=background_color,
            panel_color=panel_color,
            font_family=font_family,
            font_color=font_color,
            theme=theme_name,
            head_html=head_html,
            default_layout=default_layout,
            transition=transition,
            transition_duration=transition_duration,
        )

        # Broadcast settings update to viewers (with theme values resolved)
        rotation = await get_rotation_settings(screen_id)
        resolved_rotation = await resolve_theme_settings(rotation)
        await manager.broadcast(
            screen_id, {"type": "rotation_update", "rotation": resolved_rotation}
        )

    # Build response
    response = {"success": True}
    if name is not None:
        response["name"] = name
    if has_display_settings:
        settings = await get_rotation_settings(screen_id)
        response["settings"] = await resolve_theme_settings(settings)

    return response


@router.post("/api/v1/screens/{screen_id}/transfer")
async def transfer_screen(screen_id: str, user: RequiredUser, to_org: bool = False):
    """Transfer a screen to/from the user's organization. Requires Clerk authentication.

    - to_org=True: Transfer personal screen to current org
    - to_org=False: Transfer org screen to personal ownership

    Only available in SaaS mode.
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
        async with db._get_pool() as pool, pool.acquire() as conn:
            await conn.execute(
                "UPDATE screens SET org_id = $1, owner_id = NULL WHERE id = $2",
                user.org_id,
                screen_id,
            )
    else:
        # Transfer to personal
        async with db._get_pool() as pool, pool.acquire() as conn:
            await conn.execute(
                "UPDATE screens SET owner_id = $1, org_id = NULL WHERE id = $2",
                user.user_id,
                screen_id,
            )

    return {
        "success": True,
        "message": f"Screen transferred {'to organization' if to_org else 'to personal'}",
    }


# ============== Layout Endpoints ==============


@router.get("/api/v1/layouts", tags=["Layouts"])
async def get_layouts():
    """List all available layout presets.

    Returns preset names, descriptions, and configuration details.
    """
    return {"layouts": list_layout_presets()}


# ============== Page Endpoints ==============


@router.get("/api/v1/screens/{screen_id}/pages", tags=["Pages"])
async def list_pages(screen_id: str):
    """List all pages for a screen with rotation settings."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    pages = await get_all_pages(screen_id)
    rotation = await get_rotation_settings(screen_id)
    resolved_rotation = await resolve_theme_settings(rotation)

    return {"pages": pages, "rotation": resolved_rotation}


@router.post("/api/v1/screens/{screen_id}/pages/{page_name}", tags=["Pages"])
async def create_or_update_page(
    screen_id: str, page_name: str, request: PageRequest, x_api_key: str = Header(alias="X-API-Key")
):
    """Create or update a specific page. Requires API key authentication.

    Rate-limited in SaaS mode (daily quota based on plan).
    """
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check and increment quota in SaaS mode
    user_id = await get_user_id_from_api_key(x_api_key)
    if user_id:
        await check_and_increment_quota(user_id)

    # Normalize content
    normalized_content = normalize_content(request.content)

    # Serialize layout if it's a LayoutConfig object
    layout_value = request.layout
    if layout_value is not None and hasattr(layout_value, "model_dump"):
        layout_value = layout_value.model_dump(exclude_none=True)

    message_payload = {
        "content": normalized_content,
        "background_color": request.background_color,
        "panel_color": request.panel_color,
        "font_family": request.font_family,
        "font_color": request.font_color,
        "gap": request.gap,
        "border_radius": request.border_radius,
        "panel_shadow": request.panel_shadow,
        "layout": layout_value,
        "transition": request.transition,
        "transition_duration": request.transition_duration,
    }

    # Convert expires_at to ISO string if provided
    expires_at_str = request.expires_at.isoformat() if request.expires_at else None

    page_data = await upsert_page(
        screen_id, page_name, message_payload, duration=request.duration, expires_at=expires_at_str
    )

    # Broadcast page update
    viewers = await manager.broadcast(screen_id, {"type": "page_update", "page": page_data})

    return {"success": True, "page": page_data, "viewers": viewers}


@router.patch("/api/v1/screens/{screen_id}/pages/{page_name}", tags=["Pages"])
async def patch_page(
    screen_id: str,
    page_name: str,
    request: PageUpdateRequest,
    x_api_key: str = Header(alias="X-API-Key"),
):
    """Partially update a page. Only provided fields are updated. Requires API key.

    Rate-limited in SaaS mode (daily quota based on plan).
    """
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check and increment quota in SaaS mode
    user_id = await get_user_id_from_api_key(x_api_key)
    if user_id:
        await check_and_increment_quota(user_id)

    # Normalize content if provided
    normalized_content = None
    if request.content is not None:
        normalized_content = normalize_content(request.content)

    # Serialize layout if it's a LayoutConfig object
    layout_value = request.layout
    if layout_value is not None and hasattr(layout_value, "model_dump"):
        layout_value = layout_value.model_dump(exclude_none=True)

    # Convert expires_at to ISO string if provided
    expires_at_str = request.expires_at.isoformat() if request.expires_at else None

    page_data = await update_page(
        screen_id,
        page_name,
        content=normalized_content,
        background_color=request.background_color,
        panel_color=request.panel_color,
        font_family=request.font_family,
        font_color=request.font_color,
        gap=request.gap,
        border_radius=request.border_radius,
        panel_shadow=request.panel_shadow,
        duration=request.duration,
        expires_at=expires_at_str,
        layout=layout_value,
        transition=request.transition,
        transition_duration=request.transition_duration,
    )

    if not page_data:
        raise HTTPException(status_code=404, detail="Page not found")

    # Broadcast page update
    viewers = await manager.broadcast(screen_id, {"type": "page_update", "page": page_data})

    return {"success": True, "page": page_data, "viewers": viewers}


@router.delete("/api/v1/screens/{screen_id}/pages/{page_name}", tags=["Pages"])
async def delete_page_endpoint(
    screen_id: str, page_name: str, x_api_key: str = Header(alias="X-API-Key")
):
    """Delete a page. Cannot delete the 'default' page. Requires API key authentication."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if page_name == "default":
        raise HTTPException(status_code=400, detail="Cannot delete the default page")

    deleted = await delete_page(screen_id, page_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Page not found")

    # Broadcast page deletion
    viewers = await manager.broadcast(screen_id, {"type": "page_delete", "page_name": page_name})

    return {"success": True, "viewers": viewers}


@router.put("/api/v1/screens/{screen_id}/pages/order", tags=["Pages"])
async def reorder_pages_endpoint(
    screen_id: str, request: PageOrderRequest, x_api_key: str = Header(alias="X-API-Key")
):
    """Reorder pages by providing an ordered list of page names. Requires API key authentication."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    await reorder_pages(screen_id, request.page_names)

    # Get updated pages and broadcast (with theme values resolved)
    pages = await get_all_pages(screen_id)
    rotation = await get_rotation_settings(screen_id)
    resolved_rotation = await resolve_theme_settings(rotation)

    await manager.broadcast(
        screen_id, {"type": "pages_sync", "pages": pages, "rotation": resolved_rotation}
    )

    return {"success": True}


# ============== Screen Viewer ==============


@router.get("/screen/{screen_id}", response_class=HTMLResponse, include_in_schema=False)
async def view_screen(screen_id: str):
    """Serve the screen viewer page."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    html_path = static_path / "screen.html"
    return HTMLResponse(content=html_path.read_text())


# ============== WebSocket ==============


@router.websocket("/ws/{screen_id}")
async def websocket_endpoint(websocket: WebSocket, screen_id: str):
    """WebSocket endpoint for real-time screen updates."""
    # Validate screen exists
    screen = await get_screen_by_id(screen_id)
    if not screen:
        await websocket.close(code=4004, reason="Screen not found")
        return

    await manager.connect(screen_id, websocket)

    try:
        # Send full pages sync on connect (with theme values resolved)
        pages = await get_all_pages(screen_id)
        rotation = await get_rotation_settings(screen_id)
        resolved_rotation = await resolve_theme_settings(rotation)

        await websocket.send_json(
            {"type": "pages_sync", "pages": pages, "rotation": resolved_rotation}
        )

        # Keep connection alive and handle incoming messages
        while True:
            # We don't expect messages from viewers, but need to keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(screen_id, websocket)
