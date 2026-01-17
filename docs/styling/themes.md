# Themes

Apply pre-defined themes for quick, cohesive styling.

## Applying a Theme

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"theme": "catppuccin-mocha"}'
```

## Available Themes

### Dark Themes

#### Catppuccin Mocha

Popular pastel dark theme with soft colors.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "catppuccin-mocha"}'
```

| Property | Value |
|----------|-------|
| Background | `#1e1e2e` |
| Panel | `#313244` |
| Text | `#cdd6f4` |

![Catppuccin Mocha Theme](../images/screenshots/theme_catppuccin-mocha.png)

#### Nord

Arctic, bluish dark theme.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "nord"}'
```

| Property | Value |
|----------|-------|
| Background | `#2e3440` |
| Panel | `#3b4252` |
| Text | `#eceff4` |

![Nord Theme](../images/screenshots/theme_nord.png)

#### Dracula

Purple-tinted dark theme.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "dracula"}'
```

| Property | Value |
|----------|-------|
| Background | `#282a36` |
| Panel | `#44475a` |
| Text | `#f8f8f2` |

![Dracula Theme](../images/screenshots/theme_dracula.png)

#### Tokyo Night

Popular VS Code theme.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "tokyo-night"}'
```

| Property | Value |
|----------|-------|
| Background | `#1a1b26` |
| Panel | `#24283b` |
| Text | `#a9b1d6` |

![Tokyo Night Theme](../images/screenshots/theme_tokyo-night.png)

#### Gruvbox Dark

Retro groove colors.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "gruvbox-dark"}'
```

| Property | Value |
|----------|-------|
| Background | `#282828` |
| Panel | `#3c3836` |
| Text | `#ebdbb2` |

![Gruvbox Dark Theme](../images/screenshots/theme_gruvbox-dark.png)

#### Solarized Dark

Classic developer theme.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "solarized-dark"}'
```

| Property | Value |
|----------|-------|
| Background | `#002b36` |
| Panel | `#073642` |
| Text | `#839496` |

![Solarized Dark Theme](../images/screenshots/theme_solarized-dark.png)

### Light Themes

#### Catppuccin Latte

Light version of Catppuccin.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "catppuccin-latte"}'
```

| Property | Value |
|----------|-------|
| Background | `#eff1f5` |
| Panel | `#e6e9ef` |
| Text | `#4c4f69` |

![Catppuccin Latte Theme](../images/screenshots/theme_catppuccin-latte.png)

#### Solarized Light

Light variant of Solarized.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "solarized-light"}'
```

| Property | Value |
|----------|-------|
| Background | `#fdf6e3` |
| Panel | `#eee8d5` |
| Text | `#657b83` |

![Solarized Light Theme](../images/screenshots/theme_solarized-light.png)

#### Minimal

Clean white theme with ample whitespace.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "minimal"}'
```

![Minimal Theme](../images/screenshots/theme_minimal.png)

### Special Themes

#### Default

Clean dark gray defaults.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "default"}'
```

![Default Theme](../images/screenshots/theme_default.png)

#### Modern

Black with sharp corners, bold aesthetic.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "modern"}'
```

![Modern Theme](../images/screenshots/theme_modern.png)

#### Mono

Monospace font with terminal feel.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "mono"}'
```

![Mono Theme](../images/screenshots/theme_mono.png)

#### Elegant

Gradients with serif fonts and refined shadows.

```bash
curl -X PATCH .../screens/abc123 -d '{"theme": "elegant"}'
```

![Elegant Theme](../images/screenshots/theme_elegant.png)

## Theme with Overrides

Apply a theme but customize specific properties:

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

This applies Catppuccin Mocha colors with edge-to-edge panels.

## List All Themes

Get all themes with their complete values:

```bash
curl http://localhost:8000/api/v1/themes
```

## Per-Page Theme Override

Pages can override the screen theme with custom colors:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/pages/alert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": ["ALERT!"],
    "background_color": "#c0392b",
    "panel_color": "#e74c3c",
    "font_color": "#ffffff"
  }'
```

This page uses red colors regardless of the screen theme.
