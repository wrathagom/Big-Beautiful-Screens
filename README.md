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
- **Customizable gaps** - control spacing between panels (like a tiling window manager)
- **Customizable corners** - control panel border radius for sharp or rounded corners
- **Panel shadows** - optional drop shadows for depth and visual hierarchy
- **Gradient support** - use CSS gradients for backgrounds and panels
- **Screen-level defaults** - set default colors/fonts that apply to all pages
- **Message persistence** - new viewers see the last message immediately
- **Admin dashboard** - view all screens, active viewers, copy credentials, reload or delete screens
- **Multi-page support** - screens can have multiple named pages that rotate automatically
- **Page rotation** - configurable timer to cycle between pages with per-page duration overrides
- **Ephemeral pages** - temporary pages that auto-expire after a set time

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

### Pages API

Screens support multiple named pages that can rotate automatically. The existing `/message` endpoint updates the "default" page for backward compatibility.

#### List All Pages

```bash
curl http://localhost:8000/api/screens/{screen_id}/pages
```

**Response:**
```json
{
  "pages": [
    {"name": "default", "content": [...], "display_order": 0, "duration": null, "expires_at": null},
    {"name": "alerts", "content": [...], "display_order": 1, "duration": 10, "expires_at": null}
  ],
  "rotation": {"enabled": true, "interval": 30}
}
```

#### Create or Update a Page

```bash
curl -X POST http://localhost:8000/api/screens/{screen_id}/pages/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": ["ALERT: Server maintenance in 10 minutes"],
    "background_color": "#c0392b",
    "duration": 10
  }'
```

Optional fields:
- `duration` - seconds to display this page (overrides screen default)
- `expires_at` - ISO timestamp for ephemeral pages (e.g., `"2024-12-31T23:59:59Z"`)
- `gap` - panel gap for this page (overrides screen default, e.g., `"0"`, `"1rem"`)
- `border_radius` - panel corner radius for this page (overrides screen default)
- `panel_shadow` - CSS box-shadow for this page (overrides screen default)

#### Delete a Page

```bash
curl -X DELETE http://localhost:8000/api/screens/{screen_id}/pages/alerts \
  -H "X-API-Key: sk_your_api_key"
```

Note: The "default" page cannot be deleted.

#### Update Screen Settings

```bash
curl -X PATCH "http://localhost:8000/api/screens/{screen_id}" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "rotation_enabled": true,
    "rotation_interval": 30,
    "background_color": "linear-gradient(90deg, #2a7b9b 0%, #57c785 100%)"
  }'
```

Available settings:
- `name` - Screen display name (no API key required)
- `rotation_enabled` - Enable/disable page rotation
- `rotation_interval` - Seconds between page transitions
- `gap` - Space between panels (e.g., `"1rem"`, `"0"`)
- `border_radius` - Panel corner rounding (e.g., `"1rem"`, `"0"`)
- `panel_shadow` - CSS box-shadow for panels
- `background_color` - Default background (supports gradients)
- `panel_color` - Default panel color (supports gradients)
- `font_family` - Default font family
- `font_color` - Default text color

#### Reorder Pages

```bash
curl -X PUT http://localhost:8000/api/screens/{screen_id}/pages/order \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"page_names": ["alerts", "default", "weather"]}'
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
    {"type": "text", "value": "Red panel", "panel_color": "#c0392b"},
    {"type": "text", "value": "Green panel", "panel_color": "#27ae60"}
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

### Panel Gaps

Control the spacing between panels, similar to gaps in a tiling window manager. The gap value is any valid CSS size (e.g., `"1rem"`, `"10px"`, `"0"`).

**Screen-level default gap** (applies to all pages):

```bash
curl -X PATCH "http://localhost:8000/api/screens/{id}?gap=0.5rem" \
  -H "X-API-Key: {api_key}"
