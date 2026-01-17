# Templates API

Templates allow you to save and reuse screen configurations. There are two types:

- **System templates** - Pre-built templates provided by Big Beautiful Screens
- **User templates** - Your own saved screen configurations

## List Templates

Get available templates with pagination and filtering.

```http
GET /api/v1/templates
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-indexed) |
| `per_page` | integer | 20 | Items per page (1-100) |
| `type` | string | - | Filter by type: `system` or `user` |
| `category` | string | - | Filter by category (see categories below) |

**Categories:**

| Value | Description |
|-------|-------------|
| `restaurant` | Restaurant menus, specials boards |
| `it_tech` | Dashboards, monitoring, status displays |
| `small_business` | Retail, office displays, announcements |
| `education` | Classroom schedules, campus info |
| `healthcare` | Waiting rooms, patient info |
| `custom` | User-defined templates |

**Example:**

```bash
curl "http://localhost:8000/api/v1/templates?category=restaurant&per_page=10"
```

**Response:**

```json
{
  "templates": [
    {
      "id": "tmpl_abc123",
      "name": "Restaurant Menu Board",
      "description": "A clean menu board layout with header and specials",
      "category": "restaurant",
      "thumbnail_url": "data:image/svg+xml;base64,...",
      "type": "system",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "page": 1,
  "per_page": 10,
  "total_count": 5,
  "total_pages": 1
}
```

## Get Template Details

Get a specific template including its full configuration.

```http
GET /api/v1/templates/{template_id}
```

**Example:**

```bash
curl "http://localhost:8000/api/v1/templates/tmpl_abc123"
```

**Response:**

```json
{
  "id": "tmpl_abc123",
  "name": "Restaurant Menu Board",
  "description": "A clean menu board layout",
  "category": "restaurant",
  "thumbnail_url": "data:image/svg+xml;base64,...",
  "type": "system",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "configuration": {
    "background_color": "#1e1e2e",
    "panel_color": "#313244",
    "font_family": "system-ui, sans-serif",
    "font_color": "#cdd6f4",
    "gap": "1rem",
    "border_radius": "1rem",
    "default_layout": "dashboard-header",
    "pages": [
      {
        "name": "default",
        "content": [
          {"type": "text", "value": "Welcome!"}
        ]
      }
    ]
  }
}
```

## Create Template from Screen

Save an existing screen as a reusable template.

```http
POST /api/v1/templates
```

**Body Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `screen_id` | string | Yes | ID of the source screen |
| `name` | string | Yes | Template name (max 100 chars) |
| `description` | string | No | Description (max 500 chars) |
| `category` | string | Yes | Category (see categories above) |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/templates \
  -H "Content-Type: application/json" \
  -d '{
    "screen_id": "abc123def456",
    "name": "My Dashboard Layout",
    "description": "Custom dashboard with metrics and status",
    "category": "it_tech"
  }'
```

**Response:**

Returns the created template with full details (same format as Get Template Details).

!!! note "Automatic Thumbnail"
    A preview thumbnail is automatically generated based on the screen's layout and colors.

## Update Template

Update a template's metadata (name, description, category).

```http
PATCH /api/v1/templates/{template_id}
```

**Body Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | New template name |
| `description` | string | No | New description |
| `category` | string | No | New category |

**Example:**

```bash
curl -X PATCH http://localhost:8000/api/v1/templates/tmpl_abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Template Name",
    "category": "small_business"
  }'
```

**Response:**

Returns the updated template with full details.

!!! warning "System Templates"
    System templates cannot be modified. Attempting to update a system template returns a 403 error.

## Delete Template

Permanently delete a template.

```http
DELETE /api/v1/templates/{template_id}
```

**Example:**

```bash
curl -X DELETE http://localhost:8000/api/v1/templates/tmpl_abc123
```

**Response:**

```json
{
  "success": true
}
```

!!! warning "System Templates"
    System templates cannot be deleted. Attempting to delete a system template returns a 403 error.

## Create Screen from Template

To create a new screen from a template, use the screens endpoint with the `template_id` parameter:

```http
POST /api/v1/screens?template_id={template_id}
```

**Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/screens?template_id=tmpl_abc123"
```

This creates a new screen with:

- All settings from the template (colors, fonts, layout)
- All pages and content from the template
- A new unique screen ID and API key

See [Screens API](screens.md) for full response format.

## Error Responses

| Status | Description |
|--------|-------------|
| 401 | Authentication required (SaaS mode) |
| 403 | Cannot modify/delete system templates, or not authorized |
| 404 | Template or source screen not found |
| 422 | Invalid request body |
