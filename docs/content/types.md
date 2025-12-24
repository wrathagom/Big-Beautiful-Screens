# Content Types

Big Beautiful Screens supports multiple content types that can be mixed and matched in any panel.

## Auto-Detection

When you send a string, the type is automatically detected:

| Input | Detected Type |
|-------|---------------|
| `"Hello World"` | Text |
| `"# Heading\nSome text"` | Markdown |
| `"https://example.com/image.jpg"` | Image |
| `"https://example.com/video.mp4"` | Video |

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      "Plain text",
      "# Markdown heading",
      "https://example.com/photo.jpg"
    ]
  }'
```

## Explicit Types

For precise control, specify the type explicitly:

```json
{
  "content": [
    {"type": "text", "value": "Plain text"},
    {"type": "markdown", "value": "# Heading"},
    {"type": "image", "url": "https://example.com/image.png"},
    {"type": "video", "url": "https://example.com/video.mp4"},
    {"type": "widget", "widget_type": "clock", "widget_config": {...}}
  ]
}
```

---

## Text

Plain text that auto-scales to fill the panel.

```json
{"type": "text", "value": "Hello, World!"}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `wrap` | boolean | `true` | Enable word wrapping |

### Text Wrapping

By default, text wraps at word boundaries to maximize font size:

```json
{"type": "text", "value": "This will wrap to multiple lines", "wrap": true}
```

Disable wrapping to keep text on a single line:

```json
{"type": "text", "value": "Single line only", "wrap": false}
```

---

## Markdown

Markdown content with support for headings, bold, italic, lists, and code.

```json
{"type": "markdown", "value": "# Heading\n\n**Bold** and *italic* text.\n\n- List item 1\n- List item 2"}
```

Markdown is rendered using [marked.js](https://marked.js.org/) and auto-scaled to fit the panel.

**Supported Syntax:**

- Headings (`#`, `##`, `###`)
- Bold (`**text**`)
- Italic (`*text*`)
- Code (`` `inline` `` and fenced blocks)
- Lists (ordered and unordered)
- Links
- Blockquotes

---

## Image

Display images from any URL.

```json
{"type": "image", "url": "https://example.com/photo.jpg"}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `image_mode` | string | `"contain"` | How image fills the panel |

### Image Modes

| Mode | Description |
|------|-------------|
| `contain` | Fit entire image in panel (default) |
| `cover` | Fill panel, crop edges (edge-to-edge) |
| `cover-width` | Fill panel width, may overflow height |
| `cover-height` | Fill panel height, may overflow width |

**Example - Full bleed image:**

```json
{"type": "image", "url": "https://example.com/photo.jpg", "image_mode": "cover"}
```

!!! tip
    Use `cover` mode for background-style images that fill the entire panel.

---

## Video

Embed videos with autoplay, loop, and mute controls.

```json
{
  "type": "video",
  "url": "https://example.com/video.mp4"
}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `autoplay` | boolean | `true` | Auto-start playback |
| `loop` | boolean | `true` | Loop when finished |
| `muted` | boolean | `true` | Mute audio |
| `image_mode` | string | `"contain"` | How video fills the panel |

**Example - Full screen background video:**

```json
{
  "type": "video",
  "url": "https://example.com/background.mp4",
  "autoplay": true,
  "loop": true,
  "muted": true,
  "image_mode": "cover"
}
```

!!! note
    Most browsers require videos to be muted for autoplay to work.

---

## Widget

Interactive elements like clocks, countdowns, and charts.

```json
{
  "type": "widget",
  "widget_type": "clock",
  "widget_config": {
    "style": "digital",
    "format": "12h"
  }
}
```

See [Widgets](widgets.md) for full documentation.

---

## Per-Panel Styling

Any content type can have per-panel styling:

```json
{
  "type": "text",
  "value": "Styled panel",
  "panel_color": "#c0392b",
  "font_color": "#ffffff",
  "font_family": "Georgia, serif"
}
```

| Option | Description |
|--------|-------------|
| `panel_color` | Background color for this panel |
| `font_color` | Text color for this panel |
| `font_family` | Font family for this panel |
| `panel_shadow` | Box shadow for this panel |

---

## Mixed Content

Combine different content types in one screen:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Dashboard"},
      {"type": "widget", "widget_type": "clock", "widget_config": {"style": "analog"}},
      {"type": "image", "url": "https://example.com/chart.png"},
      {"type": "text", "value": "Status: Online", "panel_color": "#27ae60"}
    ]
  }'
```
