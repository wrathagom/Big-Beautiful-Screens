"""MCP Resource definitions for Big Beautiful Screens.

Resources provide read-only documentation that AI clients can use to
understand how to work with screens, content items, widgets, and styling.
"""

from mcp.types import Resource

# ---------------------------------------------------------------------------
# Resource content
# ---------------------------------------------------------------------------

_GUIDE = """\
# Big Beautiful Screens — Quick Start Guide

Big Beautiful Screens lets you create real-time display screens for dashboards,
status boards, and signage.  This MCP server exposes tools to create and manage
screens programmatically.

## Typical Workflow

1. **Create a screen** → `create_screen` (returns screen_id + api_key)
2. **Style the screen** → `update_screen` (set colors, fonts, theme, layout)
3. **Send content** → `send_message` (push content items to the default page)
4. **Add pages** → `create_page` (for multi-page rotation / carousel)

## Content Items

The `content` array in `send_message` and `create_page` accepts a mix of
strings and structured objects.  Strings are auto-detected (plain text,
markdown, image URLs, video URLs).  Use objects for explicit control:

### Text & Markdown
```json
{"type": "text", "value": "Hello, World!"}
{"type": "markdown", "value": "# Heading\\n\\n**Bold** text"}
```

### Images & Video
```json
{"type": "image", "url": "https://example.com/photo.jpg", "image_mode": "cover"}
{"type": "video", "url": "https://example.com/clip.mp4", "autoplay": true, "loop": true}
```

### Widgets
```json
{"type": "widget", "widget_type": "clock", "widget_config": {"style": "digital", "format": "12h", "timezone": "America/Los_Angeles"}}
{"type": "widget", "widget_type": "countdown", "widget_config": {"target": "2026-12-25T00:00:00", "expired_text": "Merry Christmas!"}}
{"type": "widget", "widget_type": "chart", "widget_config": {"chart_type": "bar", "labels": ["A","B","C"], "datasets": [{"label": "Sales", "data": [10,20,30]}]}}
```

### Per-Item Styling
Any content item can override panel styling:
```json
{
  "type": "text",
  "value": "Styled panel",
  "panel_color": "rgba(255,0,0,0.3)",
  "panel_shadow": "none",
  "font_color": "#ff0000",
  "font_family": "monospace"
}
```

### Grid Positioning
Use `grid_column` and `grid_row` for explicit placement:
```json
{"type": "text", "value": "Full width header", "grid_column": "1 / -1"}
{"type": "text", "value": "Spans 2 cols", "grid_column": "span 2"}
```

## Screen Styling

`update_screen` accepts CSS values for styling:
- `background_color`: CSS color or gradient (e.g. `"linear-gradient(135deg, #1a1a2e, #16213e)"`)
- `panel_color`: Default panel background
- `font_color`: Default text color
- `font_family`: CSS font-family
- `gap`: Space between panels (e.g. `"1rem"`)
- `border_radius`: Panel corner rounding (e.g. `"1rem"`, `"0"` for square)
- `panel_shadow`: CSS box-shadow (e.g. `"0 4px 12px rgba(0,0,0,0.3)"`, `"none"`)
- `theme`: Named theme (e.g. `"catppuccin-mocha"`, `"nord"`, `"dracula"`)

## Layouts

Pass a layout preset name or config object to `send_message` / `create_page`:
- `"vertical"` — single column
- `"horizontal"` — single row
- `"grid-2x2"`, `"grid-3x2"`, `"grid-3x3"` — grid layouts
- `"dashboard-header"` — full-width header + 3-column grid below
- `"dashboard-footer"` — 3-column grid + full-width footer
- `"featured-top"` — large header spanning full width, smaller panels below

Or use an object for custom layout:
```json
{"columns": 3, "rows": "auto 1fr 1fr", "header_rows": 1}
```

Use `list_layouts` tool to see all available presets.
"""

_WIDGETS = """\
# Widgets

Widgets are interactive content items. Set `type` to `"widget"` and specify
`widget_type` and `widget_config`.

## Clock

Displays a live clock.

```json
{
  "type": "widget",
  "widget_type": "clock",
  "widget_config": {
    "style": "digital",
    "format": "12h",
    "timezone": "America/New_York"
  }
}
```

**widget_config options:**
| Key        | Values                          | Default   |
|------------|---------------------------------|-----------|
| `style`    | `"digital"`, `"analog"`         | `"digital"` |
| `format`   | `"12h"`, `"24h"`                | `"12h"`   |
| `timezone` | IANA timezone or `"local"`      | `"local"` |

**Common timezones:** `America/New_York`, `America/Chicago`, `America/Denver`,
`America/Los_Angeles`, `Europe/London`, `Europe/Paris`, `Asia/Tokyo`, `UTC`

## Countdown

Counts down to a target date/time.

```json
{
  "type": "widget",
  "widget_type": "countdown",
  "widget_config": {
    "target": "2026-12-25T00:00:00",
    "expired_text": "Merry Christmas!"
  }
}
```

**widget_config options:**
| Key            | Description                              |
|----------------|------------------------------------------|
| `target`       | ISO 8601 datetime to count down to       |
| `expired_text` | Text shown when countdown reaches zero   |

## Chart

Displays a Chart.js chart.

```json
{
  "type": "widget",
  "widget_type": "chart",
  "widget_config": {
    "chart_type": "bar",
    "labels": ["Jan", "Feb", "Mar"],
    "datasets": [
      {"label": "Revenue", "data": [100, 150, 200], "backgroundColor": "#4CAF50"}
    ]
  }
}
```

**widget_config options:**
| Key        | Description                                    |
|------------|------------------------------------------------|
| `chart_type` | Chart type: `"bar"`, `"line"`, `"pie"`, `"doughnut"`, `"radar"`, `"polarArea"`, `"bubble"`, `"scatter"` (default: `"bar"`) |
| `labels`   | Array of x-axis labels                         |
| `datasets` | Array of dataset objects with `label`, `data`, `backgroundColor`, etc. |
| `index_axis` | `"x"` (default) or `"y"` for horizontal bars |
| `show_legend` | Boolean (default: true)                     |
| `show_grid` | Boolean (default: true)                       |
| `fill`     | Boolean — fill area under line (default: false) |
| `tension`  | Number — line curve, 0 = straight (default: 0.1) |

**Notes on chart types:**
- **pie / doughnut / polarArea**: Segments are auto-colored from a built-in palette. No x/y scales.
- **radar**: Radial layout; supports `fill` and `tension` like line charts.
- **scatter**: Requires data as `[{"x": N, "y": N}]` coordinate pairs.
- **bubble**: Like scatter but with radius: `[{"x": N, "y": N, "r": N}]`.
"""

