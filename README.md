# Big Beautiful Screens

A MicroSaaS that provides developers with API endpoints to push content to real-time display screens. Point any device (Smart TV, browser, Raspberry Pi) at a screen URL and receive live updates via WebSocket.

## Features

- **Real-time updates** via WebSocket - changes appear instantly on all connected viewers
- **Auto-layout** - content automatically arranges based on the number of items
- **Auto-scaling text** - text sizes itself to fill available space
- **Text wrapping** - optional word-wrap for larger text display
- **Markdown support** - headings, bold, italic, code blocks, and more (auto-scaled)
- **Image support** - display images with multiple sizing modes
- **Video support** - embed videos with autoplay, loop, and mute controls
- **Custom colors** - set background and panel colors globally or per-panel
- **Custom fonts** - set font family and color globally or per-panel
- **Message persistence** - new viewers see the last message immediately
- **Admin dashboard** - view all screens, active viewers, copy credentials, reload or delete screens

## Quick Start

### Installation

```bash
cd big-beautiful-screens
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running the Server

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The server will be available at `http://localhost:8000`

### Admin Dashboard

Visit `http://localhost:8000/admin/screens` to:
- View all screens with active viewer counts
- Create new screens
- Copy API keys, URLs, and code examples
- Remotely reload screen viewers (clears browser cache)
- Delete screens

## API Reference

### Create a Screen

```bash
curl -X POST http://localhost:8000/api/screens
```

**Response:**
```json
{
  "screen_id": "abc123def456",
  "api_key": "sk_AbCdEfGhIjKlMnOpQrStUvWx",
  "screen_url": "/screen/abc123def456",
  "api_url": "/api/screens/abc123def456/message"
}
```

### Send Content to a Screen

```bash
curl -X POST http://localhost:8000/api/screens/{screen_id}/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"content": ["Hello, World!"]}'
```

**Response:**
```json
{
  "success": true,
  "viewers": 2
}
```

### Reload Screen Viewers

Force all connected viewers to refresh (useful for clearing cached assets):

```bash
curl -X POST http://localhost:8000/api/screens/{screen_id}/reload
```

### Delete a Screen

```bash
curl -X DELETE http://localhost:8000/api/screens/{screen_id}
```

## Content Types

Content is auto-detected based on the string:

| Input | Detected Type |
|-------|---------------|
| `"Hello World"` | Plain text |
| `"# Heading\nSome text"` | Markdown |
| `"https://example.com/image.jpg"` | Image |
| `"https://example.com/video.mp4"` | Video |

You can also explicitly specify the type:

```json
{
  "content": [
    {"type": "text", "value": "Plain text"},
    {"type": "markdown", "value": "# Heading"},
    {"type": "image", "url": "https://example.com/image.png"},
    {"type": "video", "url": "https://example.com/video.mp4"}
  ]
}
```

## Styling Options

### Custom Colors

Set background and panel colors:

```json
{
  "content": ["Panel 1", "Panel 2"],
  "background_color": "#0d1b2a",
  "panel_color": "#1b263b"
}
```

Override color for individual panels:

```json
{
  "content": [
    {"type": "text", "value": "Normal panel"},
    {"type": "text", "value": "Red panel", "color": "#c0392b"},
    {"type": "text", "value": "Green panel", "color": "#27ae60"}
  ]
}
```

### Custom Fonts

Set font family and color globally:

```json
{
  "content": ["Hello World"],
  "font_family": "Georgia, serif",
  "font_color": "#f1c40f"
}
```

Or per-panel:

```json
{
  "content": [
    {"type": "text", "value": "Monospace", "font_family": "monospace", "font_color": "#2ecc71"},
    {"type": "text", "value": "Serif", "font_family": "Georgia, serif", "font_color": "#e74c3c"}
  ]
}
```

### Text Wrapping

By default, text wraps at word boundaries to maximize font size. Disable wrapping to keep text on a single line:

```json
{
  "content": [
    {"type": "text", "value": "This will wrap to multiple lines if needed", "wrap": true},
    {"type": "text", "value": "This stays on one line", "wrap": false}
  ]
}
```

