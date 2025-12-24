# Dashboard Example

Build a rotating dashboard with multiple metrics pages.

## Setup

First, create a screen and enable rotation:

```bash
# Create screen
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/screens)
SCREEN_ID=$(echo $RESPONSE | jq -r '.screen_id')
API_KEY=$(echo $RESPONSE | jq -r '.api_key')

# Apply theme and enable rotation
curl -X PATCH "http://localhost:8000/api/v1/screens/$SCREEN_ID" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "theme": "catppuccin-mocha",
    "rotation_enabled": true,
    "rotation_interval": 30
  }'
```

## Main Dashboard Page

```bash
curl -X POST "http://localhost:8000/api/v1/screens/$SCREEN_ID/pages/default" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Sales Dashboard"},
      {"type": "text", "value": "$52,847"},
      {"type": "text", "value": "156 Orders"},
      {"type": "widget", "widget_type": "clock", "widget_config": {"style": "digital", "show_date": true}}
    ]
  }'
```

## Metrics Page

```bash
curl -X POST "http://localhost:8000/api/v1/screens/$SCREEN_ID/pages/metrics" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# System Metrics"},
      {"type": "text", "value": "CPU: 45%", "panel_color": "#27ae60"},
      {"type": "text", "value": "Memory: 2.1GB", "panel_color": "#27ae60"},
      {"type": "text", "value": "Disk: 78%", "panel_color": "#f39c12"}
    ]
  }'
```

## Status Page

```bash
curl -X POST "http://localhost:8000/api/v1/screens/$SCREEN_ID/pages/status" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "content": [
      {"type": "text", "value": "API", "panel_color": "#27ae60"},
      {"type": "text", "value": "Database", "panel_color": "#27ae60"},
      {"type": "text", "value": "Cache", "panel_color": "#27ae60"},
      {"type": "text", "value": "Queue", "panel_color": "#27ae60"}
    ]
  }'
```

## Python Update Script

```python
import requests
import time
import random

BASE_URL = "http://localhost:8000"
SCREEN_ID = "your_screen_id"
API_KEY = "sk_your_api_key"

def update_dashboard():
    # Simulate changing metrics
    revenue = random.randint(40000, 60000)
    orders = random.randint(100, 200)

    requests.post(
        f"{BASE_URL}/api/v1/screens/{SCREEN_ID}/pages/default",
        headers={"X-API-Key": API_KEY},
        json={
            "content": [
                {"type": "markdown", "value": "# Sales Dashboard"},
                {"type": "text", "value": f"${revenue:,}"},
                {"type": "text", "value": f"{orders} Orders"},
                {"type": "widget", "widget_type": "clock",
                 "widget_config": {"style": "digital", "show_date": True}}
            ]
        }
    )

# Update every 30 seconds
while True:
    update_dashboard()
    time.sleep(30)
```

## Home Assistant Integration

```yaml
# configuration.yaml
rest_command:
  update_dashboard:
    url: "http://your-server:8000/api/v1/screens/abc123/message"
    method: POST
    headers:
      X-API-Key: "sk_your_api_key"
      Content-Type: "application/json"
    payload: >
      {
        "content": [
          {"type": "markdown", "value": "# Home Status"},
          {"type": "text", "value": "{{ states('sensor.temperature') }}°F"},
          {"type": "text", "value": "{{ states('sensor.humidity') }}%"},
          {"type": "text", "value": "{{ states('sensor.power') }}W"}
        ]
      }

# automation.yaml
automation:
  - alias: "Update Dashboard"
    trigger:
      - platform: time_pattern
        minutes: "/5"
    action:
      - service: rest_command.update_dashboard
```
