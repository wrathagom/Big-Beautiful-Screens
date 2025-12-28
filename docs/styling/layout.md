# Layout & Spacing

Control the panel arrangement, spacing, corners, and shadows of your screen.

## Layout Presets

Use named presets for common arrangements, or create custom grid layouts.

### List Available Presets

```bash
curl http://localhost:8000/api/v1/layouts
```

### Preset Categories

#### Auto (Backward Compatible)

The default behavior—content arranges automatically based on item count:

| Items | Layout |
|-------|--------|
| 1 | Full screen |
| 2 | Side by side (50/50) |
| 3 | Top half + bottom split |
| 4 | 2x2 grid |
| 5-6 | 3-column grid |

No layout field needed—just send your content.

#### Vertical Stacking (Single Column)

Perfect for menus, schedules, or lists.

| Preset | Description |
|--------|-------------|
| `vertical` | Single column, rows auto-expand to fit content |
| `vertical-6` | Single column, fixed 6 rows |
| `vertical-8` | Single column, fixed 8 rows |
| `vertical-10` | Single column, fixed 10 rows |
| `vertical-12` | Single column, fixed 12 rows |

```json
{
  "content": ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5", "Item 6"],
  "layout": "vertical"
}
```

#### Horizontal (Single Row)

| Preset | Description |
|--------|-------------|
| `horizontal` | Single row, columns auto-expand |
| `horizontal-4` | Single row, 4 fixed columns |
| `horizontal-6` | Single row, 6 fixed columns |

#### Standard Grids

| Preset | Description |
|--------|-------------|
| `grid-2x2` | 2 columns × 2 rows (4 panels) |
| `grid-3x2` | 3 columns × 2 rows (6 panels) |
| `grid-2x3` | 2 columns × 3 rows (6 panels) |
| `grid-3x3` | 3 columns × 3 rows (9 panels) |
| `grid-4x3` | 4 columns × 3 rows (12 panels) |
| `grid-4x4` | 4 columns × 4 rows (16 panels) |

```json
{
  "content": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],
  "layout": "grid-3x3"
}
```

#### Dashboard Layouts

Layouts with full-width header and/or footer rows:

| Preset | Description |
|--------|-------------|
| `dashboard-header` | Full-width header, 3-column grid below |
| `dashboard-footer` | 3-column grid with full-width footer |
| `dashboard-both` | Header and footer with grid in between |

```json
{
  "content": [
    {"type": "markdown", "value": "# Dashboard"},
    "Metric 1",
    "Metric 2",
    "Metric 3"
  ],
  "layout": "dashboard-header"
}
```

#### Menu/Schedule Layouts

| Preset | Description |
|--------|-------------|
| `menu-board` | Title header + 2-column menu items |
| `menu-3col` | Title header + 3-column menu items |
| `schedule` | Title header + stacked rows |

```json
{
  "content": [
    "# Today's Menu",
    "Burger - $8", "Fries - $4",
    "Pizza - $12", "Salad - $6"
  ],
  "layout": "menu-board"
}
```

#### Sidebar Layouts

| Preset | Description |
|--------|-------------|
| `sidebar-left` | 25% left sidebar + 75% main content |
| `sidebar-right` | 75% main content + 25% right sidebar |
| `featured-top` | Large top panel (2fr), smaller panels below (1fr) |

## Custom Layouts

For complete control, specify columns and rows directly:

### Using Column/Row Counts

```json
{
  "content": ["A", "B", "C", "D", "E", "F"],
  "layout": {
    "columns": 3,
    "rows": 2
  }
}
```

### Using CSS Grid Values

Use CSS grid-template syntax for flexible sizing:

```json
{
  "content": ["Sidebar", "Main Content"],
  "layout": {
    "columns": "1fr 3fr"
  }
}
```

### CSS Grid Unit Reference

| Unit | Meaning | Example |
|------|---------|---------|
| `1fr` | 1 fraction of available space | `1fr 1fr` = two 50% columns |
| `2fr` | 2 fractions (twice as wide) | `1fr 2fr` = 33% + 67% |
| `auto` | Size to content | `auto 1fr` = content-sized + fill |
| `200px` | Fixed pixels | `200px 1fr` = fixed + flexible |

### Header/Footer Rows

Make the first or last items span full width:

```json
{
  "content": [
    "# Title",
    "Panel 1", "Panel 2", "Panel 3",
    "Footer"
  ],
  "layout": {
    "columns": 3,
    "rows": "auto 1fr 1fr auto",
    "header_rows": 1,
    "footer_rows": 1
  }
}
```

## Per-Panel Grid Positioning

Position individual panels explicitly using CSS grid placement:

