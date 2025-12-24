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
| `countdown` | Countdown timer to a target date/time |
| `chart` | Line and bar charts for data visualization |

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

## Countdown Widget

Display a countdown timer to a target date/time.

### Basic Countdown

```json
{
  "type": "widget",
  "widget_type": "countdown",
  "widget_config": {
    "target": "2025-12-31T00:00:00Z"
  }
}
```

### Countdown with Custom Expired Text

```json
{
  "type": "widget",
  "widget_type": "countdown",
  "widget_config": {
    "target": "2025-12-31T00:00:00Z",
    "expired_text": "Happy New Year!",
    "style": "labeled"
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `target` | string | (required) | ISO 8601 datetime (e.g., `"2025-12-31T00:00:00Z"`) |
| `expired_text` | string | `"Expired"` | Text shown when countdown reaches zero |
| `style` | string | `"labeled"` | `"labeled"` or `"simple"` |
| `show_days` | boolean | `true` | Show days in countdown |
| `show_hours` | boolean | `true` | Show hours in countdown |
| `show_minutes` | boolean | `true` | Show minutes in countdown |
| `show_seconds` | boolean | `true` | Show seconds in countdown |

### Styles

**Labeled style** (default):
```
2 days  15 hrs  30 min  45 sec
```

**Simple style**:
```
2:15:30:45
```

### Examples

**New Year Countdown:**

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# New Year Countdown"},
      {
        "type": "widget",
        "widget_type": "countdown",
        "widget_config": {
          "target": "2026-01-01T00:00:00Z",
          "expired_text": "Happy New Year!",
          "style": "labeled"
        }
      }
    ],
    "background_color": "#1a1a2e",
    "panel_color": "#16213e"
  }'
```

**Event Timer (minutes and seconds only):**

```json
{
  "type": "widget",
  "widget_type": "countdown",
  "widget_config": {
    "target": "2025-12-25T10:00:00Z",
    "expired_text": "Event Started!",
    "show_days": false,
    "show_hours": false,
    "style": "simple"
  }
}
```

---

## Chart Widget

Display line or bar charts using Chart.js.

### Simple Line Chart

```json
{
  "type": "widget",
  "widget_type": "chart",
  "widget_config": {
    "chart_type": "line",
    "labels": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "values": [10, 25, 15, 30, 22],
    "label": "Sales"
  }
}
```

### Bar Chart

```json
{
  "type": "widget",
  "widget_type": "chart",
  "widget_config": {
    "chart_type": "bar",
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "values": [120, 190, 300, 250],
    "color": "#3498db"
  }
}
```

### Multi-Series Chart

```json
{
  "type": "widget",
  "widget_type": "chart",
  "widget_config": {
    "chart_type": "bar",
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "datasets": [
      {"label": "2023", "values": [120, 190, 300, 250], "color": "#3498db"},
      {"label": "2024", "values": [150, 220, 280, 310], "color": "#2ecc71"}
    ],
    "x_axis_label": "Quarter",
    "y_axis_label": "Revenue ($K)"
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `chart_type` | string | `"bar"` | `"line"` or `"bar"` |
| `labels` | array | `[]` | X-axis labels |
| `values` | array | `null` | Data values (simple single-series format) |
| `datasets` | array | `[]` | Multiple data series (advanced format) |
| `label` | string | `"Data"` | Label for single-series data |
| `color` | string | auto | Color for single-series (hex code) |
| `x_axis_label` | string | `null` | X-axis title |
| `y_axis_label` | string | `null` | Y-axis title |
| `show_legend` | boolean | `true` | Show chart legend |
| `legend_position` | string | `"top"` | `"top"`, `"bottom"`, `"left"`, `"right"` |
| `show_grid` | boolean | `true` | Show grid lines |
| `fill` | boolean | `false` | Fill area under line (line charts) |
| `tension` | number | `0.1` | Line curve (0 = straight, 0.4 = smooth) |
| `y_min` | number | `null` | Y-axis minimum value |
| `y_max` | number | `null` | Y-axis maximum value |

### Data Formats

**Simple format** (single series):
```json
{
  "labels": ["A", "B", "C"],
  "values": [10, 20, 15],
  "label": "My Data",
  "color": "#3498db"
}
```

**Advanced format** (multiple series):
```json
{
  "labels": ["A", "B", "C"],
  "datasets": [
    {"label": "Series 1", "values": [10, 20, 15], "color": "#3498db"},
    {"label": "Series 2", "values": [15, 25, 20], "color": "#e74c3c"}
  ]
}
```

### Examples

**Sales Dashboard Line Chart:**

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Sales Dashboard"},
      {
        "type": "widget",
        "widget_type": "chart",
        "widget_config": {
          "chart_type": "line",
          "labels": ["Jan", "Feb", "Mar", "Apr", "May"],
          "values": [65, 59, 80, 81, 56],
          "label": "Monthly Sales",
          "fill": true,
          "tension": 0.4
        }
      }
    ]
  }'
```

**Quarterly Comparison Bar Chart:**

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {
        "type": "widget",
        "widget_type": "chart",
        "widget_config": {
          "chart_type": "bar",
          "labels": ["Q1", "Q2", "Q3", "Q4"],
          "datasets": [
            {"label": "2023", "values": [120, 190, 300, 250], "color": "#3498db"},
            {"label": "2024", "values": [150, 220, 280, 310], "color": "#2ecc71"}
          ],
          "x_axis_label": "Quarter",
          "y_axis_label": "Revenue ($K)",
          "show_legend": true
        }
      }
    ],
    "background_color": "#1e1e2e",
    "panel_color": "#313244",
    "font_color": "#cdd6f4"
  }'
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
