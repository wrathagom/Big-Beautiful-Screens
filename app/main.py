import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .models import MessageRequest, ScreenResponse, MessageResponse
from .database import init_db, create_screen, get_screen_by_id, get_screen_by_api_key, save_message, get_last_message, get_all_screens, delete_screen, update_screen_name
from .connection_manager import manager

app = FastAPI(title="Big Beautiful Screens", version="0.1.0")

# Mount static files
static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.on_event("startup")
async def startup():
    await init_db()


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
    """Send a message to a screen. Requires API key authentication."""
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
        "font_color": request.font_color
    }

    # Save message to database
    created_at = datetime.now(timezone.utc).isoformat()
    await save_message(screen_id, message_payload, created_at)

    # Broadcast to all connected viewers
    viewers = await manager.broadcast(screen_id, {
        "type": "message",
        **message_payload
    })

    return MessageResponse(success=True, viewers=viewers)


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


@app.patch("/api/screens/{screen_id}")
async def update_screen(screen_id: str, name: str | None = None):
    """Update a screen's properties (currently just name)."""
    updated = await update_screen_name(screen_id, name)
    if not updated:
        raise HTTPException(status_code=404, detail="Screen not found")
    return {"success": True, "name": name}


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
            <h1>Big Beautiful Screens</h1>
            <p class="subtitle">Admin Dashboard</p>

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
        # Send the last message if one exists
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
            if item.color:
                entry["color"] = item.color
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
