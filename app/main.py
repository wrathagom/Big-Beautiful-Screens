import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .models import (
    MessageRequest, ScreenResponse, MessageResponse,
    PageRequest, PageUpdateRequest, RotationSettings, PageOrderRequest, PageResponse, PagesListResponse,
    ScreenUpdateRequest, ThemeCreate, ThemeUpdate
)
from .database import (
    init_db, create_screen, get_screen_by_id, get_screen_by_api_key,
    save_message, get_last_message, get_all_screens, delete_screen, update_screen_name,
    upsert_page, get_all_pages, get_page, update_page, delete_page, reorder_pages,
    get_rotation_settings, update_rotation_settings, cleanup_expired_pages,
    get_all_themes, get_theme_from_db, create_theme_in_db, update_theme_in_db,
    delete_theme_from_db, get_theme_usage_counts
)
from .connection_manager import manager
from .themes import get_theme, list_themes, get_theme_async

app = FastAPI(title="Big Beautiful Screens", version="0.1.0")

# Mount static files
static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/api/themes")
async def get_available_themes():
    """List all available themes with their properties."""
    themes = await get_all_themes()
    usage_counts = await get_theme_usage_counts()
    # Add usage count to each theme
    for theme in themes:
        theme["usage_count"] = usage_counts.get(theme["name"], 0)
    return {"themes": themes}


@app.get("/api/themes/{theme_name}")
async def get_theme_by_name(theme_name: str):
    """Get a specific theme by name."""
    theme = await get_theme_from_db(theme_name)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme


@app.post("/api/themes")
async def create_theme(request: ThemeCreate):
    """Create a new custom theme."""
    # Check if theme name already exists
    existing = await get_theme_from_db(request.name)
    if existing:
        raise HTTPException(status_code=400, detail="Theme with this name already exists")

    # Validate theme name (URL-safe)
    if not request.name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Theme name must be alphanumeric with hyphens/underscores only")

    theme = await create_theme_in_db(
        name=request.name,
        display_name=request.display_name,
        background_color=request.background_color,
        panel_color=request.panel_color,
        font_family=request.font_family,
        font_color=request.font_color,
        gap=request.gap,
        border_radius=request.border_radius,
        panel_shadow=request.panel_shadow
    )
    return {"success": True, "theme": theme}


@app.patch("/api/themes/{theme_name}")
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
        panel_shadow=request.panel_shadow
    )
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    return {"success": True, "theme": theme}


@app.delete("/api/themes/{theme_name}")
async def delete_theme(theme_name: str):
    """Delete a theme. Will fail if the theme is in use by any screens."""
    success, error = await delete_theme_from_db(theme_name)
    if not success:
        raise HTTPException(status_code=400, detail=error)
    return {"success": True}


@app.post("/api/screens", response_model=ScreenResponse)
async def create_new_screen():
    """Create a new screen and return its ID and API key."""
    screen_id = uuid.uuid4().hex[:12]
    api_key = f"sk_{secrets.token_urlsafe(24)}"
    created_at = datetime.now(timezone.utc).isoformat()

    await create_screen(screen_id, api_key, created_at)

    return ScreenResponse(
        screen_id=screen_id,
        api_key=api_key,
        screen_url=f"/screen/{screen_id}",
        api_url=f"/api/screens/{screen_id}/message"
    )


@app.post("/api/screens/{screen_id}/message", response_model=MessageResponse)
async def send_message(
    screen_id: str,
    request: MessageRequest,
    x_api_key: str = Header(alias="X-API-Key")
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
        "panel_shadow": request.panel_shadow
    }

    # Save to pages table as "default" page (backward compatible)
    page_data = await upsert_page(screen_id, "default", message_payload)

    # Also save to messages table for legacy compatibility
    created_at = datetime.now(timezone.utc).isoformat()
    await save_message(screen_id, message_payload, created_at)

    # Broadcast page update to all connected viewers
    viewers = await manager.broadcast(screen_id, {
        "type": "page_update",
        "page": page_data
    })

    # Also broadcast legacy message format for backward compatibility
    await manager.broadcast(screen_id, {
        "type": "message",
        **message_payload
    })

    return MessageResponse(success=True, viewers=viewers)


@app.get("/api/screens/{screen_id}")
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
        "settings": settings
    }


