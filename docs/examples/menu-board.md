# Menu Board Example

Create a digital menu board for a restaurant or cafe.

## Single Page Menu

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Breakfast\n\n- Eggs Benedict $12\n- Pancakes $9\n- Avocado Toast $11"},
      {"type": "markdown", "value": "# Lunch\n\n- Club Sandwich $14\n- Caesar Salad $12\n- Soup of the Day $8"},
      {"type": "markdown", "value": "# Drinks\n\n- Coffee $4\n- Fresh Juice $6\n- Smoothie $7"}
    ],
    "background_color": "#1a1a2e",
    "panel_color": "#16213e",
    "font_family": "Georgia, serif",
    "font_color": "#f5f5f5"
  }'
```

## Multi-Page Rotating Menu

### Setup

```bash
# Enable rotation with 15 second interval
curl -X PATCH http://localhost:8000/api/v1/screens/abc123 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "rotation_enabled": true,
    "rotation_interval": 15,
    "background_color": "#2c1810",
    "panel_color": "#3d241a",
    "font_family": "Georgia, serif",
    "font_color": "#f5e6d3"
  }'
```

### Food Menu Page

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/pages/default \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Main Menu\n\n## Burgers\n- Classic $12\n- Bacon $14\n- Veggie $11"},
      {"type": "markdown", "value": "## Sides\n- Fries $5\n- Onion Rings $6\n- Coleslaw $4"},
      {"type": "markdown", "value": "## Combos\n\nAny burger + side + drink\n\n# $16"}
    ]
  }'
```

### Drinks Page

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/pages/drinks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Drinks\n\n## Soft Drinks $3\nCoke, Sprite, Fanta\n\n## Iced Tea $4\nSweetened or Unsweetened"},
      {"type": "markdown", "value": "## Craft Beer $7\n- Local IPA\n- Wheat Ale\n- Stout"},
      {"type": "image", "url": "https://example.com/drinks.jpg", "image_mode": "cover"}
    ]
  }'
```

### Daily Specials Page

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/pages/specials \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Today'\''s Special\n\n## BBQ Brisket Sandwich\n\nSlow-smoked brisket with tangy slaw on brioche\n\n# $15"}
    ],
    "panel_color": "#4a3728",
    "duration": 10
  }'
```

## Food Truck Menu

Compact single-screen menu for limited space:

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Tacos\n- Carnitas $4\n- Chicken $4\n- Fish $5\n- Veggie $3.50"},
      {"type": "markdown", "value": "# Burritos\n- Regular $9\n- Super $12\n\n# Bowls $10"}
    ],
    "gap": "0.5rem",
    "background_color": "#1a472a",
    "panel_color": "#2d5a3d",
    "font_color": "#f0f0f0"
  }'
```

## Coffee Shop Menu

```bash
curl -X POST http://localhost:8000/api/v1/screens/abc123/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_api_key" \
  -d '{
    "content": [
      {"type": "markdown", "value": "# Espresso\n\n| | S | M | L |\n|---|---|---|---|\n| Latte | $4 | $5 | $6 |\n| Cappuccino | $4 | $5 | $6 |\n| Americano | $3 | $4 | $5 |"},
      {"type": "markdown", "value": "# Cold Drinks\n\n- Cold Brew $5\n- Iced Latte $5.50\n- Frappe $6"},
      {"type": "markdown", "value": "# Pastries\n\n- Croissant $4\n- Muffin $3.50\n- Scone $3"}
    ],
    "theme": "catppuccin-latte"
  }'
```

## Dynamic Pricing

Update prices from your POS system:

```python
import requests

MENU_DATA = {
    "burgers": [
        ("Classic Burger", 12.99),
        ("Bacon Burger", 14.99),
        ("Veggie Burger", 11.99),
    ],
    "sides": [
        ("Fries", 4.99),
        ("Onion Rings", 5.99),
    ]
}

def format_menu(items):
    return "\n".join([f"- {name} ${price:.2f}" for name, price in items])

requests.post(
    "http://localhost:8000/api/v1/screens/abc123/message",
    headers={"X-API-Key": "sk_your_key"},
    json={
        "content": [
            {"type": "markdown", "value": f"# Burgers\n\n{format_menu(MENU_DATA['burgers'])}"},
            {"type": "markdown", "value": f"# Sides\n\n{format_menu(MENU_DATA['sides'])}"}
        ]
    }
)
```