_EXAMPLES = """\
# Examples

## Simple Status Board

```
create_screen(name="Status Board")
update_screen(screen_id="...", api_key="...", background_color="#1a1a2e", font_color="#e0e0e0", panel_color="rgba(255,255,255,0.05)", border_radius="0.75rem")
send_message(screen_id="...", api_key="...", layout="vertical", content=[
    {"type": "markdown", "value": "# System Status"},
    {"type": "markdown", "value": "**API Server:** ✅ Healthy\\n**Database:** ✅ Connected\\n**Queue:** ⚠️ 142 pending"},
    {"type": "widget", "widget_type": "clock", "widget_config": {"style": "digital", "format": "24h", "timezone": "UTC"}}
])
```

## Digital Clock Display

```
create_screen(name="Office Clock")
update_screen(screen_id="...", api_key="...", background_color="#000000", font_color="#ffffff", panel_color="transparent", panel_shadow="none", border_radius="0")
send_message(screen_id="...", api_key="...", content=[
    {"type": "widget", "widget_type": "clock", "widget_config": {"style": "digital", "format": "12h", "timezone": "America/Los_Angeles"}}
])
```

## Event Countdown

```
create_screen(name="Launch Countdown")
update_screen(screen_id="...", api_key="...", background_color="linear-gradient(135deg, #0f0c29, #302b63, #24243e)", font_color="#f0f0f0")
send_message(screen_id="...", api_key="...", layout="vertical", content=[
    {"type": "markdown", "value": "# 🚀 Product Launch", "panel_color": "transparent", "panel_shadow": "none"},
    {"type": "widget", "widget_type": "countdown", "widget_config": {"target": "2026-03-15T09:00:00", "expired_text": "🎉 We're Live!"}},
    {"type": "markdown", "value": "*Get ready...*", "panel_color": "transparent", "panel_shadow": "none"}
])
```

## Dashboard with Charts

```
create_screen(name="Sales Dashboard")
update_screen(screen_id="...", api_key="...", background_color="#1e1e2e", font_color="#cdd6f4", panel_color="rgba(255,255,255,0.05)")
send_message(screen_id="...", api_key="...", layout="dashboard-header", content=[
    {"type": "markdown", "value": "# 📊 Sales Dashboard"},
    {"type": "widget", "widget_type": "chart", "widget_config": {"chart_type": "bar", "labels": ["Q1","Q2","Q3","Q4"], "datasets": [{"label": "Revenue ($k)", "data": [120,180,240,310], "backgroundColor": "#89b4fa"}]}},
    {"type": "widget", "widget_type": "chart", "widget_config": {"chart_type": "line", "labels": ["Jan","Feb","Mar","Apr","May","Jun"], "datasets": [{"label": "Users", "data": [120,190,300,500,800,1200], "color": "#a6e3a1"}]}},
    {"type": "widget", "widget_type": "clock", "widget_config": {"style": "digital", "format": "24h"}}
])
```
"""

# ---------------------------------------------------------------------------
# Resource registry
# ---------------------------------------------------------------------------

_RESOURCE_MAP: dict[str, str] = {
    "bbs://guide": _GUIDE,
    "bbs://widgets": _WIDGETS,
    "bbs://examples": _EXAMPLES,
}

RESOURCES: list[Resource] = [
    Resource(
        uri="bbs://guide",
        name="Quick Start Guide",
        description="How to create and style screens, content item types, layouts, and styling options",
        mimeType="text/markdown",
    ),
    Resource(
        uri="bbs://widgets",
        name="Widget Reference",
        description="Clock, countdown, and chart widget types with configuration options",
        mimeType="text/markdown",
    ),
    Resource(
        uri="bbs://examples",
        name="Examples",
        description="Complete example screen configurations (status board, clock, countdown, dashboard)",
        mimeType="text/markdown",
    ),
]


def get_resource_content(uri: str) -> str:
    """Return the content for a given resource URI."""
    content = _RESOURCE_MAP.get(uri)
    if content is None:
        raise ValueError(f"Unknown resource: {uri}")
    return content
