# Big Beautiful Screens - Dashboard Creation Guide

This skill helps users create and configure digital signage screens using the Big Beautiful Screens API.

## API Endpoint

Send content to a screen via POST request:

```
POST /api/v1/screens/{screen_id}/message
Header: X-API-Key: {api_key}
Content-Type: application/json
```

## Request Structure

```json
{
  "content": [...],           // Array of content items (required)
  "layout": "preset-name",    // Layout preset or custom config
  "background_color": "#hex", // Screen background
  "panel_color": "#hex",      // Default panel background
  "font_family": "...",       // CSS font-family
  "font_color": "#hex",       // Default text color
  "gap": "1rem",              // Gap between panels
  "border_radius": "1rem",    // Panel corner rounding
  "panel_shadow": "..."       // CSS box-shadow
}
```

---

## Content Types

### Text
```json
{"type": "text", "value": "Hello World"}
```
Options:
- `wrap`: boolean (default: true) - Enable text wrapping

### Markdown
```json
{"type": "markdown", "value": "# Heading\n\n**Bold** and *italic*"}
```
Supports standard markdown: headings, bold, italic, lists, code blocks.

### Image
```json
{"type": "image", "url": "https://example.com/image.png"}
```
Options:
- `image_mode`: "contain" | "cover" | "cover-width" | "cover-height" (default: "contain")

### Video
```json
{"type": "video", "url": "https://example.com/video.mp4"}
```
Options:
- `autoplay`: boolean (default: true)
- `loop`: boolean (default: true)
- `muted`: boolean (default: true)
- `image_mode`: same as image

### Widget
```json
{"type": "widget", "widget_type": "clock", "widget_config": {...}}
```
See Widget Reference below.

---

## Per-Panel Styling

Any content item can have per-panel overrides:

```json
{
  "type": "text",
  "value": "Styled Panel",
  "panel_color": "#ff6b6b",
  "panel_shadow": "0 4px 12px rgba(0,0,0,0.3)",
  "font_family": "'Roboto Mono', monospace",
  "font_color": "#ffffff"
}
```

---

## Grid Positioning

For custom layouts, use CSS grid positioning:

```json
{
  "type": "widget",
  "widget_type": "chart",
  "grid_column": "span 2",   // Span 2 columns
  "grid_row": "span 2",      // Span 2 rows
  "widget_config": {...}
}
```

Values:
- `"span N"` - Span N cells
- `"1 / -1"` - Full width/height
- `"1 / 3"` - From line 1 to line 3

---

## Layout Presets

### Vertical (Single Column)
- `"vertical"` - Auto rows
- `"vertical-6"` - 6 rows
- `"vertical-8"` - 8 rows
- `"vertical-10"` - 10 rows
- `"vertical-12"` - 12 rows

### Horizontal (Single Row)
- `"horizontal"` - Auto columns
- `"horizontal-4"` - 4 columns
- `"horizontal-6"` - 6 columns

### Grid Layouts
- `"grid-2x2"` - 2 columns x 2 rows
- `"grid-3x2"` - 3 columns x 2 rows
- `"grid-2x3"` - 2 columns x 3 rows
- `"grid-3x3"` - 3 columns x 3 rows
- `"grid-4x3"` - 4 columns x 3 rows
- `"grid-4x4"` - 4 columns x 4 rows

### Dashboard Layouts (with full-width header/footer)
- `"dashboard-header"` - 3 columns, header spans full width
- `"dashboard-footer"` - 3 columns, footer spans full width
- `"dashboard-both"` - 3 columns, header and footer span full width

### Specialty Layouts
- `"menu-board"` - 2 columns with header row
- `"menu-3col"` - 3 columns with header row
- `"schedule"` - Single column with header
- `"featured-top"` - Large top row, smaller bottom
- `"sidebar-left"` - Narrow left, wide right
- `"sidebar-right"` - Wide left, narrow right

### Custom Layout
```json
{
  "layout": {
    "columns": 3,                    // Number or CSS grid-template-columns
    "rows": 2,                       // Number or CSS grid-template-rows
    "header_rows": 1,                // Rows that span full width at top
    "footer_rows": 1                 // Rows that span full width at bottom
  }
}
```

Advanced CSS grid values:
```json
{
  "layout": {
    "columns": "1fr 2fr 1fr",        // Custom column widths
    "rows": "auto 1fr 1fr auto"      // Custom row heights
  }
}
```

---

## Widget Reference

### Clock Widget
```json
{
  "type": "widget",
  "widget_type": "clock",
  "widget_config": {
    "style": "digital",        // "digital" | "analog"
    "timezone": "local",       // IANA timezone or "local"
    "format": "12h",           // "12h" | "24h"
    "show_seconds": true,
    "show_date": false,
    "show_numbers": true       // For analog style
  }
}
```

### Countdown Widget
```json
{
  "type": "widget",
  "widget_type": "countdown",
  "widget_config": {
    "target": "2025-12-31T23:59:59Z",  // ISO 8601 datetime (required)
    "expired_text": "Happy New Year!",
    "show_days": true,
    "show_hours": true,
    "show_minutes": true,
    "show_seconds": true,
    "style": "labeled"         // "simple" | "labeled"
  }
}
```

