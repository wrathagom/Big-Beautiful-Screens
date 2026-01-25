# Big Beautiful Screens

**API-driven real-time display screens for dashboards, menus, and signage.**

<div class="grid cards" markdown>

-   :material-server: **Self-Hosted**

    ---

    Run on your own infrastructure with Docker. Full control, no limits, completely free.

    [:octicons-arrow-right-24: Install & Run](getting-started/installation.md)

-   :material-cloud: **Hosted (SaaS)**

    ---

    Start creating screens immediately. No installation, free tier available.

    [:octicons-arrow-right-24: Start Creating](getting-started/saas-quickstart.md)

</div>

---

## Features

- **Real-time updates** via WebSocket - changes appear instantly
- **Auto-layout** - content arranges automatically based on item count
- **Auto-scaling text** - text sizes itself to fill available space
- **Multiple content types** - text, markdown, images, video, and widgets
- **Interactive widgets** - clocks, countdowns, and more
- **Theming** - 13+ pre-defined themes or fully custom styling
- **Multi-page rotation** - cycle through pages automatically
- **Ephemeral pages** - temporary content that auto-expires
- **Screen templates** - start from pre-built layouts or save your own

## Quick Example

```bash
# Create a screen
curl -X POST http://localhost:8000/api/v1/screens

# Send content
curl -X POST http://localhost:8000/api/v1/screens/{id}/message \
  -H "X-API-Key: {api_key}" \
  -H "Content-Type: application/json" \
  -d '{"content": ["Hello, World!", "Panel 2", "Panel 3"]}'
```

Open `http://localhost:8000/screen/{id}` to see your content update in real-time.

## Use Cases

- **Dashboards** - Sales metrics, system status, KPIs
- **Digital signage** - Lobby displays, announcements
- **Menu boards** - Restaurant menus, specials
- **Status boards** - Build status, server health
- **Event displays** - Schedules, countdowns
- **Office displays** - Meeting room signs, welcome screens

## Getting Started

Ready to get started? Head to the [Installation Guide](getting-started/installation.md) or jump straight to the [Quick Start](getting-started/quickstart.md).

## Architecture

```
┌─────────────────┐     REST API      ┌─────────────────┐
│  Your App/      │ ───────────────▶  │  Big Beautiful  │
│  Automation     │                   │  Screens        │
└─────────────────┘                   └────────┬────────┘
                                               │
                                               │ WebSocket
                                               ▼
                         ┌──────────────────────────────────────┐
                         │                                      │
                    ┌────┴────┐  ┌─────────┐  ┌─────────┐      │
                    │ Browser │  │ Smart   │  │ Rasp Pi │ ...  │
                    │         │  │ TV      │  │         │      │
                    └─────────┘  └─────────┘  └─────────┘      │
                         │                                      │
                         └──────────────────────────────────────┘
                                    Viewers
```
