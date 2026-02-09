# MCP Server

Big Beautiful Screens includes a built-in MCP (Model Context Protocol) server that enables AI agents like Claude Desktop to programmatically manage screens, content, and styling.

## Overview

The MCP server wraps the existing REST API endpoints, providing a standardized interface for AI agents to:

- List and manage screens
- Send content to screens
- Create and manage pages for rotation
- Apply themes and styling
- Query available layouts

## Setup

### Prerequisites

1. A running Big Beautiful Screens instance (SaaS or self-hosted)
2. An MCP-compatible AI agent (e.g., Claude Desktop)

### Installation

The MCP server is included with Big Beautiful Screens. No additional installation is required.

### Running the MCP Server

The MCP server supports two transport modes:

#### HTTP/SSE Transport (Recommended for Railway/Remote)

The MCP server is automatically available as HTTP endpoints when running the FastAPI application:

- **SSE Endpoint**: `GET /mcp/sse` - Server-Sent Events connection for receiving messages
- **Messages Endpoint**: `POST /mcp/messages` - Send messages to the MCP server

This mode works with Railway and other cloud deployments since it runs as part of the main FastAPI application.

#### Streamable HTTP Transport (Codex)

Codex expects MCP over **Streamable HTTP** (not the legacy SSE + `/messages` pattern).
Big Beautiful Screens also exposes a Streamable HTTP MCP endpoint:

- **Streamable HTTP Endpoint**: `GET|POST|DELETE /mcp/http` - Streamable HTTP MCP transport

#### Stdio Transport (Local Development)

For local development or direct integration, you can run the MCP server as a standalone process:

```bash
# Using the CLI script
python -m app.mcp.cli

# Or if installed via pip
bbs-mcp-server
```

## Configuration

### Claude Desktop Configuration

Add the following to your Claude Desktop configuration file:

=== "SaaS Mode (HTTP/SSE)"

    ```json
    {
      "mcpServers": {
        "big-beautiful-screens": {
          "url": "https://your-bbs-instance.railway.app/mcp/sse",
          "transport": "sse"
        }
      }
    }
    ```

=== "Self-Hosted Mode (HTTP/SSE)"

    ```json
    {
      "mcpServers": {
        "big-beautiful-screens": {
          "url": "http://localhost:8000/mcp/sse",
          "transport": "sse"
        }
      }
    }
    ```

=== "Local Development (Stdio)"

    ```json
    {
      "mcpServers": {
        "big-beautiful-screens": {
          "command": "python",
          "args": ["-m", "app.mcp.cli"],
          "cwd": "/path/to/Big-Beautiful-Screens",
          "env": {
            "APP_MODE": "self-hosted"
          }
        }
      }
    }
    ```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `APP_MODE` | Application mode: `saas` or `self-hosted` | No (defaults to `self-hosted`) |
| `BBS_API_KEY` | Account API key (`ak_` prefix) for SaaS mode | SaaS only |
| `BBS_API_URL` | Base URL of your BBS instance | No (defaults to `http://localhost:8000`) |

## Available Tools

### list_screens

List all screens accessible to the authenticated user.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number (default: 1) |
| `per_page` | integer | Items per page (default: 20, max: 100) |

**Example:**

```
List all my screens
```

### create_screen

Create a new display screen.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Optional name for the screen |
| `template_id` | string | Optional template ID to initialize with |

**Example:**

```
Create a new screen called "Office Dashboard"
```

### get_screen

Get details of a specific screen.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `screen_id` | string | Yes | The screen's unique identifier |

**Example:**

```
Get the details of screen abc123def456
```

### update_screen

Update a screen's properties.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `screen_id` | string | Yes | The screen's unique identifier |
| `api_key` | string | Yes | The screen's API key (`sk_` prefix) |
| `name` | string | No | New screen name |
| `theme` | string | No | Theme name to apply |
| `rotation_enabled` | boolean | No | Enable/disable page rotation |
| `rotation_interval` | integer | No | Seconds between page transitions |
| `background_color` | string | No | Screen background color |
| `panel_color` | string | No | Default panel color |
| `font_family` | string | No | Default font family |
| `font_color` | string | No | Default text color |
| `gap` | string | No | Gap between panels |
| `border_radius` | string | No | Panel corner rounding |
| `default_layout` | string | No | Default layout preset |
| `transition` | string | No | Transition effect (`none`, `fade`, `slide-left`) |

