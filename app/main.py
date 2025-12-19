import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .models import MessageRequest, ScreenResponse, MessageResponse
from .database import init_db, create_screen, get_screen_by_id, get_screen_by_api_key, save_message, get_last_message, get_all_screens, delete_screen
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

    # Build HTML table rows
    rows = ""
    for screen in screens:
        screen_url = f"/screen/{screen['id']}"
        api_url = f"/api/screens/{screen['id']}/message"

        viewer_count = manager.get_viewer_count(screen['id'])
        rows += f"""
        <tr data-screen-id="{screen['id']}" data-api-key="{screen['api_key']}" data-screen-url="{screen_url}" data-api-url="{api_url}">
            <td data-label="Screen ID"><code>{screen['id']}</code></td>
            <td data-label="API Key"><code class="api-key">{screen['api_key']}</code></td>
            <td data-label="Screen URL"><a href="{screen_url}" target="_blank">{screen_url}</a></td>
            <td data-label="API URL"><code>{api_url}</code></td>
            <td data-label="Created">{screen['created_at'][:19].replace('T', ' ')}</td>
            <td data-label="Viewers" class="viewers-cell">{viewer_count}</td>
            <td class="actions-cell">
                <div class="copy-dropdown">
                    <button class="btn-copy" onclick="toggleDropdown(this)">Copy ▾</button>
                    <div class="dropdown-menu">
                        <button onclick="copyFromRow(this, 'screen-id')">Screen ID</button>
                        <button onclick="copyFromRow(this, 'api-key')">API Key</button>
                        <button onclick="copyFromRow(this, 'screen-url')">Screen URL</button>
                        <button onclick="copyFromRow(this, 'api-url')">API URL</button>
                        <hr>
                        <button onclick="copyExample(this, 'bash')">Bash Example</button>
                        <button onclick="copyExample(this, 'python')">Python Example</button>
                    </div>
                </div>
                <button class="btn-reload" onclick="reloadScreen('{screen['id']}')">Reload</button>
                <button class="btn-delete" onclick="deleteScreen('{screen['id']}')">Delete</button>
            </td>
        </tr>
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

            <table>
                <thead>
                    <tr>
                        <th>Screen ID</th>
                        <th>API Key</th>
                        <th>Screen URL</th>
                        <th>API URL</th>
                        <th>Created</th>
                        <th>Viewers</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="7" class="empty">No screens yet. Create one to get started!</td></tr>'}
                </tbody>
            </table>
        </div>

        <script>
            const BASE_URL = window.location.origin;

            document.getElementById('create-screen').addEventListener('click', async () => {{
                const response = await fetch('/api/screens', {{ method: 'POST' }});
                const data = await response.json();
                alert('Screen created!\\n\\nScreen ID: ' + data.screen_id + '\\nAPI Key: ' + data.api_key);
                location.reload();
            }});

            // Close dropdowns when clicking outside
            document.addEventListener('click', (e) => {{
                if (!e.target.closest('.copy-dropdown')) {{
                    document.querySelectorAll('.dropdown-menu.show').forEach(menu => {{
                        menu.classList.remove('show');
                    }});
                }}
            }});

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

            function getRowData(btn) {{
                const row = btn.closest('tr');
                return {{
                    screenId: row.dataset.screenId,
                    apiKey: row.dataset.apiKey,
                    screenUrl: row.dataset.screenUrl,
                    apiUrl: row.dataset.apiUrl
                }};
            }}

            function copyFromRow(btn, field) {{
                const data = getRowData(btn);
                const values = {{
                    'screen-id': data.screenId,
                    'api-key': data.apiKey,
                    'screen-url': BASE_URL + data.screenUrl,
                    'api-url': BASE_URL + data.apiUrl
                }};
                copyAndFeedback(btn, values[field]);
            }}

            function copyExample(btn, type) {{
                const data = getRowData(btn);
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
                copyAndFeedback(btn, text);
            }}

            function copyAndFeedback(btn, text) {{
                navigator.clipboard.writeText(text).then(() => {{
                    const originalText = btn.textContent;
                    btn.textContent = 'Copied!';
                    btn.classList.add('copied');
                    setTimeout(() => {{
                        btn.textContent = originalText;
                        btn.classList.remove('copied');
                        btn.closest('.dropdown-menu').classList.remove('show');
                    }}, 1000);
                }});
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
