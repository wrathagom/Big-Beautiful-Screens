"""Screen and Page API endpoints."""

import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ..auth import OptionalUser
from ..config import AppMode, get_settings
from ..connection_manager import manager
from ..database import (
    create_screen,
    delete_page,
    delete_screen,
    get_all_pages,
    get_rotation_settings,
    get_screen_by_id,
    reorder_pages,
    update_page,
    update_rotation_settings,
    update_screen_name,
    upsert_page,
)
from ..models import (
    MessageRequest,
    MessageResponse,
    PageOrderRequest,
    PageRequest,
    PageUpdateRequest,
    ScreenResponse,
    ScreenUpdateRequest,
)
from ..themes import get_theme
from ..utils import normalize_content, resolve_theme_settings

router = APIRouter(tags=["Screens"])

static_path = Path(__file__).parent.parent.parent / "static"


# ============== Screen Endpoints ==============


@router.post("/api/screens", response_model=ScreenResponse)
async def create_new_screen(user: OptionalUser = None):
    """Create a new screen and return its ID and API key.

    In SaaS mode with authentication, sets the current user as owner.
    Otherwise creates an anonymous screen.
    """
    screen_id = uuid.uuid4().hex[:12]
    api_key = f"sk_{secrets.token_urlsafe(24)}"
    created_at = datetime.now(UTC).isoformat()

    # Set ownership if user is authenticated in SaaS mode
    settings = get_settings()
    owner_id = None
    org_id = None
    if settings.APP_MODE == AppMode.SAAS and user:
        owner_id = user.user_id
        org_id = user.org_id

    await create_screen(screen_id, api_key, created_at, owner_id=owner_id, org_id=org_id)

    return ScreenResponse(
        screen_id=screen_id,
        api_key=api_key,
        screen_url=f"/screen/{screen_id}",
        api_url=f"/api/screens/{screen_id}/message",
    )


@router.post("/api/screens/{screen_id}/message", response_model=MessageResponse)
async def send_message(
    screen_id: str, request: MessageRequest, x_api_key: str = Header(alias="X-API-Key")
):
    """Send a message to a screen (updates the 'default' page). Requires API key authentication."""
    # Validate screen exists
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # Validate API key
    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Normalize content to structured format
    normalized_content = normalize_content(request.content)

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
    }

    # Save to pages table as "default" page
    page_data = await upsert_page(screen_id, "default", message_payload)

    # Broadcast page update to all connected viewers
    viewers = await manager.broadcast(screen_id, {"type": "page_update", "page": page_data})

    return MessageResponse(success=True, viewers=viewers)


@router.get("/api/screens/{screen_id}")
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


@router.delete("/api/screens/{screen_id}")
async def delete_screen_endpoint(screen_id: str):
    """Delete a screen and its messages."""
    deleted = await delete_screen(screen_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Screen not found")
    return {"success": True, "message": "Screen deleted"}


@router.post("/api/screens/{screen_id}/reload")
async def reload_screen(screen_id: str):
    """Send reload command to all viewers of a screen."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    viewers = await manager.broadcast(screen_id, {"type": "reload"})
    return {"success": True, "viewers_reloaded": viewers}


@router.post("/api/screens/{screen_id}/debug")
async def toggle_debug(screen_id: str, enabled: bool = True):
    """Toggle debug mode on all viewers of a screen."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    viewers = await manager.broadcast(screen_id, {"type": "debug", "enabled": enabled})
    return {"success": True, "debug_enabled": enabled, "viewers": viewers}


@router.patch("/api/screens/{screen_id}")
async def update_screen(
    screen_id: str,
    request: ScreenUpdateRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Update a screen's properties via JSON body.

    API key is required for rotation/display settings, optional for name-only updates.
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

    # Require API key for rotation/display setting changes (including theme)
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
    )
    if has_display_settings and (not x_api_key or screen["api_key"] != x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

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


# ============== Page Endpoints ==============


@router.get("/api/screens/{screen_id}/pages", tags=["Pages"])
async def list_pages(screen_id: str):
    """List all pages for a screen with rotation settings."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    pages = await get_all_pages(screen_id)
    rotation = await get_rotation_settings(screen_id)
    resolved_rotation = await resolve_theme_settings(rotation)

    return {"pages": pages, "rotation": resolved_rotation}


@router.post("/api/screens/{screen_id}/pages/{page_name}", tags=["Pages"])
async def create_or_update_page(
    screen_id: str, page_name: str, request: PageRequest, x_api_key: str = Header(alias="X-API-Key")
):
    """Create or update a specific page. Requires API key authentication."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Normalize content
    normalized_content = normalize_content(request.content)

    message_payload = {
        "content": normalized_content,
        "background_color": request.background_color,
        "panel_color": request.panel_color,
        "font_family": request.font_family,
        "font_color": request.font_color,
        "gap": request.gap,
        "border_radius": request.border_radius,
        "panel_shadow": request.panel_shadow,
    }

    # Convert expires_at to ISO string if provided
    expires_at_str = request.expires_at.isoformat() if request.expires_at else None

    page_data = await upsert_page(
        screen_id, page_name, message_payload, duration=request.duration, expires_at=expires_at_str
    )

    # Broadcast page update
    viewers = await manager.broadcast(screen_id, {"type": "page_update", "page": page_data})

    return {"success": True, "page": page_data, "viewers": viewers}


@router.patch("/api/screens/{screen_id}/pages/{page_name}", tags=["Pages"])
async def patch_page(
    screen_id: str,
    page_name: str,
    request: PageUpdateRequest,
    x_api_key: str = Header(alias="X-API-Key"),
):
    """Partially update a page. Only provided fields are updated. Requires API key."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen["api_key"] != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Normalize content if provided
    normalized_content = None
    if request.content is not None:
        normalized_content = normalize_content(request.content)

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
    )

    if not page_data:
        raise HTTPException(status_code=404, detail="Page not found")

    # Broadcast page update
    viewers = await manager.broadcast(screen_id, {"type": "page_update", "page": page_data})

    return {"success": True, "page": page_data, "viewers": viewers}


@router.delete("/api/screens/{screen_id}/pages/{page_name}", tags=["Pages"])
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


@router.put("/api/screens/{screen_id}/pages/order", tags=["Pages"])
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