@app.delete("/api/screens/{screen_id}")
async def delete_screen_endpoint(screen_id: str):
    """Delete a screen and its messages."""
    deleted = await delete_screen(screen_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Screen not found")
    return {"success": True, "message": "Screen deleted"}


@app.post("/api/screens/{screen_id}/reload")
async def reload_screen(screen_id: str):
    """Send reload command to all viewers of a screen."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    viewers = await manager.broadcast(screen_id, {"type": "reload"})
    return {"success": True, "viewers_reloaded": viewers}


@app.post("/api/screens/{screen_id}/debug")
async def toggle_debug(screen_id: str, enabled: bool = True):
    """Toggle debug mode on all viewers of a screen."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    viewers = await manager.broadcast(screen_id, {"type": "debug", "enabled": enabled})
    return {"success": True, "debug_enabled": enabled, "viewers": viewers}


@app.patch("/api/screens/{screen_id}")
async def update_screen(
    screen_id: str,
    request: ScreenUpdateRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key")
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
    border_radius = request.border_radius if request.border_radius is not None else theme_values.get("border_radius")
    panel_shadow = request.panel_shadow if request.panel_shadow is not None else theme_values.get("panel_shadow")
    background_color = request.background_color if request.background_color is not None else theme_values.get("background_color")
    panel_color = request.panel_color if request.panel_color is not None else theme_values.get("panel_color")
    font_family = request.font_family if request.font_family is not None else theme_values.get("font_family")
    font_color = request.font_color if request.font_color is not None else theme_values.get("font_color")
    head_html = request.head_html

    # Require API key for rotation/display setting changes (including theme)
    has_display_settings = (
        request.theme is not None or
        rotation_enabled is not None or
        rotation_interval is not None or
        gap is not None or
        border_radius is not None or
        panel_shadow is not None or
        background_color is not None or
        panel_color is not None or
        font_family is not None or
        font_color is not None or
        head_html is not None
    )
    if has_display_settings:
        if not x_api_key or screen["api_key"] != x_api_key:
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
            head_html=head_html
        )

        # Broadcast settings update to viewers (with theme values resolved)
        rotation = await get_rotation_settings(screen_id)
        resolved_rotation = await resolve_theme_settings(rotation)
        await manager.broadcast(screen_id, {
            "type": "rotation_update",
            "rotation": resolved_rotation
        })

    # Build response
    response = {"success": True}
    if name is not None:
        response["name"] = name
    if has_display_settings:
        settings = await get_rotation_settings(screen_id)
        response["settings"] = await resolve_theme_settings(settings)

    return response


# ============== Page Endpoints ==============

@app.get("/api/screens/{screen_id}/pages")
async def list_pages(screen_id: str):
    """List all pages for a screen with rotation settings."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    pages = await get_all_pages(screen_id)
    rotation = await get_rotation_settings(screen_id)
    resolved_rotation = await resolve_theme_settings(rotation)

    return {
        "pages": pages,
        "rotation": resolved_rotation
    }


@app.post("/api/screens/{screen_id}/pages/{page_name}")
async def create_or_update_page(
    screen_id: str,
    page_name: str,
    request: PageRequest,
    x_api_key: str = Header(alias="X-API-Key")
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
        "panel_shadow": request.panel_shadow
    }

    # Convert expires_at to ISO string if provided
    expires_at_str = request.expires_at.isoformat() if request.expires_at else None

    page_data = await upsert_page(
        screen_id, page_name, message_payload,
        duration=request.duration,
        expires_at=expires_at_str
    )

    # Broadcast page update
    viewers = await manager.broadcast(screen_id, {
        "type": "page_update",
        "page": page_data
    })

    # If updating default page, also broadcast legacy message
    if page_name == "default":
        await manager.broadcast(screen_id, {
            "type": "message",
            **message_payload
        })

    return {"success": True, "page": page_data, "viewers": viewers}


@app.patch("/api/screens/{screen_id}/pages/{page_name}")
async def patch_page(
    screen_id: str,
    page_name: str,
    request: PageUpdateRequest,
    x_api_key: str = Header(alias="X-API-Key")
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
        screen_id, page_name,
        content=normalized_content,
        background_color=request.background_color,
        panel_color=request.panel_color,
        font_family=request.font_family,
        font_color=request.font_color,
        gap=request.gap,
        border_radius=request.border_radius,
        panel_shadow=request.panel_shadow,
        duration=request.duration,
        expires_at=expires_at_str
    )

    if not page_data:
        raise HTTPException(status_code=404, detail="Page not found")

    # Broadcast page update
    viewers = await manager.broadcast(screen_id, {
        "type": "page_update",
        "page": page_data
    })

    return {"success": True, "page": page_data, "viewers": viewers}


@app.delete("/api/screens/{screen_id}/pages/{page_name}")
async def delete_page_endpoint(
    screen_id: str,
    page_name: str,
    x_api_key: str = Header(alias="X-API-Key")
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
    viewers = await manager.broadcast(screen_id, {
        "type": "page_delete",
        "page_name": page_name
    })

    return {"success": True, "viewers": viewers}


@app.put("/api/screens/{screen_id}/pages/order")
async def reorder_pages_endpoint(
    screen_id: str,
    request: PageOrderRequest,
    x_api_key: str = Header(alias="X-API-Key")
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

    await manager.broadcast(screen_id, {
        "type": "pages_sync",
        "pages": pages,
        "rotation": resolved_rotation
    })

    return {"success": True}


@app.get("/screen/{screen_id}", response_class=HTMLResponse)
async def view_screen(screen_id: str):
    """Serve the screen viewer page."""
    screen = await get_screen_by_id(screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # Return the static HTML file
    html_path = static_path / "screen.html"
    return HTMLResponse(content=html_path.read_text())


@app.get("/admin/screens", response_class=HTMLResponse)
async def admin_screens():
    """Admin page listing all screens."""
    screens = await get_all_screens()

    # Build screen cards
    cards = ""
    for screen in screens:
        screen_url = f"/screen/{screen['id']}"
        api_url = f"/api/screens/{screen['id']}/message"
        viewer_count = manager.get_viewer_count(screen['id'])
        created = screen['created_at'][:19].replace('T', ' ')
        last_updated = screen.get('last_updated')
        last_updated_display = last_updated[:19].replace('T', ' ') if last_updated else 'Never'
        name = screen.get('name') or ''
        name_display = name if name else 'Unnamed Screen'
        name_class = '' if name else 'unnamed'

        cards += f"""
        <div class="screen-card" data-screen-id="{screen['id']}" data-api-key="{screen['api_key']}" data-screen-url="{screen_url}" data-api-url="{api_url}">
            <div class="card-header" onclick="toggleExpand(this.parentElement)">
                <div class="card-summary">
                    <span class="screen-name {name_class}" onclick="editName(this, event)" title="Click to edit name">{name_display}</span>
                    <code class="screen-id">{screen['id']}</code>
                    <a href="{screen_url}" target="_blank" class="screen-link" onclick="event.stopPropagation()">
                        <span class="link-icon">↗</span> {screen_url}
                    </a>
                    <span class="viewer-badge">{viewer_count} viewer{"s" if viewer_count != 1 else ""}</span>
                </div>
                <span class="expand-icon">▼</span>
            </div>
            <div class="card-details">
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>API Key</label>
                        <div class="detail-value">
                            <code class="api-key">{screen['api_key']}</code>
                            <button class="btn-icon" onclick="copyValue(this, '{screen['api_key']}')" title="Copy API Key">📋</button>
                        </div>
                    </div>
                    <div class="detail-item">
                        <label>API Endpoint</label>
                        <div class="detail-value">
                            <code>{api_url}</code>
                            <button class="btn-icon" onclick="copyValue(this, BASE_URL + '{api_url}')" title="Copy API URL">📋</button>
                        </div>
                    </div>
                </div>
                <div class="detail-section">
                    <label>Custom Head HTML <span class="hint">(for Google Fonts, etc.)</span></label>
                    <textarea class="head-html-input" placeholder="<link rel=&quot;preconnect&quot; href=&quot;https://fonts.googleapis.com&quot;>
<link href=&quot;https://fonts.googleapis.com/css2?family=...&quot; rel=&quot;stylesheet&quot;>" onclick="event.stopPropagation()">{screen.get('head_html') or ''}</textarea>
                    <button class="btn-secondary btn-save-head" onclick="saveHeadHtml('{screen['id']}', this); event.stopPropagation();">Save Head HTML</button>
                </div>
                <div class="detail-footer">
                    <div class="detail-timestamps">
                        <span>Created: {created}</span>
                        <span>Last Updated: {last_updated_display}</span>
                    </div>
                    <div class="detail-actions">
                        <div class="copy-dropdown">
                            <button class="btn-secondary" onclick="toggleDropdown(this); event.stopPropagation();">Copy Example ▾</button>
                            <div class="dropdown-menu">
                                <button onclick="copyExample(this, 'bash')">Bash / cURL</button>
                                <button onclick="copyExample(this, 'python')">Python</button>
                            </div>
                        </div>
                        <button class="btn-debug" onclick="toggleDebug('{screen['id']}'); event.stopPropagation();">Toggle Debug</button>
                        <button class="btn-reload" onclick="reloadScreen('{screen['id']}'); event.stopPropagation();">Reload Viewers</button>
                        <button class="btn-delete" onclick="deleteScreen('{screen['id']}'); event.stopPropagation();">Delete Screen</button>
                    </div>
                </div>
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Big Beautiful Screens - Admin</title>
        <link rel="stylesheet" href="/static/admin.css">
    </head>
    <body>
        <div class="container">
            <div class="admin-header">
                <div>
                    <h1>Big Beautiful Screens</h1>
                    <p class="subtitle">Admin Dashboard</p>
                </div>
                <a href="/admin/themes" class="nav-link">Manage Themes →</a>
            </div>

            <div class="actions">
                <button id="create-screen" class="btn-primary">+ Create New Screen</button>
            </div>

            <div class="screen-list">
                {cards if cards else '<div class="empty">No screens yet. Create one to get started!</div>'}
            </div>
        </div>

        <script>
            const BASE_URL = window.location.origin;

            document.getElementById('create-screen').addEventListener('click', async () => {{
                const response = await fetch('/api/screens', {{ method: 'POST' }});
                const data = await response.json();
                // Auto-expand the new screen card after reload
                sessionStorage.setItem('expandScreen', data.screen_id);
                location.reload();
            }});

            // Auto-expand newly created screen
            const expandScreen = sessionStorage.getItem('expandScreen');
            if (expandScreen) {{
                sessionStorage.removeItem('expandScreen');
                const card = document.querySelector(`[data-screen-id="${{expandScreen}}"]`);
                if (card) {{
                    card.classList.add('expanded');
                }}
            }}

            // Close dropdowns when clicking outside
            document.addEventListener('click', (e) => {{
                if (!e.target.closest('.copy-dropdown')) {{
                    document.querySelectorAll('.dropdown-menu.show').forEach(menu => {{
                        menu.classList.remove('show');
                    }});
                }}
            }});

            function toggleExpand(card) {{
                card.classList.toggle('expanded');
            }}

            function toggleDropdown(btn) {{
                const menu = btn.nextElementSibling;
                const wasOpen = menu.classList.contains('show');

                // Close all other dropdowns
                document.querySelectorAll('.dropdown-menu.show').forEach(m => {{
                    m.classList.remove('show');
                }});

                // Toggle this one
                if (!wasOpen) {{
                    menu.classList.add('show');
                }}
            }}

            function getCardData(el) {{
                const card = el.closest('.screen-card');
                return {{
                    screenId: card.dataset.screenId,
                    apiKey: card.dataset.apiKey,
                    screenUrl: card.dataset.screenUrl,
                    apiUrl: card.dataset.apiUrl
                }};
            }}

            function copyValue(btn, value) {{
                navigator.clipboard.writeText(value).then(() => {{
                    const original = btn.textContent;
                    btn.textContent = '✓';
                    btn.classList.add('copied');
                    setTimeout(() => {{
                        btn.textContent = original;
                        btn.classList.remove('copied');
                    }}, 1000);
                }});
                event.stopPropagation();
            }}

            function copyExample(btn, type) {{
                const data = getCardData(btn);
                let text = '';

                if (type === 'bash') {{
                    text = `curl -X POST ${{BASE_URL}}${{data.apiUrl}} \\\\
  -H "Content-Type: application/json" \\\\
  -H "X-API-Key: ${{data.apiKey}}" \\\\
  -d '{{"content": ["Hello, World!"]}}'`;
                }} else if (type === 'python') {{
                    text = `import requests

response = requests.post(
    "${{BASE_URL}}${{data.apiUrl}}",
    headers={{"X-API-Key": "${{data.apiKey}}"}},
    json={{"content": ["Hello, World!"]}}
)
print(response.json())`;
                }}

                navigator.clipboard.writeText(text).then(() => {{
                    const original = btn.textContent;
                    btn.textContent = 'Copied!';
                    btn.classList.add('copied');
                    setTimeout(() => {{
                        btn.textContent = original;
                        btn.classList.remove('copied');
                        btn.closest('.dropdown-menu').classList.remove('show');
                    }}, 1000);
                }});
                event.stopPropagation();
            }}

            async function reloadScreen(screenId) {{
                try {{
                    const response = await fetch(`/api/screens/${{screenId}}/reload`, {{ method: 'POST' }});
                    const data = await response.json();
                    if (response.ok) {{
                        alert(`Reload sent to ${{data.viewers_reloaded}} viewer(s)`);
                    }} else {{
                        alert('Failed to reload: ' + (data.detail || 'Unknown error'));
                    }}
                }} catch (error) {{
                    alert('Failed to reload: ' + error.message);
                }}
            }}

            // Track debug state per screen
            const debugState = {{}};

            async function toggleDebug(screenId) {{
                // Toggle the state
                debugState[screenId] = !debugState[screenId];
                const enabled = debugState[screenId];

                try {{
                    const response = await fetch(`/api/screens/${{screenId}}/debug?enabled=${{enabled}}`, {{ method: 'POST' }});
                    const data = await response.json();
                    if (response.ok) {{
                        alert(`Debug ${{enabled ? 'enabled' : 'disabled'}} for ${{data.viewers}} viewer(s)`);
                    }} else {{
                        alert('Failed to toggle debug: ' + (data.detail || 'Unknown error'));
                    }}
                }} catch (error) {{
                    alert('Failed to toggle debug: ' + error.message);
                }}
            }}

            async function deleteScreen(screenId) {{
                if (!confirm('Are you sure you want to delete this screen? This action cannot be undone.')) {{
                    return;
                }}

                try {{
                    const response = await fetch(`/api/screens/${{screenId}}`, {{ method: 'DELETE' }});
                    if (response.ok) {{
                        location.reload();
                    }} else {{
                        const data = await response.json();
                        alert('Failed to delete screen: ' + (data.detail || 'Unknown error'));
                    }}
                }} catch (error) {{
                    alert('Failed to delete screen: ' + error.message);
                }}
            }}

            async function saveHeadHtml(screenId, btn) {{
                const card = btn.closest('.screen-card');
                const apiKey = card.dataset.apiKey;
                const textarea = card.querySelector('.head-html-input');
                const headHtml = textarea.value;

                try {{
                    btn.disabled = true;
                    btn.textContent = 'Saving...';

                    const response = await fetch(`/api/screens/${{screenId}}`, {{
                        method: 'PATCH',
                        headers: {{
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey
                        }},
                        body: JSON.stringify({{ head_html: headHtml }})
                    }});

                    if (response.ok) {{
                        btn.textContent = 'Saved!';
                        setTimeout(() => {{
                            btn.textContent = 'Save Head HTML';
                            btn.disabled = false;
                        }}, 1500);
                    }} else {{
                        const data = await response.json();
                        alert('Failed to save: ' + (data.detail || 'Unknown error'));
                        btn.textContent = 'Save Head HTML';
                        btn.disabled = false;
                    }}
                }} catch (error) {{
                    alert('Failed to save: ' + error.message);
                    btn.textContent = 'Save Head HTML';
                    btn.disabled = false;
                }}
            }}

            function editName(el, event) {{
                event.stopPropagation();
                const card = el.closest('.screen-card');
                const screenId = card.dataset.screenId;
                const currentName = el.classList.contains('unnamed') ? '' : el.textContent;

                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'name-input';
                input.value = currentName;
                input.placeholder = 'Enter screen name...';

                const saveName = async () => {{
                    const newName = input.value.trim();
                    try {{
                        const response = await fetch(`/api/screens/${{screenId}}?name=${{encodeURIComponent(newName)}}`, {{
                            method: 'PATCH'
                        }});
                        if (response.ok) {{
                            el.textContent = newName || 'Unnamed Screen';
                            el.classList.toggle('unnamed', !newName);
                        }}
                    }} catch (error) {{
                        console.error('Failed to update name:', error);
                    }}
                    input.replaceWith(el);
                }};

                input.addEventListener('blur', saveName);
                input.addEventListener('keydown', (e) => {{
                    if (e.key === 'Enter') {{
                        e.preventDefault();
                        input.blur();
                    }}
                    if (e.key === 'Escape') {{
                        input.value = currentName;
                        input.blur();
                    }}
                }});

                el.replaceWith(input);
                input.focus();
                input.select();
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/admin/themes", response_class=HTMLResponse)
async def admin_themes():
    """Admin page for managing themes."""
    themes = await get_all_themes()
    usage_counts = await get_theme_usage_counts()

    # Build theme cards
    cards = ""
    for theme in themes:
        usage_count = usage_counts.get(theme["name"], 0)
        builtin_badge = '<span class="builtin-badge">Built-in</span>' if theme["is_builtin"] else ''
        usage_badge = f'<span class="usage-badge">{usage_count} screen{"s" if usage_count != 1 else ""}</span>'

        # Escape values for HTML attributes
        bg_color = theme["background_color"] or ""
        panel_color = theme["panel_color"] or ""
        font_color = theme["font_color"] or ""
        font_family = theme["font_family"] or ""
        gap = theme["gap"] or "1rem"
        border_radius = theme["border_radius"] or "1rem"
        panel_shadow = theme["panel_shadow"] or ""

        cards += f"""
        <div class="theme-card" data-theme-name="{theme['name']}">
            <div class="card-header" onclick="toggleExpand(this.parentElement)">
                <div class="card-summary">
                    <span class="theme-name">{theme['display_name'] or theme['name']}</span>
                    <code class="theme-id">{theme['name']}</code>
                    <div class="theme-swatches">
                        <span class="color-swatch" style="background: {bg_color};" title="Background"></span>
                        <span class="color-swatch" style="background: {panel_color};" title="Panel"></span>
                        <span class="color-swatch" style="background: {font_color};" title="Text"></span>
                    </div>
                    {builtin_badge}
                    {usage_badge}
                </div>
                <span class="expand-icon">▼</span>
            </div>
            <div class="card-details">
                <div class="theme-editor">
                    <div class="editor-grid">
                        <div class="editor-field">
                            <label>Display Name</label>
                            <input type="text" class="theme-input" data-field="display_name"
                                   value="{theme['display_name'] or ''}" placeholder="Theme display name">
                        </div>
                        <div class="editor-field">
                            <label>Background Color</label>
                            <input type="text" class="theme-input" data-field="background_color"
                                   value="{bg_color}" placeholder="#1e1e2e or linear-gradient(...)">
                        </div>
                        <div class="editor-field">
                            <label>Panel Color</label>
                            <input type="text" class="theme-input" data-field="panel_color"
                                   value="{panel_color}" placeholder="#313244 or rgba(...)">
                        </div>
                        <div class="editor-field">
                            <label>Font Color</label>
                            <input type="text" class="theme-input" data-field="font_color"
                                   value="{font_color}" placeholder="#cdd6f4">
                        </div>
                        <div class="editor-field">
                            <label>Font Family</label>
                            <input type="text" class="theme-input" data-field="font_family"
                                   value="{font_family}" placeholder="system-ui, sans-serif">
                        </div>
                        <div class="editor-field">
                            <label>Gap</label>
                            <input type="text" class="theme-input" data-field="gap"
                                   value="{gap}" placeholder="1rem">
                        </div>
                        <div class="editor-field">
                            <label>Border Radius</label>
                            <input type="text" class="theme-input" data-field="border_radius"
                                   value="{border_radius}" placeholder="0.75rem">
                        </div>
                        <div class="editor-field">
                            <label>Panel Shadow</label>
                            <input type="text" class="theme-input" data-field="panel_shadow"
                                   value="{panel_shadow}" placeholder="0 4px 12px rgba(0,0,0,0.3)">
                        </div>
                    </div>
                    <div class="theme-preview" id="preview-{theme['name']}">
                        <div class="preview-container" style="background: {bg_color}; padding: {gap}; border-radius: 8px;">
                            <div class="preview-panel" style="background: {panel_color}; color: {font_color}; font-family: {font_family}; padding: 1rem; border-radius: {border_radius}; box-shadow: {panel_shadow};">
                                Preview Text
                            </div>
                        </div>
                    </div>
                </div>
                <div class="detail-footer">
                    <div class="detail-actions">
                        <button class="btn-primary" onclick="saveTheme('{theme['name']}', this); event.stopPropagation();">Save Changes</button>
                        <button class="btn-secondary" onclick="duplicateTheme('{theme['name']}'); event.stopPropagation();">Duplicate</button>
                        <button class="btn-delete" onclick="deleteTheme('{theme['name']}', {usage_count}); event.stopPropagation();" {'disabled title="In use by screens"' if usage_count > 0 else ''}>Delete</button>
                    </div>
                </div>
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Theme Management - Big Beautiful Screens</title>
        <link rel="stylesheet" href="/static/admin.css">
    </head>
    <body>
        <div class="container">
            <div class="admin-header">
                <div>
                    <h1>Theme Management</h1>
                    <p class="subtitle">Create and customize themes</p>
                </div>
                <a href="/admin/screens" class="nav-link">← Back to Screens</a>
            </div>

            <div class="actions">
                <button id="create-theme" class="btn-primary">+ Create New Theme</button>
            </div>

            <div class="theme-list">
                {cards if cards else '<div class="empty">No themes found. Create one to get started!</div>'}
            </div>
        </div>

        <!-- Create Theme Modal -->
        <div id="create-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Create New Theme</h2>
                    <button class="modal-close" onclick="closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="editor-grid">
                        <div class="editor-field">
                            <label>Theme ID (URL-safe)</label>
                            <input type="text" id="new-theme-name" class="new-theme-input" placeholder="my-custom-theme" pattern="[a-z0-9-_]+">
                        </div>
                        <div class="editor-field">
                            <label>Display Name</label>
                            <input type="text" id="new-theme-display" class="new-theme-input" placeholder="My Custom Theme">
                        </div>
                        <div class="editor-field">
                            <label>Background Color</label>
                            <input type="text" id="new-theme-bg" class="new-theme-input" data-preview="bg" value="#1e1e2e" placeholder="#1e1e2e">
                        </div>
                        <div class="editor-field">
                            <label>Panel Color</label>
                            <input type="text" id="new-theme-panel" class="new-theme-input" data-preview="panel" value="#313244" placeholder="#313244">
                        </div>
                        <div class="editor-field">
                            <label>Font Color</label>
                            <input type="text" id="new-theme-font-color" class="new-theme-input" data-preview="font-color" value="#cdd6f4" placeholder="#cdd6f4">
                        </div>
                        <div class="editor-field">
                            <label>Font Family</label>
                            <input type="text" id="new-theme-font-family" class="new-theme-input" data-preview="font-family" value="system-ui, -apple-system, sans-serif">
                        </div>
                    </div>
                    <div class="theme-preview" id="new-theme-preview">
                        <div class="preview-container" style="background: #1e1e2e; padding: 1rem; border-radius: 8px;">
                            <div class="preview-panel" style="background: #313244; color: #cdd6f4; font-family: system-ui, -apple-system, sans-serif; padding: 1rem; border-radius: 0.75rem;">
                                <span>Preview Text</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="closeModal()">Cancel</button>
                    <button class="btn-primary" onclick="submitCreateTheme()">Create Theme</button>
                </div>
            </div>
        </div>

        <script>
            function toggleExpand(card) {{
                card.classList.toggle('expanded');
            }}

            // Create theme modal
            document.getElementById('create-theme').addEventListener('click', () => {{
                document.getElementById('create-modal').style.display = 'flex';
            }});

            function closeModal() {{
                document.getElementById('create-modal').style.display = 'none';
            }}

            // Close modal on outside click
            document.getElementById('create-modal').addEventListener('click', (e) => {{
                if (e.target.id === 'create-modal') closeModal();
            }});

            async function submitCreateTheme() {{
                const name = document.getElementById('new-theme-name').value.trim();
                const displayName = document.getElementById('new-theme-display').value.trim();
                const bgColor = document.getElementById('new-theme-bg').value.trim();
                const panelColor = document.getElementById('new-theme-panel').value.trim();
                const fontColor = document.getElementById('new-theme-font-color').value.trim();
                const fontFamily = document.getElementById('new-theme-font-family').value.trim();

                if (!name) {{
                    alert('Theme ID is required');
                    return;
                }}

                try {{
                    const response = await fetch('/api/themes', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            name: name,
                            display_name: displayName || null,
                            background_color: bgColor,
                            panel_color: panelColor,
                            font_color: fontColor,
                            font_family: fontFamily
                        }})
                    }});

                    if (response.ok) {{
                        location.reload();
                    }} else {{
                        const data = await response.json();
                        alert('Failed to create theme: ' + (data.detail || 'Unknown error'));
                    }}
                }} catch (error) {{
                    alert('Failed to create theme: ' + error.message);
                }}
            }}

            async function saveTheme(themeName, btn) {{
                const card = btn.closest('.theme-card');
                const inputs = card.querySelectorAll('.theme-input');
                const updates = {{}};

                inputs.forEach(input => {{
                    const field = input.dataset.field;
                    const value = input.value.trim();
                    if (value) {{
                        updates[field] = value;
                    }}
                }});

                try {{
                    btn.disabled = true;
                    btn.textContent = 'Saving...';

                    const response = await fetch(`/api/themes/${{themeName}}`, {{
                        method: 'PATCH',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(updates)
                    }});

                    if (response.ok) {{
                        btn.textContent = 'Saved!';
                        updatePreview(card);
                        setTimeout(() => {{
                            btn.textContent = 'Save Changes';
                            btn.disabled = false;
                        }}, 1500);
                    }} else {{
                        const data = await response.json();
                        alert('Failed to save: ' + (data.detail || 'Unknown error'));
                        btn.textContent = 'Save Changes';
                        btn.disabled = false;
                    }}
                }} catch (error) {{
                    alert('Failed to save: ' + error.message);
                    btn.textContent = 'Save Changes';
                    btn.disabled = false;
                }}
            }}

            async function deleteTheme(themeName, usageCount) {{
                if (usageCount > 0) {{
                    alert(`Cannot delete theme: it is in use by ${{usageCount}} screen(s)`);
                    return;
                }}

                if (!confirm(`Are you sure you want to delete the theme "${{themeName}}"?`)) {{
                    return;
                }}

                try {{
                    const response = await fetch(`/api/themes/${{themeName}}`, {{
                        method: 'DELETE'
                    }});

                    if (response.ok) {{
                        location.reload();
                    }} else {{
                        const data = await response.json();
                        alert('Failed to delete: ' + (data.detail || 'Unknown error'));
                    }}
                }} catch (error) {{
                    alert('Failed to delete: ' + error.message);
                }}
            }}

            async function duplicateTheme(themeName) {{
                const newName = prompt('Enter a name for the new theme:', themeName + '-copy');
                if (!newName) return;

                try {{
                    // First get the theme data
                    const getResponse = await fetch(`/api/themes/${{themeName}}`);
                    if (!getResponse.ok) {{
                        alert('Failed to get theme data');
                        return;
                    }}
                    const theme = await getResponse.json();

                    // Create new theme with same values
                    const response = await fetch('/api/themes', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            name: newName,
                            display_name: (theme.display_name || theme.name) + ' (Copy)',
                            background_color: theme.background_color,
                            panel_color: theme.panel_color,
                            font_color: theme.font_color,
                            font_family: theme.font_family,
                            gap: theme.gap,
                            border_radius: theme.border_radius,
                            panel_shadow: theme.panel_shadow
                        }})
                    }});

                    if (response.ok) {{
                        location.reload();
                    }} else {{
                        const data = await response.json();
                        alert('Failed to duplicate: ' + (data.detail || 'Unknown error'));
                    }}
                }} catch (error) {{
                    alert('Failed to duplicate: ' + error.message);
                }}
            }}

            function updatePreview(card) {{
                const themeName = card.dataset.themeName;
                const preview = card.querySelector('.theme-preview');
                const container = preview.querySelector('.preview-container');
                const panel = preview.querySelector('.preview-panel');

                const getValue = (field) => {{
                    const input = card.querySelector(`[data-field="${{field}}"]`);
                    return input ? input.value : '';
                }};

                container.style.background = getValue('background_color');
                container.style.padding = getValue('gap') || '1rem';
                panel.style.background = getValue('panel_color');
                panel.style.color = getValue('font_color');
                panel.style.fontFamily = getValue('font_family');
                panel.style.borderRadius = getValue('border_radius') || '0.75rem';
                panel.style.boxShadow = getValue('panel_shadow') || 'none';
            }}

            // Live preview on input change for existing themes
            document.querySelectorAll('.theme-input').forEach(input => {{
                input.addEventListener('input', () => {{
                    const card = input.closest('.theme-card');
                    updatePreview(card);
                }});
            }});

            // Live preview for new theme modal
            function updateNewThemePreview() {{
                const preview = document.getElementById('new-theme-preview');
                const container = preview.querySelector('.preview-container');
                const panel = preview.querySelector('.preview-panel');

                container.style.background = document.getElementById('new-theme-bg').value || '#1e1e2e';
                panel.style.background = document.getElementById('new-theme-panel').value || '#313244';
                panel.style.color = document.getElementById('new-theme-font-color').value || '#cdd6f4';
                panel.style.fontFamily = document.getElementById('new-theme-font-family').value || 'system-ui';
            }}

            document.querySelectorAll('.new-theme-input').forEach(input => {{
                input.addEventListener('input', updateNewThemePreview);
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.websocket("/ws/{screen_id}")
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

        await websocket.send_json({
            "type": "pages_sync",
            "pages": pages,
            "rotation": resolved_rotation
        })

        # Also send legacy message format for backward compatibility
        last_message = await get_last_message(screen_id)
        if last_message:
            await websocket.send_json({
                "type": "message",
                **last_message
            })

        # Keep connection alive and handle incoming messages
        while True:
            # We don't expect messages from viewers, but need to keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(screen_id, websocket)


async def resolve_theme_settings(rotation: dict) -> dict:
    """Resolve theme values and merge with screen-level overrides.

    Theme values are used as defaults; explicit screen values override them.
    """
    if not rotation:
        return rotation

    theme_name = rotation.get("theme")
    if not theme_name:
        return rotation

    # Look up theme from database
    theme = await get_theme_from_db(theme_name)
    if not theme:
        return rotation

    # Merge: screen values override theme values
    resolved = rotation.copy()
    for key in ["background_color", "panel_color", "font_family", "font_color",
                "gap", "border_radius", "panel_shadow"]:
        # Use screen value if set, otherwise use theme value
        if resolved.get(key) is None:
            resolved[key] = theme.get(key)

    return resolved


def normalize_content(content: list) -> list:
    """Normalize content items to structured format with auto-detection."""
    normalized = []

    for item in content:
        if isinstance(item, str):
            normalized.append(detect_content_type(item))
        else:
            # Already structured (ContentItem)
            if item.type == "image":
                entry = {"type": "image", "url": item.url or item.value}
            elif item.type == "video":
                entry = {
                    "type": "video",
                    "url": item.url or item.value,
                    "autoplay": item.autoplay if item.autoplay is not None else True,
                    "loop": item.loop if item.loop is not None else True,
                    "muted": item.muted if item.muted is not None else True
                }
            else:
                entry = {"type": item.type, "value": item.value}

            # Preserve per-panel styling if specified
            if item.panel_color:
                entry["panel_color"] = item.panel_color
            if item.font_family:
                entry["font_family"] = item.font_family
            if item.font_color:
                entry["font_color"] = item.font_color
            if item.image_mode:
                entry["image_mode"] = item.image_mode
            if item.wrap is not None:
                entry["wrap"] = item.wrap

            normalized.append(entry)

    return normalized


def detect_content_type(text: str) -> dict:
    """Auto-detect content type from a string."""
    text_lower = text.lower()

    # Check if it's a video URL
    video_extensions = ('.mp4', '.webm', '.ogg', '.mov')
    if text_lower.startswith('http') and any(text_lower.endswith(ext) for ext in video_extensions):
        return {"type": "video", "url": text, "autoplay": True, "loop": True, "muted": True}

    # Check if it's an image URL
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp')
    if text_lower.startswith('http') and any(text_lower.endswith(ext) for ext in image_extensions):
        return {"type": "image", "url": text}

    # Check if it contains markdown syntax
    markdown_indicators = ['# ', '## ', '### ', '**', '__', '```', '- ', '* ', '1. ', '> ']
    if any(indicator in text for indicator in markdown_indicators):
        return {"type": "markdown", "value": text}

    # Default to plain text
    return {"type": "text", "value": text}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