```

**Per-page gap override**:

```json
{
  "content": ["Panel 1", "Panel 2", "Panel 3", "Panel 4"],
  "gap": "0"
}
```

**Per-message gap** (when using the `/message` endpoint):

```json
{
  "content": ["Tight Grid", "No Spacing"],
  "gap": "2px"
}
```

Common gap values:
| Value | Description |
|-------|-------------|
| `"1rem"` | Default spacing (comfortable padding) |
| `"0.5rem"` | Compact layout |
| `"0"` | Edge-to-edge panels (true tiling) |
| `"2rem"` | Extra spacious |

### Panel Corner Radius

Control the corner rounding of panels. The value is any valid CSS border-radius (e.g., `"1rem"`, `"10px"`, `"0"`).

**Screen-level default radius** (applies to all pages):

```bash
curl -X PATCH "http://localhost:8000/api/screens/{id}?border_radius=0" \
  -H "X-API-Key: {api_key}"
```

**Per-page radius override**:

```json
{
  "content": ["Sharp Corners"],
  "border_radius": "0"
}
```

Common border radius values:
| Value | Description |
|-------|-------------|
| `"1rem"` | Default rounded corners |
| `"0.5rem"` | Subtle rounding |
| `"0"` | Sharp corners (true tiling) |
| `"2rem"` | Very rounded |

**Tiling window manager style** (zero gap + zero radius):

```bash
curl -X PATCH "http://localhost:8000/api/screens/{id}?gap=0&border_radius=0" \
  -H "X-API-Key: {api_key}"
```

### Panel Shadows

Add depth to panels with CSS box-shadow. Shadows are disabled by default (no shadow).

**Screen-level shadow** (applies to all pages):

```bash
curl -X PATCH "http://localhost:8000/api/screens/{id}?panel_shadow=0%204px%2012px%20rgba(0,0,0,0.3)" \
  -H "X-API-Key: {api_key}"
```

**Per-page shadow override**:

```json
{
  "content": ["Elevated Panel"],
  "panel_shadow": "0 8px 24px rgba(0,0,0,0.4)"
}
```

Common shadow values:
| Value | Description |
|-------|-------------|
| `null` or omit | No shadow (default) |
| `"0 2px 4px rgba(0,0,0,0.1)"` | Subtle lift |
| `"0 4px 12px rgba(0,0,0,0.3)"` | Medium depth |
| `"0 8px 24px rgba(0,0,0,0.4)"` | Strong elevation |

### Gradient Backgrounds

Both `background_color` and `panel_color` accept any valid CSS value, including gradients:

**Page background gradient**:

```json
{
  "content": ["Content on gradient"],
  "background_color": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
}
```

**Panel gradient**:

```json
{
  "content": [
    {"type": "text", "value": "Gradient Panel", "panel_color": "linear-gradient(180deg, #2c3e50 0%, #4ca1af 100%)"}
  ]
}
```

**Default panel gradient with per-panel override**:

```json
{
  "content": [
    "Uses default gradient",
    {"type": "text", "value": "Custom gradient", "panel_color": "radial-gradient(circle, #ffd89b 0%, #19547b 100%)"}
  ],
  "panel_color": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
}
```

Common gradient patterns:
| Pattern | Example |
|---------|---------|
| Linear diagonal | `"linear-gradient(135deg, #667eea 0%, #764ba2 100%)"` |
| Linear vertical | `"linear-gradient(180deg, #2c3e50 0%, #4ca1af 100%)"` |
| Radial | `"radial-gradient(circle, #ffd89b 0%, #19547b 100%)"` |
| Sunset | `"linear-gradient(to right, #f83600 0%, #f9d423 100%)"` |

### Screen-Level Defaults

Set default colors and fonts at the screen level that apply to all pages. Pages can override these defaults.

**Set screen-level defaults**:

```bash
curl -X PATCH "http://localhost:8000/api/screens/{id}" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{
    "background_color": "linear-gradient(90deg, #2a7b9b 0%, #57c785 71%, #eddd53 100%)",
    "panel_color": "#1a1a2e",
    "font_family": "Georgia, serif",
    "font_color": "#f1c40f"
  }'
