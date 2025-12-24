# Colors & Fonts

Customize the appearance of your screens with colors, fonts, and gradients.

## Color Hierarchy

Colors follow this precedence (first match wins):

1. **Per-panel** - Set on individual content items
2. **Per-page** - Set in the page request
3. **Screen defaults** - Set via screen settings
4. **Theme defaults** - Applied when a theme is set
5. **System defaults** - Transparent/inherit

## Background Color

Set the screen background:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": ["Hello"],
    "background_color": "#1a1a2e"
  }'
```

### Screen Default

Set a default background for all pages:

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"background_color": "#1a1a2e"}'
```

## Panel Color

Set the panel (card) background:

```json
{
  "content": ["Panel content"],
  "panel_color": "#16213e"
}
```

### Per-Panel Override

Different colors for each panel:

```json
{
  "content": [
    {"type": "text", "value": "Success", "panel_color": "#27ae60"},
    {"type": "text", "value": "Warning", "panel_color": "#f39c12"},
    {"type": "text", "value": "Error", "panel_color": "#c0392b"}
  ]
}
```

## Font Family

Set the font:

```json
{
  "content": ["Custom font"],
  "font_family": "Georgia, serif"
}
```

Common font stacks:

| Name | Value |
|------|-------|
| System | `system-ui, sans-serif` |
| Serif | `Georgia, serif` |
| Monospace | `'Courier New', monospace` |
| Modern | `'Helvetica Neue', sans-serif` |

### Per-Panel Font

```json
{
  "content": [
    {"type": "text", "value": "Monospace", "font_family": "monospace"},
    {"type": "text", "value": "Serif", "font_family": "Georgia, serif"}
  ]
}
```

## Font Color

Set the text color:

```json
{
  "content": ["Colored text"],
  "font_color": "#f1c40f"
}
```

### Per-Panel Color

```json
{
  "content": [
    {"type": "text", "value": "Gold", "font_color": "#f1c40f"},
    {"type": "text", "value": "Cyan", "font_color": "#00bcd4"}
  ]
}
```

## Gradients

Both `background_color` and `panel_color` accept CSS gradients.

### Linear Gradient

```json
{
  "content": ["Gradient background"],
  "background_color": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
}
```

### Radial Gradient

```json
{
  "content": [
    {
      "type": "text",
      "value": "Radial",
      "panel_color": "radial-gradient(circle, #ffd89b 0%, #19547b 100%)"
    }
  ]
}
```

### Common Gradients

| Name | Value |
|------|-------|
| Purple Dream | `linear-gradient(135deg, #667eea 0%, #764ba2 100%)` |
| Ocean | `linear-gradient(180deg, #2c3e50 0%, #4ca1af 100%)` |
| Sunset | `linear-gradient(to right, #f83600 0%, #f9d423 100%)` |
| Forest | `linear-gradient(135deg, #134e5e 0%, #71b280 100%)` |

## Complete Example

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Dashboard"},
      {"type": "text", "value": "Online", "panel_color": "#27ae60", "font_color": "#fff"},
      {"type": "text", "value": "42", "font_family": "monospace", "font_color": "#00bcd4"}
    ],
    "background_color": "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
    "panel_color": "#16213e",
    "font_family": "system-ui, sans-serif",
    "font_color": "#ecf0f1"
  }'
```

## Google Fonts

Use custom Google Fonts by setting `head_html` on the screen:

```bash
# Set custom font link
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "head_html": "<link href=\"https://fonts.googleapis.com/css2?family=Roboto+Mono&display=swap\" rel=\"stylesheet\">",
    "font_family": "\"Roboto Mono\", monospace"
  }'
```
