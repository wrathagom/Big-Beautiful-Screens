# Big Beautiful Screens

API-driven real-time display screens for dashboards, menus, and signage.

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://wrathagom.github.io/Big-Beautiful-Screens/)
[![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-green)](LICENSE)

## Features

- **Real-time updates** via WebSocket
- **Auto-layout** based on content count
- **Auto-scaling text** to fill panels
- **Multiple content types** - text, markdown, images, video
- **Interactive widgets** - clocks, countdowns, charts
- **13+ themes** - Catppuccin, Nord, Dracula, and more
- **Multi-page rotation** with per-page durations
- **Ephemeral pages** that auto-expire

## Quick Start

```bash
# Run with Docker
docker run -d -p 8000:8000 ghcr.io/wrathagom/big-beautiful-screens

# Create a screen
curl -X POST http://localhost:8000/api/v1/screens

# Send content
curl -X POST http://localhost:8000/api/v1/screens/{id}/message \
  -H "X-API-Key: {api_key}" \
  -H "Content-Type: application/json" \
  -d '{"content": ["Hello, World!", "Panel 2", "Panel 3"]}'
```

Open `http://localhost:8000/screen/{id}` to view.

## Documentation

**[Read the full documentation →](https://wrathagom.github.io/Big-Beautiful-Screens/)**

- [Installation](https://wrathagom.github.io/Big-Beautiful-Screens/getting-started/installation/)
- [Quick Start](https://wrathagom.github.io/Big-Beautiful-Screens/getting-started/quickstart/)
- [API Reference](https://wrathagom.github.io/Big-Beautiful-Screens/api/screens/)
- [Content Types](https://wrathagom.github.io/Big-Beautiful-Screens/content/types/)
- [Widgets](https://wrathagom.github.io/Big-Beautiful-Screens/content/widgets/)
- [Themes](https://wrathagom.github.io/Big-Beautiful-Screens/styling/themes/)
- [Examples](https://wrathagom.github.io/Big-Beautiful-Screens/examples/dashboard/)

## Example

```bash
# Apply a theme
curl -X PATCH http://localhost:8000/api/v1/screens/{id} \
  -H "X-API-Key: {api_key}" \
  -d '{"theme": "catppuccin-mocha"}'

# Add a clock widget
curl -X POST http://localhost:8000/api/v1/screens/{id}/message \
  -H "X-API-Key: {api_key}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Dashboard"},
      {"type": "widget", "widget_type": "clock", "widget_config": {"style": "analog"}},
      {"type": "text", "value": "Status: Online", "panel_color": "#27ae60"}
    ]
  }'
```

## Use Cases

- **Dashboards** - Sales metrics, system status, KPIs
- **Digital signage** - Lobby displays, announcements
- **Menu boards** - Restaurant menus, specials
- **Status boards** - Build status, server health
- **Event displays** - Schedules, countdowns

## Admin Dashboard

Visit `http://localhost:8000/admin/screens` to manage screens, view active viewers, and copy API credentials.

## Development

```bash
# Clone and setup
git clone https://github.com/wrathagom/Big-Beautiful-Screens.git
cd Big-Beautiful-Screens
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
uvicorn app.main:app --reload

# Test
pytest tests/ -v
```

## License

[PolyForm Noncommercial 1.0.0](LICENSE)

Free for noncommercial use. Commercial use requires a separate license—contact the author for details.
