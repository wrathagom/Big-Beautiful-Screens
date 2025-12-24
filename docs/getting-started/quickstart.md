# Quick Start

This guide will get you displaying content on a screen in under 5 minutes.

## Step 1: Start the Server

=== "Docker"

    ```bash
    docker run -d -p 8000:8000 ghcr.io/wrathagom/big-beautiful-screens
    ```

=== "Manual"

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    ```

## Step 2: Create a Screen

```bash
curl -X POST http://localhost:8000/api/v1/screens
```

You'll get a response like:

```json
{
  "screen_id": "abc123def456",
  "api_key": "sk_AbCdEfGhIjKlMnOpQrStUvWx",
  "screen_url": "/screen/abc123def456",
  "api_url": "/api/v1/screens/abc123def456/message"
}
```

!!! tip "Save your credentials"
    Keep the `screen_id` and `api_key` handy—you'll need them for all API calls.

## Step 3: Open the Screen

Open your browser to:

```
http://localhost:8000/screen/abc123def456
```

You'll see "Waiting for content..."

## Step 4: Send Content

In a terminal, send your first message:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123def456/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_AbCdEfGhIjKlMnOpQrStUvWx" \
  -d '{"content": ["Hello, World!"]}'
```

Your screen instantly updates!

## Step 5: Try Multiple Panels

Send content with multiple items to see the auto-layout:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123def456/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_AbCdEfGhIjKlMnOpQrStUvWx" \
  -d '{
    "content": [
      "# Sales Today\n$12,345",
      "# Active Users\n1,234",
      "# Server Status\nOnline",
      "# Orders\n156"
    ]
  }'
```

## Step 6: Add Some Style

Apply a theme and customize colors:

```bash
curl -X PATCH http://localhost:8000/api/v1/screens/abc123def456 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_AbCdEfGhIjKlMnOpQrStUvWx" \
  -d '{"theme": "catppuccin-mocha"}'
```

## Step 7: Add a Widget

Display a live clock:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123def456/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_AbCdEfGhIjKlMnOpQrStUvWx" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Dashboard"},
      {"type": "widget", "widget_type": "clock", "widget_config": {"style": "digital", "show_date": true}},
      {"type": "widget", "widget_type": "clock", "widget_config": {"style": "analog"}}
    ]
  }'
```

## What's Next?

- [Content Types](../content/types.md) - Learn about text, markdown, images, and video
- [Widgets](../content/widgets.md) - Add interactive elements like clocks
- [Styling](../styling/colors.md) - Customize colors, fonts, and themes
- [Multi-page Rotation](../api/pages.md) - Set up rotating dashboards
- [Examples](../examples/dashboard.md) - Real-world use cases

## Admin Dashboard

Visit `http://localhost:8000/admin/screens` to:

- View all screens and active viewers
- Copy API keys and URLs
- Reload or delete screens
- Access code examples
