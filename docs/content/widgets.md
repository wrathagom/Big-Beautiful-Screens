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
| `countup` | Count-up timer from a start date/time |
| `chart` | Line and bar charts for data visualization |
| `weather` | Current conditions and forecasts using Open-Meteo API |
| `stock` | Stock ticker display with adaptive layouts |

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

![Digital Clock Widget - 12h format](../images/screenshots/widget_clock_digital_12h.png)

![Digital Clock Widget - 24h format](../images/screenshots/widget_clock_digital_24h.png)

![Digital Clock Widget - with date](../images/screenshots/widget_clock_with_date.png)

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

![Analog Clock Widget](../images/screenshots/widget_clock_analog.png)

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

![Countdown Widget - Simple Style](../images/screenshots/widget_countdown_simple.png)

![Countdown Widget - Labeled Style](../images/screenshots/widget_countdown_labeled.png)

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

![Countdown Widget - Expired](../images/screenshots/widget_countdown_expired.png)

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

## Count-Up Widget

Display a count-up timer from a start date/time.

### Basic Count-Up

```json
{
  "type": "widget",
  "widget_type": "countup",
  "widget_config": {
    "start": "2025-01-01T00:00:00Z"
  }
}
```

### Count-Up with Label

```json
{
  "type": "widget",
  "widget_type": "countup",
  "widget_config": {
    "start": "2025-01-01T00:00:00Z",
    "label": "Since last update",
    "label_position": "below",
    "style": "labeled"
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `start` | string | (required) | ISO 8601 datetime (e.g., `"2025-01-01T00:00:00Z"`) |
| `label` | string | `null` | Optional descriptive text to display with the timer |
| `label_position` | string | `"below"` | `"above"`, `"below"`, or `"inline"` |
| `style` | string | `"labeled"` | `"labeled"` or `"simple"` |
| `show_days` | boolean | `true` | Show days in count-up |
| `show_hours` | boolean | `true` | Show hours in count-up |
| `show_minutes` | boolean | `true` | Show minutes in count-up |
| `show_seconds` | boolean | `true` | Show seconds in count-up |

### Styles

**Labeled style** (default):
```
2 days  15 hrs  30 min  45 sec
```

**Simple style**:
```
2:15:30:45
```

### Label Positions

**Below** (default): Label appears below the timer
```
02h 30m 45s
Since last update
```

**Above**: Label appears above the timer
```
Since last update
02h 30m 45s
```

**Inline**: Label appears inline with the timer
```
Since last update 02h 30m 45s
```

### Examples

**Uptime Counter:**

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# System Uptime"},
      {
        "type": "widget",
        "widget_type": "countup",
        "widget_config": {
          "start": "2025-06-01T00:00:00Z",
          "label": "Since last restart",
          "label_position": "below",
          "style": "labeled"
        }
      }
    ],
    "background_color": "#1a1a2e",
    "panel_color": "#16213e"
  }'
```

**Simple Timer (hours and minutes only):**

```json
{
  "type": "widget",
  "widget_type": "countup",
  "widget_config": {
    "start": "2025-01-01T00:00:00Z",
    "show_days": false,
    "show_seconds": false,
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

![Chart Widget - Line Chart](../images/screenshots/widget_chart_line.png)

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

![Chart Widget - Bar Chart](../images/screenshots/widget_chart_bar.png)

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

## Weather Widget

Display current weather conditions and forecasts using the free Open-Meteo API. No API key required.

### Current Weather

```json
{
  "type": "widget",
  "widget_type": "weather",
  "widget_config": {
    "location": "New York",
    "units": "imperial"
  }
}
```

### Hourly Forecast

```json
{
  "type": "widget",
  "widget_type": "weather",
  "widget_config": {
    "location": "London",
    "units": "metric",
    "display": "hourly",
    "hours_to_show": 7
  }
}
```

### Daily Forecast

```json
{
  "type": "widget",
  "widget_type": "weather",
  "widget_config": {
    "location": "Tokyo",
    "display": "daily",
    "days_to_show": 7
  }
}
```

### Full Weather Display

```json
{
  "type": "widget",
  "widget_type": "weather",
  "widget_config": {
    "location": "San Francisco",
    "display": "full",
    "hours_to_show": 6,
    "days_to_show": 5
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `location` | string | (required) | City name (e.g., "New York", "London") |
| `units` | string | `"imperial"` | `"imperial"` (F, mph) or `"metric"` (C, km/h) |
| `display` | string | `"current"` | `"current"`, `"hourly"`, `"daily"`, or `"full"` |
| `hours_to_show` | number | `7` | Hours in hourly forecast |
| `days_to_show` | number | `7` | Days in daily forecast |
| `show_humidity` | boolean | `true` | Show humidity percentage |
| `show_wind` | boolean | `true` | Show wind speed |
| `show_precipitation` | boolean | `true` | Show precipitation info |
| `refresh_interval` | number | `1800000` | Refresh interval in ms (default 30 min) |

### Display Modes

**Current** - Large temperature, weather icon, conditions, humidity/wind

**Hourly** - Current conditions + 7-hour horizontal forecast strip

**Daily** - Current conditions + 7-day vertical forecast list

**Full** - Current + hourly + daily in grid layout

### Example

**Weather Dashboard:**

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Weather"},
      {
        "type": "widget",
        "widget_type": "weather",
        "widget_config": {
          "location": "Denver",
          "units": "imperial",
          "display": "daily",
          "days_to_show": 5
        }
      }
    ],
    "background_color": "#1a1a2e",
    "panel_color": "#16213e"
  }'
