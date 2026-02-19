# Account API Keys

Account-level API keys allow programmatic access to account-level operations like listing screens, creating screens, and managing templates, themes, and media. This is useful for MCP (Model Context Protocol) integration and automation.

!!! note "SaaS Mode Only"
    Account API keys are only available in SaaS mode. Self-hosted users can use basic authentication or other methods to secure their instance.

## Key Types

Big Beautiful Screens uses two types of API keys:

| Key Type | Prefix | Purpose |
|----------|--------|---------|
| Screen Key | `sk_` | Operations on a specific screen (send messages, update settings) |
| Account Key | `ak_` | Account-level operations (list screens, create screens, manage templates) |

## Create an Account Key

Creates a new account-level API key.

```http
POST /api/v1/account/keys
```

**Authentication:** Requires Clerk session authentication.

**Body Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | A descriptive name for the key (1-100 characters) |
| `expires_in_days` | integer | No | Days until expiration (1-365). Omit for no expiration. |

**Example:**

```bash
curl -X POST https://app.bigbeautifulscreens.com/api/v1/account/keys \
  -H "Authorization: Bearer {clerk_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MCP Integration",
    "expires_in_days": 90
  }'
```

**Response:**

```json
{
  "id": "ak_id_abc123",
  "name": "MCP Integration",
  "key": "ak_AbCdEfGhIjKlMnOpQrStUvWxYz123456",
  "scopes": ["*"],
  "expires_at": "2024-06-15T12:00:00Z",
  "created_at": "2024-03-15T12:00:00Z"
}
```

!!! warning "Store Your Key Securely"
    The full API key is only shown once at creation. Store it securely—you won't be able to retrieve it later.

## List Account Keys

Lists all account keys for the authenticated user.

```http
GET /api/v1/account/keys
```

**Authentication:** Requires Clerk session authentication.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `per_page` | integer | 20 | Items per page (max 100) |

**Example:**

```bash
curl https://app.bigbeautifulscreens.com/api/v1/account/keys \
  -H "Authorization: Bearer {clerk_token}"
```

**Response:**

```json
{
  "keys": [
    {
      "id": "ak_id_abc123",
      "name": "MCP Integration",
      "key_preview": "ak_AbCd...3456",
      "scopes": ["*"],
      "expires_at": "2024-06-15T12:00:00Z",
      "created_at": "2024-03-15T12:00:00Z",
      "last_used_at": "2024-03-20T08:30:00Z"
    }
  ],
  "total_count": 1,
  "page": 1,
  "per_page": 20
}
```

## Delete an Account Key

Permanently deletes an account key. This immediately revokes access for any integrations using this key.

```http
DELETE /api/v1/account/keys/{key_id}
```

**Authentication:** Requires Clerk session authentication.

**Example:**

```bash
curl -X DELETE https://app.bigbeautifulscreens.com/api/v1/account/keys/ak_id_abc123 \
  -H "Authorization: Bearer {clerk_token}"
```

**Response:**

```json
{
  "success": true,
  "message": "Account API key deleted"
}
```

## Using Account Keys

Once created, use account keys in the `X-API-Key` header for account-level operations:

### List Your Screens

```bash
curl https://app.bigbeautifulscreens.com/api/v1/screens \
  -H "X-API-Key: ak_your_account_key"
```

### Create a Screen

```bash
curl -X POST https://app.bigbeautifulscreens.com/api/v1/screens \
  -H "X-API-Key: ak_your_account_key"
```

### List Templates

```bash
curl https://app.bigbeautifulscreens.com/api/v1/templates \
  -H "X-API-Key: ak_your_account_key"
```

### Create a Theme

```bash
curl -X POST https://app.bigbeautifulscreens.com/api/v1/themes \
  -H "X-API-Key: ak_your_account_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-custom-theme",
    "display_name": "My Custom Theme",
    "background_color": "#1a1a2e",
    "panel_color": "#16213e",
    "font_color": "#eaeaea"
  }'
```

## Account Key vs Screen Key

Use the appropriate key type for each operation:

| Operation | Key Type | Example |
|-----------|----------|---------|
| List all screens | Account (`ak_`) | `GET /api/v1/screens` |
| Create a screen | Account (`ak_`) | `POST /api/v1/screens` |
| Send message to screen | Screen (`sk_`) | `POST /api/v1/screens/{id}/message` |
| Update screen settings | Screen (`sk_`) | `PATCH /api/v1/screens/{id}` |
| Delete a screen | Screen (`sk_`) | `DELETE /api/v1/screens/{id}` |
| List templates | Account (`ak_`) | `GET /api/v1/templates` |
| Create template | Account (`ak_`) | `POST /api/v1/templates` |
| List themes | Public | `GET /api/v1/themes` |
| Create theme | Account (`ak_`) | `POST /api/v1/themes` |
| Upload media | Account (`ak_`) | `POST /api/v1/media/upload` |

## MCP Integration Example

Account keys are designed for MCP (Model Context Protocol) integration. Here's an example MCP tool configuration:

```json
{
  "name": "big-beautiful-screens",
  "description": "Manage display screens",
  "authentication": {
    "type": "api_key",
    "header": "X-API-Key",
    "key": "ak_your_account_key"
  },
  "tools": [
    {
      "name": "list_screens",
      "description": "List all screens",
      "endpoint": "GET /api/v1/screens"
    },
    {
      "name": "create_screen",
      "description": "Create a new screen",
      "endpoint": "POST /api/v1/screens"
    }
  ]
}
```

## Error Responses

| Status | Description |
|--------|-------------|
| 401 | Invalid, expired, or missing API key |
| 403 | Account keys not available (self-hosted mode) |
| 404 | Key not found or belongs to another user |
| 422 | Invalid request body |

## Security Best Practices

1. **Use descriptive names** - Name keys by their purpose (e.g., "MCP Server", "CI/CD Pipeline")
2. **Set expiration dates** - Use `expires_in_days` for temporary integrations
3. **Rotate keys regularly** - Delete old keys and create new ones periodically
4. **Monitor usage** - Check `last_used_at` to identify unused keys
5. **Principle of least privilege** - Create separate keys for different integrations