```json
{
  "content": [
    {"type": "text", "value": "Title", "grid_column": "1 / -1"},
    {"type": "text", "value": "Main", "grid_column": "span 2", "grid_row": "span 2"},
    {"type": "text", "value": "Side 1"},
    {"type": "text", "value": "Side 2"}
  ],
  "layout": {"columns": 3, "rows": "auto 1fr 1fr"}
}
```

### Grid Positioning Reference

| Property | Example Values | Description |
|----------|---------------|-------------|
| `grid_column` | `"span 2"` | Span 2 columns |
| `grid_column` | `"1 / -1"` | Span all columns (full width) |
| `grid_column` | `"1 / 3"` | From column 1 to 3 |
| `grid_row` | `"span 2"` | Span 2 rows |
| `grid_row` | `"2 / 4"` | From row 2 to 4 |

## Screen Default Layout

Set a default layout for all pages on a screen:

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"default_layout": "vertical-12"}'
```

Or with a custom configuration:

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"default_layout": {"columns": 2, "rows": 6}}'
```

Individual pages can still override with their own layout.

---

## Panel Gap

Control the space between panels.

### Screen Default

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"gap": "1rem"}'
```

### Per-Page Override

```json
{
  "content": ["Panel 1", "Panel 2"],
  "gap": "0"
}
```

### Common Values

| Value | Description |
|-------|-------------|
| `"1rem"` | Default spacing (comfortable) |
| `"0.5rem"` | Compact layout |
| `"0"` | Edge-to-edge (true tiling) |
| `"2rem"` | Extra spacious |

## Border Radius

Control the corner rounding of panels.

### Screen Default

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"border_radius": "0.5rem"}'
```

### Per-Page Override

```json
{
  "content": ["Sharp corners"],
  "border_radius": "0"
}
```

### Common Values

| Value | Description |
|-------|-------------|
| `"1rem"` | Rounded corners |
| `"0.5rem"` | Subtle rounding |
| `"0"` | Sharp corners |
| `"2rem"` | Very rounded |

## Panel Shadow

Add depth with CSS box shadows.

### Screen Default

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"panel_shadow": "0 4px 12px rgba(0,0,0,0.3)"}'
```

### Per-Page Override

```json
{
  "content": ["Elevated panel"],
  "panel_shadow": "0 8px 24px rgba(0,0,0,0.4)"
}
```

### Per-Panel Shadow

```json
{
  "content": [
    {"type": "text", "value": "No shadow", "panel_shadow": "none"},
    {"type": "text", "value": "Strong shadow", "panel_shadow": "0 8px 24px rgba(0,0,0,0.5)"}
  ]
}
```

### Common Values

| Value | Description |
|-------|-------------|
| `null` or omit | No shadow |
| `"0 2px 4px rgba(0,0,0,0.1)"` | Subtle lift |
| `"0 4px 12px rgba(0,0,0,0.3)"` | Medium depth |
| `"0 8px 24px rgba(0,0,0,0.4)"` | Strong elevation |
| `"none"` | Explicitly disable |

## Style Recipes

### Tiling Window Manager Style

Edge-to-edge panels:

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "gap": "0",
    "border_radius": "0",
    "panel_shadow": null
  }'
```

### Floating Cards Style

Card-based layout with shadows:

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "gap": "1.5rem",
    "border_radius": "1rem",
    "panel_shadow": "0 8px 24px rgba(0,0,0,0.4)"
  }'
```

### Restaurant Menu Board

```json
{
  "content": [
    "# Joe's Diner",
    "Burger - $8.99", "Fries - $3.99",
    "Pizza - $12.99", "Salad - $6.99",
    "Hot Dog - $5.99", "Wings - $9.99"
  ],
  "layout": "menu-board",
  "background_color": "#1a1a1a",
  "panel_color": "#2d2d2d"
}
```

### Train Departure Board

```json
{
  "content": [
    "# Departures",
    "10:15 | Platform 1 | Chicago Express",
    "10:32 | Platform 3 | Regional",
    "10:45 | Platform 2 | NYC Shuttle",
    "11:00 | Platform 1 | Boston Line"
  ],
  "layout": "schedule"
}
```

### Dashboard with Charts

```json
{
  "content": [
    {"type": "markdown", "value": "# System Status"},
    {"type": "widget", "widget_type": "chart", "widget_config": {"chart_type": "line", "labels": ["Mon", "Tue", "Wed"], "values": [100, 120, 115]}},
    {"type": "widget", "widget_type": "chart", "widget_config": {"chart_type": "bar", "labels": ["A", "B", "C"], "values": [30, 50, 20]}},
    {"type": "widget", "widget_type": "clock"}
  ],
  "layout": "dashboard-header"
}
```

## Style Inheritance

Settings follow this precedence (highest to lowest):

1. Per-panel values (in content item)
2. Per-page values (in page/message request)
3. Screen defaults (set via PATCH)
4. Theme defaults (when a theme is applied)
5. System defaults