**Example:**

```
Update screen abc123 to use the "nord" theme with 10 second rotation
```

### delete_screen

Delete a screen and all its pages.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `screen_id` | string | Yes | The screen's unique identifier |
| `api_key` | string | Yes | The screen's API key |

**Example:**

```
Delete screen abc123 with API key sk_xxx
```

### send_message

Send content to a screen's default page.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `screen_id` | string | Yes | The screen's unique identifier |
| `api_key` | string | Yes | The screen's API key |
| `content` | array | Yes | Array of content items |
| `layout` | string | No | Layout preset name |
| `background_color` | string | No | Background color |
| `panel_color` | string | No | Panel color |
| `font_family` | string | No | Font family |
| `font_color` | string | No | Text color |

**Content Types:**

- **Text**: Plain strings are auto-detected
- **Markdown**: Strings starting with `#` or containing markdown syntax
- **Images**: URLs ending in `.png`, `.jpg`, `.gif`, etc.
- **Videos**: URLs ending in `.mp4`, `.webm`, etc.

**Example:**

```
Send a message to screen abc123 with content:
- "# Welcome"
- "Current time: 10:30 AM"
- "https://example.com/chart.png"
```

### create_page

Create or update a named page for rotation.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `screen_id` | string | Yes | The screen's unique identifier |
| `page_name` | string | Yes | Name of the page |
| `api_key` | string | Yes | The screen's API key |
| `content` | array | Yes | Array of content items |
| `layout` | string | No | Layout preset |
| `duration` | integer | No | Display duration in seconds |
| `background_color` | string | No | Page background color |
| `panel_color` | string | No | Page panel color |
| `transition` | string | No | Transition effect |

**Example:**

```
Create a page called "stats" on screen abc123 with sales metrics
```

### list_layouts

List all available layout presets.

**Example:**

```
What layouts are available?
```

## Authentication

### SaaS Mode

In SaaS mode, the MCP server uses account API keys (`ak_` prefix) for authentication. These keys provide access to account-level operations like listing and creating screens.

To create an account API key:

1. Log in to your Big Beautiful Screens account
2. Go to Settings → API Keys
3. Create a new account key
4. Copy the key and add it to your MCP configuration

### Self-Hosted Mode

In self-hosted mode, no account-level authentication is required. The MCP server can list and create screens without an API key.

For screen-specific operations (update, delete, send message), you still need the screen's API key (`sk_` prefix).

## Example Workflows

### Create a Dashboard

```
1. Create a new screen called "Sales Dashboard"
2. Apply the "catppuccin-mocha" theme
3. Send content with sales metrics and charts
4. Enable rotation with 30 second intervals
```

### Multi-Page Display

```
1. Create a screen for the office lobby
2. Create a "welcome" page with company logo and greeting
3. Create a "news" page with company announcements
4. Create a "weather" page with local weather
5. Enable rotation between pages
```

### Update Existing Screen

```
1. List my screens to find the dashboard
2. Get the screen details to see current settings
3. Update the content with new metrics
4. Change the theme to "nord"
```

## Error Handling

The MCP server returns structured error responses:

```json
{
  "error": "Screen not found"
}
```

Common errors:

| Error | Description |
|-------|-------------|
| `Screen not found` | The specified screen_id doesn't exist |
| `Invalid API key` | The provided API key doesn't match |
| `api_key is required` | Missing required API key parameter |
| `content is required` | Missing required content parameter |
| `Screen limit reached` | User has reached their plan's screen limit (SaaS) |

## Security Considerations

1. **API Keys**: Never share screen API keys (`sk_`) publicly. They provide full control over the screen.
2. **Account Keys**: Account API keys (`ak_`) should be stored securely and rotated regularly.
3. **Environment Variables**: Use environment variables for sensitive configuration, not command-line arguments.
