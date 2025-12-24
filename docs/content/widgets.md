# Widgets

Widgets are interactive, live-updating elements that add dynamic functionality to your screens.

## Overview

Unlike static content types, widgets are active—they update themselves without requiring API calls. For example, a clock widget updates every second automatically.

```json
{
  "type": "widget",
  "widget_type": "clock",
  "widget_config": {
    "style": "digital",
    "format": "12h"
  }
}
```

## Available Widgets

| Widget | Description |
|--------|-------------|
| `clock` | Digital or analog clock display |
| `countdown` | Countdown timer (coming soon) |
| `chart` | Data visualization (coming soon) |

---

## Clock Widget

Display a live clock in digital or analog format.

### Digital Clock

```json
{
  "type": "widget",
  "widget_type": "clock",
  "widget_config": {
    "style": "digital",
    "format": "12h",
    "show_seconds": true,
    "show_date": true
  }
}
```

### Analog Clock

```json
{
  "type": "widget",
  "widget_type": "clock",
  "widget_config": {
    "style": "analog",
    "show_numbers": true
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `style` | string | `"digital"` | `"digital"` or `"analog"` |
| `timezone` | string | `"local"` | IANA timezone (e.g., `"America/New_York"`, `"UTC"`) |
| `format` | string | `"12h"` | `"12h"` or `"24h"` (digital only) |
| `show_seconds` | boolean | `true` | Show seconds (digital only) |
| `show_date` | boolean | `false` | Show date below time (digital only) |
| `show_numbers` | boolean | `false` | Show hour numbers (analog only) |

### Timezone Examples

```json
// Local time (browser timezone)
{"style": "digital", "timezone": "local"}

// UTC
{"style": "digital", "timezone": "UTC"}

// Specific timezone
{"style": "digital", "timezone": "America/New_York"}
{"style": "digital", "timezone": "Europe/London"}
{"style": "digital", "timezone": "Asia/Tokyo"}
```

### Multiple Clocks

Display clocks for different timezones:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {
        "type": "widget",
        "widget_type": "clock",
        "widget_config": {"style": "digital", "timezone": "America/New_York", "show_date": true}
      },
      {
        "type": "widget",
        "widget_type": "clock",
        "widget_config": {"style": "digital", "timezone": "Europe/London", "show_date": true}
      },
      {
        "type": "widget",
        "widget_type": "clock",
        "widget_config": {"style": "digital", "timezone": "Asia/Tokyo", "show_date": true}
      }
    ]
  }'
```

---

## Coming Soon

### Countdown Widget

```json
{
  "type": "widget",
  "widget_type": "countdown",
  "widget_config": {
    "target": "2025-12-31T00:00:00Z",
    "expired_text": "Happy New Year!",
    "show_days": true,
    "show_hours": true,
    "show_minutes": true,
    "show_seconds": true
  }
}
```

### Chart Widget

```json
{
  "type": "widget",
  "widget_type": "chart",
  "widget_config": {
    "chart_type": "line",
    "data": {
      "labels": ["Mon", "Tue", "Wed", "Thu", "Fri"],
      "values": [10, 25, 15, 30, 22]
    }
  }
}
```

---

## Widget with Panel Styling

Widgets can have per-panel styling like any other content type:

```json
{
  "type": "widget",
  "widget_type": "clock",
  "widget_config": {"style": "analog"},
  "panel_color": "#1a1a2e",
  "font_color": "#ffffff"
}
```

---

## Dashboard Example

Create a dashboard with mixed widgets and content:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Office Dashboard"},
      {"type": "widget", "widget_type": "clock", "widget_config": {"style": "digital", "format": "12h", "show_date": true}},
      {"type": "widget", "widget_type": "clock", "widget_config": {"style": "analog", "show_numbers": true}},
      {"type": "text", "value": "All Systems Operational", "panel_color": "#27ae60"}
    ],
    "background_color": "#1e1e2e",
    "panel_color": "#313244",
    "font_color": "#cdd6f4"
  }'
```

---

## Technical Details

### Lifecycle

Widgets are created when a page renders and destroyed when the page changes. This ensures:

- No memory leaks from abandoned timers
- Clean transitions between pages
- Proper cleanup on page rotation

### Performance

Widgets update independently without server calls:

- Clock widgets update every second client-side
- No additional API traffic for live updates
- Scales to unlimited viewers
