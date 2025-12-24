# Screens API

Screens are the core resource in Big Beautiful Screens. Each screen has a unique ID and API key.

## Create a Screen

Creates a new screen and returns credentials.

```http
POST /api/v1/screens
```

**Response:**

```json
{
  "screen_id": "abc123def456",
  "api_key": "sk_AbCdEfGhIjKlMnOpQrStUvWx",
  "screen_url": "/screen/abc123def456",
  "api_url": "/api/v1/screens/abc123def456/message"
}
```

!!! note "API Key Security"
    The API key is only shown once at creation. Store it securely.

## Update Screen Settings

Update screen configuration like name, rotation, and styling defaults.

```http
PATCH /api/v1/screens/{screen_id}
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Screen API key |

**Body Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Display name for the screen |
| `rotation_enabled` | boolean | Enable page rotation |
| `rotation_interval` | integer | Seconds between page transitions |
| `gap` | string | Space between panels (e.g., `"1rem"`, `"0"`) |
| `border_radius` | string | Panel corner rounding (e.g., `"1rem"`, `"0"`) |
| `panel_shadow` | string | CSS box-shadow for panels |
| `background_color` | string | Default background color/gradient |
| `panel_color` | string | Default panel color/gradient |
| `font_family` | string | Default font family |
| `font_color` | string | Default text color |
| `theme` | string | Apply a pre-defined theme |

**Example:**

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123def456 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "name": "Office Dashboard",
    "rotation_enabled": true,
    "rotation_interval": 30,
    "theme": "catppuccin-mocha"
  }'
```

**Response:**

```json
{
  "success": true,
  "name": "Office Dashboard",
  "settings": {
    "enabled": true,
    "interval": 30,
    "gap": "1rem",
    "border_radius": "0.5rem",
    "panel_shadow": "0 4px 12px rgba(0,0,0,0.3)",
    "background_color": "#1e1e2e",
    "panel_color": "#313244",
    "font_family": "system-ui, sans-serif",
    "font_color": "#cdd6f4",
    "theme": "catppuccin-mocha"
  }
}
```

## Delete a Screen

Permanently deletes a screen and all its pages.

```http
DELETE /api/v1/screens/{screen_id}
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Screen API key |

**Example:**

```bash
curl -X DELETE http://localhost:8000/api/v1/screens/abc123def456 \
  -H "X-API-Key: sk_your_api_key"
```

**Response:**

```json
{
  "success": true,
  "message": "Screen deleted"
}
```

## Reload Screen Viewers

Force all connected viewers to refresh their browser. Useful for clearing cached assets.

```http
POST /api/v1/screens/{screen_id}/reload
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Screen API key |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123def456/reload \
  -H "X-API-Key: sk_your_api_key"
```

**Response:**

```json
{
  "success": true,
  "viewers_reloaded": 3
}
```

## View a Screen

Open a screen in any web browser:

```
GET /screen/{screen_id}
```

This endpoint serves the screen viewer HTML page. Connect any device—browser, Smart TV, Raspberry Pi—to this URL.

## Authentication

All write operations require the `X-API-Key` header with the screen's API key.

```bash
curl -X POST http://localhost:8000/api/v1/screens/{id}/message \
  -H "X-API-Key: sk_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"content": ["Hello"]}'
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 401 | Invalid or missing API key |
| 404 | Screen not found |
| 422 | Invalid request body |