### Count-Up Widget
```json
{
  "type": "widget",
  "widget_type": "countup",
  "widget_config": {
    "start": "2025-01-01T00:00:00Z",  // ISO 8601 datetime (required)
    "label": "Since last update",
    "label_position": "below",         // "above" | "below" | "inline"
    "show_days": true,
    "show_hours": true,
    "show_minutes": true,
    "show_seconds": true,
    "style": "labeled"                 // "simple" | "labeled"
  }
}
```

### Chart Widget
```json
{
  "type": "widget",
  "widget_type": "chart",
  "widget_config": {
    "chart_type": "bar",       // "bar" | "line" | "pie" | "doughnut" | "radar" | "polarArea" | "bubble" | "scatter"
    "labels": ["A", "B", "C"],
    "datasets": [{
      "data": [10, 20, 30],
      "backgroundColor": ["#ff0000", "#00ff00", "#0000ff"],  // Per-bar colors
      "borderColor": "#ffffff",
      "label": "Series 1"
    }],
    "index_axis": "x",         // "x" (vertical) | "y" (horizontal bars)
    "show_legend": true,
    "legend_position": "top",  // "top" | "bottom" | "left" | "right"
    "show_grid": true,
    "x_min": null,
    "x_max": 100,
    "y_min": 0,
    "y_max": null,
    "x_axis_label": "Category",
    "y_axis_label": "Value",
    "fill": false,             // Fill area under line
    "tension": 0.1,            // Line curve (0 = straight)
    "point_radius": 3
  }
}
```

Simple format (single series):
```json
{
  "widget_config": {
    "chart_type": "bar",
    "labels": ["A", "B", "C"],
    "values": [10, 20, 30],    // Use values instead of datasets
    "color": "#3498db",
    "label": "My Data"
  }
}
```

Pie/Doughnut (auto-colored segments):
```json
{
  "widget_config": {
    "chart_type": "pie",
    "labels": ["Desktop", "Mobile", "Tablet"],
    "values": [60, 30, 10]
  }
}
```

Scatter (x/y coordinate pairs):
```json
{
  "widget_config": {
    "chart_type": "scatter",
    "datasets": [{"label": "Points", "data": [{"x": 10, "y": 20}, {"x": 15, "y": 10}]}]
  }
}
```

### Weather Widget
```json
{
  "type": "widget",
  "widget_type": "weather",
  "widget_config": {
    "location": "New York",    // City name (required)
    "units": "imperial",       // "imperial" | "metric"
    "display": "current",      // "current" | "hourly" | "daily" | "full"
    "hours_to_show": 7,
    "days_to_show": 7,
    "show_humidity": true,
    "show_wind": true,
    "show_precipitation": true,
    "refresh_interval": 1800000  // 30 minutes in ms
  }
}
```

### Stock Widget
```json
{
  "type": "widget",
  "widget_type": "stock",
  "widget_config": {
    "stocks": [
      {"symbol": "AAPL", "price": 150.25, "change": 2.50, "change_percent": 1.69},
      {"symbol": "GOOGL", "price": 140.00, "change": -1.25, "change_percent": -0.88}
    ],
    "show_change": true,
    "show_percent": true,
    "gain_color": "#22c55e",
    "loss_color": "#ef4444",
    "neutral_color": "#9ca3af",
    "compact": false
  }
}
```

### RSS Widget
```json
{
  "type": "widget",
  "widget_type": "rss",
  "widget_config": {
    "url": "https://example.com/feed.xml",  // RSS feed URL (required)
    "max_items": 5,
    "show_description": false,
    "show_date": true,
    "show_image": false,
    "title_override": "Latest News",
    "refresh_interval": 300000,  // 5 minutes in ms
    "date_format": "relative"    // "relative" | "short" | "long"
  }
}
```

---

## Color Tips

### Catppuccin Mocha (Popular Dark Theme)
- Background: `#1e1e2e`
- Panel: `#313244`
- Text: `#cdd6f4`
- Accent colors: Mauve `#cba6f7`, Peach `#fab387`, Green `#a6e3a1`, Blue `#89b4fa`

### Gradients
```json
"background_color": "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)"
```

---

## Complete Example

Dashboard with chart spanning 2x2, and two info panels:

```json
{
  "content": [
    {
      "type": "widget",
      "widget_type": "chart",
      "grid_column": "span 2",
      "grid_row": "span 2",
      "widget_config": {
        "chart_type": "bar",
        "index_axis": "y",
        "labels": ["Claude", "Codex"],
        "datasets": [{
          "data": [12, 47],
          "backgroundColor": ["#cba6f7", "#fab387"]
        }],
        "show_legend": false,
        "x_max": 100
      }
    },
    {
      "type": "text",
      "value": "Claude resets in\n5h 24m",
      "font_color": "#cba6f7"
    },
    {
      "type": "text",
      "value": "Codex resets in\n4h 59m",
      "font_color": "#fab387"
    }
  ],
  "layout": {"columns": 3, "rows": 2},
  "background_color": "#1e1e2e",
  "panel_color": "#313244",
  "font_color": "#cdd6f4",
  "gap": "16",
  "border_radius": "12"
}
```

---

## curl Example

```bash
curl -X POST "https://app.bigbeautifulscreens.com/api/v1/screens/{screen_id}/message" \
  -H "X-API-Key: {api_key}" \
  -H "Content-Type: application/json" \
  -d '{"content": [{"type": "text", "value": "Hello World"}]}'
```