### Image Display Modes

Control how images fill their panel:

| Mode | Description |
|------|-------------|
| `contain` | Fit entire image in panel (default) |
| `cover` | Fill panel, crop edges (edge-to-edge, no panel visible) |
| `cover-width` | Fill panel width, may overflow height |
| `cover-height` | Fill panel height, may overflow width |

```json
{
  "content": [
    {"type": "image", "url": "https://example.com/photo.jpg", "image_mode": "cover"}
  ]
}
```

### Video Options

Videos support autoplay, loop, and mute controls (all default to `true`):

```json
{
  "content": [
    {
      "type": "video",
      "url": "https://example.com/video.mp4",
      "autoplay": true,
      "loop": true,
      "muted": true,
      "image_mode": "cover"
    }
  ]
}
```

## Auto-Layout

The screen automatically arranges content based on the number of items:

| Items | Layout |
|-------|--------|
| 1 | Full screen |
| 2 | Side by side (50/50) |
| 3 | Top half + bottom split |
| 4 | 2x2 grid |
| 5-6 | 3-column grid |

## Viewing Screens

Open the screen URL in any browser:

```
http://localhost:8000/screen/{screen_id}
```

Works on:
- Desktop browsers
- Mobile browsers
- Smart TVs
- Raspberry Pi with a browser
- Any device with a web browser

## Examples

### Simple Text Display

```bash
curl -X POST http://localhost:8000/api/screens/{id}/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{"content": ["Build Status: PASSING"]}'
```

### Dashboard with Multiple Panels

```bash
curl -X POST http://localhost:8000/api/screens/{id}/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{
    "content": [
      "# Sales Today\n$12,345",
      "# Active Users\n1,234",
      "# Server Status\nAll systems operational"
    ],
    "background_color": "#1a1a2e",
    "panel_color": "#16213e"
  }'
```

### Status Board with Colors

```bash
curl -X POST http://localhost:8000/api/screens/{id}/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{
    "content": [
      {"type": "text", "value": "Production: OK", "color": "#27ae60"},
      {"type": "text", "value": "Staging: DEPLOYING", "color": "#f39c12"},
      {"type": "text", "value": "Dev: FAILED", "color": "#c0392b"}
    ]
  }'
```

### Metrics Display with Markdown

```bash
curl -X POST http://localhost:8000/api/screens/{id}/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{
    "content": [
      {"type": "markdown", "value": "Power Produced:\n# 1,287\n*Megawatts*"}
    ]
  }'
```

### Full-Screen Image

```bash
curl -X POST http://localhost:8000/api/screens/{id}/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{
    "content": [
      {"type": "image", "url": "https://picsum.photos/1920/1080", "image_mode": "cover"}
    ]
  }'
```

### Video Background

```bash
curl -X POST http://localhost:8000/api/screens/{id}/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{
    "content": [
      {"type": "video", "url": "https://example.com/background.mp4", "image_mode": "cover"}
    ]
  }'
```

## Python Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Create a screen
response = requests.post(f"{BASE_URL}/api/screens")
screen = response.json()

screen_id = screen["screen_id"]
api_key = screen["api_key"]

print(f"View your screen at: {BASE_URL}/screen/{screen_id}")

# Send content
requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={
        "content": [
            {"type": "markdown", "value": "# Hello from Python!\n*Auto-scaled markdown*"}
        ],
        "background_color": "#2c3e50",
        "font_family": "Georgia, serif"
    }
)

# Reload all viewers (clear cache)
requests.post(f"{BASE_URL}/api/screens/{screen_id}/reload")
```

## Project Structure

```
big-beautiful-screens/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app with all routes
│   ├── models.py            # Pydantic models
│   ├── database.py          # SQLite operations
│   └── connection_manager.py # WebSocket management
├── static/
│   ├── screen.html          # Screen viewer page
│   ├── screen.js            # Client-side rendering
│   ├── screen.css           # Screen styling
│   └── admin.css            # Admin page styling
├── data/                    # SQLite database (auto-created)
├── requirements.txt
└── README.md
```

## License

MIT
