# Getting Started with Hosted BBS

Get up and running in minutes with the hosted version of Big Beautiful Screens.

## 1. Sign Up

Head to [bigbeautifulscreens.com](https://bigbeautifulscreens.com) and create an account. You'll be taken to your dashboard automatically.

## 2. Create Your First Screen

Click **+ Create New Screen** in your dashboard. You can start from scratch or choose a template.

Once created, you'll see:

- **Screen URL** - Open this on any device to display your screen
- **API Key** - Use this to send content to your screen
- **API Endpoint** - The URL for pushing updates

## 3. Send Content

Use the API to push content to your screen. Replace `{screen_id}` and `{api_key}` with your values:

=== "cURL"

    ```bash
    curl -X POST https://bigbeautifulscreens.com/api/v1/screens/{screen_id}/message \
      -H "X-API-Key: {api_key}" \
      -H "Content-Type: application/json" \
      -d '{"content": ["Hello, World!", "Panel 2", "Panel 3"]}'
    ```

=== "Python"

    ```python
    import requests

    response = requests.post(
        "https://bigbeautifulscreens.com/api/v1/screens/{screen_id}/message",
        headers={"X-API-Key": "{api_key}"},
        json={"content": ["Hello, World!", "Panel 2", "Panel 3"]}
    )
    ```

=== "JavaScript"

    ```javascript
    fetch("https://bigbeautifulscreens.com/api/v1/screens/{screen_id}/message", {
      method: "POST",
      headers: {
        "X-API-Key": "{api_key}",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        content: ["Hello, World!", "Panel 2", "Panel 3"]
      })
    });
    ```

## 4. View Your Screen

Open the screen URL in any browser, smart TV, or display device. Content updates appear instantly via WebSocket.

## What's Next?

- [Content Types](../content/types.md) - Text, images, video, widgets, and more
- [Layouts](../styling/layout.md) - Grids, dashboards, sidebars
- [Themes](../styling/themes.md) - Pre-built color schemes
- [Multi-Page Rotation](../api/pages.md) - Cycle through multiple pages
- [API Reference](../api/messages.md) - Full API documentation
