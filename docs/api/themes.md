# Themes API

Big Beautiful Screens includes 13+ pre-defined themes for quick styling.

## List Themes

Get all available themes with their values.

```http
GET /api/v1/themes
```

**Response:**

```json
{
  "themes": [
    {
      "name": "catppuccin-mocha",
      "background_color": "#1e1e2e",
      "panel_color": "#313244",
      "font_family": "system-ui, sans-serif",
      "font_color": "#cdd6f4",
      "gap": "1rem",
      "border_radius": "0.5rem",
      "panel_shadow": "0 4px 12px rgba(0,0,0,0.3)"
    },
    ...
  ]
}
```

## Apply a Theme

Set a theme on a screen:

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"theme": "catppuccin-mocha"}'
```

## Available Themes

| Theme | Description |
|-------|-------------|
| `default` | Dark gray, clean defaults |
| `minimal` | White, lots of whitespace |
| `elegant` | Gradients, serif fonts, refined shadows |
| `modern` | Black, sharp corners, bold |
| `mono` | Monospace font, terminal feel |
| `catppuccin-mocha` | Popular pastel dark theme |
| `catppuccin-latte` | Light version of Catppuccin |
| `solarized-dark` | Classic developer theme |
| `solarized-light` | Light variant of Solarized |
| `dracula` | Purple-tinted dark theme |
| `nord` | Arctic, bluish dark theme |
| `gruvbox-dark` | Retro groove colors |
| `tokyo-night` | Popular VS Code theme |

## Theme with Overrides

Apply a theme but override specific values:

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

This applies the Catppuccin Mocha colors but with edge-to-edge panels.

## Theme Previews

### Catppuccin Mocha

```json
{
  "background_color": "#1e1e2e",
  "panel_color": "#313244",
  "font_color": "#cdd6f4"
}
```

### Nord

```json
{
  "background_color": "#2e3440",
  "panel_color": "#3b4252",
  "font_color": "#eceff4"
}
```

### Dracula

```json
{
  "background_color": "#282a36",
  "panel_color": "#44475a",
  "font_color": "#f8f8f2"
}
```

### Solarized Dark

```json
{
  "background_color": "#002b36",
  "panel_color": "#073642",
  "font_color": "#839496"
}
```

### Tokyo Night

```json
{
  "background_color": "#1a1b26",
  "panel_color": "#24283b",
  "font_color": "#a9b1d6"
}
```
