# Status Display Example

Build a status board showing service health, build status, or system state.

## Simple Status Board

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "text", "value": "API", "panel_color": "#27ae60"},
      {"type": "text", "value": "Database", "panel_color": "#27ae60"},
      {"type": "text", "value": "Cache", "panel_color": "#f39c12"},
      {"type": "text", "value": "Queue", "panel_color": "#c0392b"}
    ],
    "background_color": "#1a1a2e"
  }'
```

## Build Status Display

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Build Status"},
      {"type": "text", "value": "main\nPASSING", "panel_color": "#27ae60"},
      {"type": "text", "value": "develop\nBUILDING", "panel_color": "#3498db"},
      {"type": "text", "value": "feature/auth\nFAILED", "panel_color": "#c0392b"}
    ],
    "theme": "tokyo-night"
  }'
```

## Server Monitoring

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Server Status\n\nUpdated: 2:34 PM"},
      {"type": "markdown", "value": "## web-01\nCPU: 23%\nMem: 4.2GB\nDisk: 45%", "panel_color": "#27ae60"},
      {"type": "markdown", "value": "## web-02\nCPU: 67%\nMem: 6.8GB\nDisk: 72%", "panel_color": "#f39c12"},
      {"type": "markdown", "value": "## db-01\nCPU: 12%\nMem: 28GB\nDisk: 89%", "panel_color": "#e74c3c"}
    ]
  }'
```

## Python Monitoring Script

```python
import requests
import psutil
import time

BASE_URL = "http://localhost:8000"
SCREEN_ID = "your_screen_id"
API_KEY = "sk_your_api_key"

def get_status_color(value, warning=70, critical=90):
    if value >= critical:
        return "#c0392b"
    elif value >= warning:
        return "#f39c12"
    return "#27ae60"

def update_status():
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    requests.post(
        f"{BASE_URL}/api/v1/screens/{SCREEN_ID}/message",
        headers={"X-API-Key": API_KEY},
        json={
            "content": [
                {"type": "markdown", "value": f"# System Status\n\nUpdated: {time.strftime('%I:%M %p')}"},
                {"type": "text", "value": f"CPU\n{cpu:.0f}%",
                 "panel_color": get_status_color(cpu)},
                {"type": "text", "value": f"Memory\n{memory:.0f}%",
                 "panel_color": get_status_color(memory)},
                {"type": "text", "value": f"Disk\n{disk:.0f}%",
                 "panel_color": get_status_color(disk)}
            ],
            "background_color": "#1a1a2e"
        }
    )

while True:
    update_status()
    time.sleep(10)
```

## GitHub Actions Status

```python
import requests

GITHUB_TOKEN = "your_github_token"
REPOS = ["owner/repo1", "owner/repo2", "owner/repo3"]

def get_workflow_status(repo):
    response = requests.get(
        f"https://api.github.com/repos/{repo}/actions/runs",
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
        params={"per_page": 1}
    )
    runs = response.json().get("workflow_runs", [])
    if runs:
        return runs[0]["conclusion"] or runs[0]["status"]
    return "unknown"

def status_to_color(status):
    return {
        "success": "#27ae60",
        "failure": "#c0392b",
        "in_progress": "#3498db",
        "queued": "#f39c12",
    }.get(status, "#95a5a6")

content = [{"type": "markdown", "value": "# CI Status"}]
for repo in REPOS:
    status = get_workflow_status(repo)
    content.append({
        "type": "text",
        "value": f"{repo.split('/')[1]}\n{status.upper()}",
        "panel_color": status_to_color(status)
    })

requests.post(
    "http://localhost:8000/api/v1/screens/abc123/message",
    headers={"X-API-Key": "sk_your_key"},
    json={"content": content, "theme": "tokyo-night"}
)
```

## Kubernetes Pod Status

```python
from kubernetes import client, config
import requests

config.load_kube_config()
v1 = client.CoreV1Api()

pods = v1.list_namespaced_pod(namespace="default")

content = [{"type": "markdown", "value": "# Pod Status"}]
for pod in pods.items[:6]:  # Max 6 panels
    phase = pod.status.phase
    color = {
        "Running": "#27ae60",
        "Pending": "#f39c12",
        "Failed": "#c0392b",
    }.get(phase, "#95a5a6")

    content.append({
        "type": "text",
        "value": f"{pod.metadata.name[:20]}\n{phase}",
        "panel_color": color
    })

requests.post(
    "http://localhost:8000/api/v1/screens/abc123/message",
    headers={"X-API-Key": "sk_your_key"},
    json={"content": content, "theme": "nord"}
)
```

## Alert Page

Create an ephemeral alert that auto-expires:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/pages/alert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# ⚠️ ALERT\n\nDatabase connection pool exhausted\n\nInvestigating..."}
    ],
    "background_color": "#c0392b",
    "panel_color": "#e74c3c",
    "font_color": "#ffffff",
    "expires_at": "2024-12-31T12:00:00Z"
  }'
```
