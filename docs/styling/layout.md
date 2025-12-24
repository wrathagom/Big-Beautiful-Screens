# Layout & Spacing

Control the spacing, corners, and shadows of your screen layout.

## Auto Layout

Content automatically arranges based on item count:

| Items | Layout |
|-------|--------|
| 1 | Full screen |
| 2 | Side by side (50/50) |
| 3 | Top half + bottom split |
| 4 | 2x2 grid |
| 5-6 | 3-column grid |

No configuration needed—just send your content and it arranges automatically.

## Panel Gap

Control the space between panels.

### Screen Default

Set the default gap for all pages:

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

## Tiling Window Manager Style

For a true tiling WM aesthetic with edge-to-edge panels:

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

Or with a theme:

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "theme": "catppuccin-mocha",
    "gap": "0",
    "border_radius": "0"
  }'
```

## Floating Cards Style

For a card-based layout with shadows and spacing:

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

## Style Inheritance

Layout settings follow this precedence:

1. Per-page values (in page/message request)
2. Screen defaults (set via PATCH)
3. Theme defaults (when a theme is applied)
4. System defaults (`1rem` gap, `1rem` radius, no shadow)

## Example: Dashboard Layout

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Metrics"},
      {"type": "text", "value": "1,234"},
      {"type": "text", "value": "5,678"},
      {"type": "text", "value": "9,012"}
    ],
    "gap": "0.75rem",
    "border_radius": "0.5rem",
    "panel_shadow": "0 2px 8px rgba(0,0,0,0.2)",
    "background_color": "#0d1117",
    "panel_color": "#161b22"
  }'
```
