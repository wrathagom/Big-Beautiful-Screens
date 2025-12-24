# Pages API

Screens can have multiple pages that rotate automatically. This is useful for dashboards that cycle through different views.

## How Pages Work

- Every screen has a required `default` page
- Additional pages can be added with any name
- Pages display in order based on `display_order`
- The `/message` endpoint updates the `default` page (for backward compatibility)

## List Pages

Get all pages for a screen.

```http
GET /api/v1/screens/{screen_id}/pages
```

**Response:**

```json
{
  "pages": [
    {
      "name": "default",
      "content": [...],
      "display_order": 0,
      "duration": null,
      "expires_at": null
    },
    {
      "name": "alerts",
      "content": [...],
      "display_order": 1,
      "duration": 10,
      "expires_at": null
    }
  ],
  "rotation": {
    "enabled": true,
    "interval": 30
  }
}
```

## Create or Update a Page

Create a new page or update an existing one.

```http
POST /api/v1/screens/{screen_id}/pages/{page_name}
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Screen API key |

**Body Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | array | Content items (required) |
| `duration` | integer | Seconds to display (overrides screen default) |
| `expires_at` | string | ISO timestamp for auto-expiry |
| `background_color` | string | Page background color |
| `panel_color` | string | Page panel color |
| `font_family` | string | Page font family |
| `font_color` | string | Page text color |
| `gap` | string | Page panel gap |
| `border_radius` | string | Page border radius |
| `panel_shadow` | string | Page panel shadow |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/pages/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": ["ALERT: Server maintenance in 10 minutes"],
    "background_color": "#c0392b",
    "duration": 10
  }'
```

**Response:**

```json
{
  "success": true,
  "page": {
    "name": "alerts",
    "content": [...],
    "display_order": 1,
    "duration": 10,
    "expires_at": null
  },
  "viewers": 2
}
```

## Delete a Page

Remove a page from the rotation.

```http
DELETE /api/v1/screens/{screen_id}/pages/{page_name}
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Screen API key |

!!! warning
    The `default` page cannot be deleted.

**Example:**

```bash
curl -X DELETE http://localhost:8000/api/v1/screens/abc123/pages/alerts \
  -H "X-API-Key: sk_your_api_key"
```

## Reorder Pages

Change the display order of pages.

```http
PUT /api/v1/screens/{screen_id}/pages/order
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Screen API key |

**Body:**

```json
{
  "page_names": ["alerts", "default", "weather"]
}
```

**Example:**

```bash
curl -X PUT http://localhost:8000/api/v1/screens/abc123/pages/order \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{"page_names": ["alerts", "default", "weather"]}'
```

## Rotation Settings

Enable or disable page rotation and set the interval.

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "rotation_enabled": true,
    "rotation_interval": 30
  }'
```

When rotation is enabled:

- Pages cycle automatically at the specified interval
- Each page can override the interval with its own `duration`
- Expired pages are silently skipped

## Per-Page Duration

Override the rotation interval for a specific page:

```json
{
  "content": ["BREAKING NEWS: ..."],
  "duration": 60
}
```

This page will display for 60 seconds instead of the screen's default.

## Ephemeral Pages

Create temporary pages that auto-expire:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/pages/flash-sale \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": ["Flash Sale! 50% off for the next hour"],
    "expires_at": "2024-12-31T23:59:59Z"
  }'
```

When the expiry time passes, the page is silently removed from rotation.

## Style Inheritance

Page styles follow this precedence (first match wins):

1. Per-panel values (in content items)
2. Per-page values (in page request)
3. Screen-level defaults (set via PATCH)
4. System defaults