```

---

## Stock Widget

Display stock tickers with adaptive layouts. This is a static display widget—you provide the stock data, and it handles formatting and display.

### Single Stock

```json
{
  "type": "widget",
  "widget_type": "stock",
  "widget_config": {
    "stocks": [
      { "symbol": "AAPL", "price": 189.72, "change": 3.45, "change_percent": 1.85, "name": "Apple Inc." }
    ]
  }
}
```

![Stock Widget - Single Stock](../images/screenshots/widget_stock_single.png)

### Multiple Stocks (Grid)

```json
{
  "type": "widget",
  "widget_type": "stock",
  "widget_config": {
    "stocks": [
      { "symbol": "AAPL", "price": 189.72, "change": 3.45, "change_percent": 1.85 },
      { "symbol": "GOOGL", "price": 141.25, "change": -2.10, "change_percent": -1.47 },
      { "symbol": "MSFT", "price": 378.91, "change": 5.23, "change_percent": 1.40 },
      { "symbol": "AMZN", "price": 178.50, "change": -1.25, "change_percent": -0.70 }
    ]
  }
}
```

![Stock Widget - Grid Layout](../images/screenshots/widget_stock_grid.png)

### Compact List (5+ Stocks)

```json
{
  "type": "widget",
  "widget_type": "stock",
  "widget_config": {
    "stocks": [
      { "symbol": "AAPL", "price": 189.72, "change": 3.45, "change_percent": 1.85, "name": "Apple Inc." },
      { "symbol": "GOOGL", "price": 141.25, "change": -2.10, "change_percent": -1.47, "name": "Alphabet Inc." },
      { "symbol": "MSFT", "price": 378.91, "change": 5.23, "change_percent": 1.40, "name": "Microsoft Corp." },
      { "symbol": "AMZN", "price": 178.50, "change": -1.25, "change_percent": -0.70, "name": "Amazon.com Inc." },
      { "symbol": "META", "price": 505.65, "change": 12.30, "change_percent": 2.49, "name": "Meta Platforms" }
    ],
    "compact": true
  }
}
```

![Stock Widget - List Layout](../images/screenshots/widget_stock_list.png)

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `stocks` | array | (required) | Array of stock objects |
| `show_change` | boolean | `true` | Show +/- absolute change |
| `show_percent` | boolean | `true` | Show percentage change |
| `gain_color` | string | `"#22c55e"` | Color for positive changes |
| `loss_color` | string | `"#ef4444"` | Color for negative changes |
| `neutral_color` | string | `"#9ca3af"` | Color for no change |
| `compact` | boolean | `false` | Force compact list mode |

### Stock Object Format

```json
{
  "symbol": "AAPL",           // Required: ticker symbol
  "price": 189.72,            // Required: current price
  "change": 3.45,             // Optional: absolute change (+/-)
  "change_percent": 1.85,     // Optional: percent change (+/-)
  "name": "Apple Inc."        // Optional: company name
}
```

### Adaptive Display Modes

The widget automatically chooses a layout based on the number of stocks:

- **1 stock**: Large single-ticker display
- **2-4 stocks**: Grid layout (2x2)
- **5+ stocks**: Compact list view

Use `compact: true` to force compact list mode regardless of count.

### Custom Colors

```json
{
  "type": "widget",
  "widget_type": "stock",
  "widget_config": {
    "stocks": [
      { "symbol": "AAPL", "price": 189.72, "change": 3.45, "change_percent": 1.85 }
    ],
    "gain_color": "#00ff00",
    "loss_color": "#ff0000"
  }
}
```

### Example

**Stock Ticker Board:**

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Market Watch"},
      {
        "type": "widget",
        "widget_type": "stock",
        "widget_config": {
          "stocks": [
            { "symbol": "^DJI", "price": 38989.50, "change": 125.30, "change_percent": 0.32, "name": "Dow Jones" },
            { "symbol": "^GSPC", "price": 5123.41, "change": 18.75, "change_percent": 0.37, "name": "S&P 500" },
            { "symbol": "^IXIC", "price": 16091.92, "change": -42.10, "change_percent": -0.26, "name": "NASDAQ" }
          ]
        }
      }
    ],
    "background_color": "#0a0a0a",
    "panel_color": "#1a1a1a",
    "font_color": "#ffffff"
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
