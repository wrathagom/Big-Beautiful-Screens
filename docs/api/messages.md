# Messages API

The message endpoint is the simplest way to update screen content. It updates the `default` page.

## Send a Message

Update the default page content.

```http
POST /api/v1/screens/{screen_id}/message
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Screen API key |
| `Content-Type` | Yes | `application/json` |

**Body Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | array | Content items (required) |
| `background_color` | string | Background color/gradient |
| `panel_color` | string | Panel color/gradient |
| `font_family` | string | Font family |
| `font_color` | string | Text color |
| `gap` | string | Space between panels |
| `border_radius` | string | Panel corner radius |
| `panel_shadow` | string | Panel box-shadow |

## Simple Text

Send an array of strings:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"content": ["Hello, World!"]}'
```

**Response:**

```json
{
  "success": true,
  "viewers": 2
}
```

## Multiple Panels

Content automatically arranges based on item count:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      "Panel 1",
      "Panel 2",
      "Panel 3",
      "Panel 4"
    ]
  }'
```

| Items | Layout |
|-------|--------|
| 1 | Full screen |
| 2 | Side by side (50/50) |
| 3 | Top half + bottom split |
| 4 | 2x2 grid |
| 5-6 | 3-column grid |

## Structured Content

Explicitly specify content types:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "text", "value": "Plain text"},
      {"type": "markdown", "value": "# Heading\n**Bold** text"},
      {"type": "image", "url": "https://example.com/image.jpg"},
      {"type": "widget", "widget_type": "clock", "widget_config": {"style": "digital"}}
    ]
  }'
```

See [Content Types](../content/types.md) for all available types.

## With Styling

Apply colors and fonts:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": ["Styled Content"],
    "background_color": "#1a1a2e",
    "panel_color": "#16213e",
    "font_family": "Georgia, serif",
    "font_color": "#f1c40f"
  }'
```

## Per-Panel Styling

Override styles for individual panels:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "text", "value": "OK", "panel_color": "#27ae60"},
      {"type": "text", "value": "WARNING", "panel_color": "#f39c12"},
      {"type": "text", "value": "ERROR", "panel_color": "#c0392b"}
    ]
  }'
```

## Gradients

Use CSS gradients for backgrounds:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": ["Gradient Background"],
    "background_color": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
  }'
```

## Real-Time Updates

Messages are delivered instantly to all connected viewers via WebSocket. There's no polling—changes appear immediately.

```python
import requests
import time

# Update every second
while True:
    requests.post(
        "http://localhost:8000/api/v1/screens/abc123/message",
        headers={"X-API-Key": "sk_your_key"},
        json={"content": [f"Time: {time.strftime('%H:%M:%S')}"]}
    )
    time.sleep(1)
```

## Backward Compatibility

The `/message` endpoint exists for simple use cases. For multi-page screens, use the [Pages API](pages.md) instead.

`/message` is equivalent to:

```
POST /api/v1/screens/{id}/pages/default
```