```

**Inheritance order** (first match wins):
1. Per-panel values (in content items)
2. Per-page values (in page request)
3. Screen-level defaults (set via PATCH)
4. System defaults (no color/transparent)

This lets you set a consistent theme once and override only when needed.

## Multi-Page Rotation

Screens can display multiple pages that rotate automatically. This is useful for dashboards that need to cycle through different views.

### How Pages Work

- Every screen has a required "default" page
- Additional pages can be added with any name (e.g., "alerts", "weather", "metrics")
- The existing `/message` API updates the "default" page for backward compatibility
- Pages are displayed in order based on `display_order`

### Rotation Settings

Enable rotation, set the interval (in seconds), and configure the default gap:

```bash
curl -X PATCH "http://localhost:8000/api/screens/{id}?rotation_enabled=true&rotation_interval=30&gap=0.5rem" \
  -H "X-API-Key: {api_key}"
```

When rotation is enabled:
- Pages cycle automatically at the specified interval
- Each page can override the interval with its own `duration`
- Expired pages are silently skipped

### Per-Page Duration

Override the rotation interval for a specific page:

```json
{
  "content": ["BREAKING NEWS: ..."],
  "duration": 60
}
```

This page will display for 60 seconds instead of the screen's default interval.

### Ephemeral Pages

Create temporary pages that auto-expire:

```json
{
  "content": ["Flash Sale! 50% off for the next hour"],
  "expires_at": "2024-12-31T23:59:59Z"
}
```

When the expiry time passes, the page is silently removed from rotation.

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
      {"type": "text", "value": "Production: OK", "panel_color": "#27ae60"},
      {"type": "text", "value": "Staging: DEPLOYING", "panel_color": "#f39c12"},
      {"type": "text", "value": "Dev: FAILED", "panel_color": "#c0392b"}
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

### Multi-Page Dashboard with Rotation

Set up a rotating dashboard with multiple pages:

```bash
# Enable rotation (30 second interval)
curl -X PATCH "http://localhost:8000/api/screens/{id}?rotation_enabled=true&rotation_interval=30" \
  -H "X-API-Key: {api_key}"

# Create main dashboard page
curl -X POST http://localhost:8000/api/screens/{id}/pages/default \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{"content": ["# Sales Dashboard", "Revenue: $50,000", "Orders: 150"]}'

# Create metrics page
curl -X POST http://localhost:8000/api/screens/{id}/pages/metrics \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{"content": ["# System Metrics", "CPU: 45%", "Memory: 2.1GB"]}'

# Create weather page (displays for 10 seconds)
curl -X POST http://localhost:8000/api/screens/{id}/pages/weather \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{"content": ["# Weather", "72°F Sunny"], "duration": 10}'
```

### Ephemeral Alert Page

Create a temporary alert that expires in 1 hour:

```bash
curl -X POST http://localhost:8000/api/screens/{id}/pages/alert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {api_key}" \
  -d '{
    "content": ["MAINTENANCE: Server restart in 30 minutes"],
    "background_color": "#e74c3c",
    "expires_at": "2024-12-31T12:00:00Z"
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

## Testing

Run the test suite with pytest:

```bash
source venv/bin/activate
pytest tests/ -v
```

The tests cover:
- Screen creation and management
- Message sending with all content types
- Color, font, and styling options
- Video and image display modes
- Text wrapping options
- Panel gap, border radius, and shadow settings
- Authentication (API key validation)
- Admin page functionality
- Content type auto-detection
- Page management and rotation settings
- Ephemeral pages with expiration

### Manual Testing Scripts

For interactive testing with a running server, use the provided test scripts:

```bash
# Start the server first
uvicorn app.main:app --reload

# In another terminal, run tests
python test_api.py      # Basic API tests
python test_colors.py   # Color feature tests
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
├── tests/
│   └── test_screens.py      # Pytest test suite
├── data/                    # SQLite database (auto-created)
├── requirements.txt
└── README.md
```

## License

MIT
