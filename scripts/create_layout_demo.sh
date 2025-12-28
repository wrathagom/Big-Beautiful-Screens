#!/bin/bash
#
# Create a demo screen that rotates through all layout presets and custom examples.
#
# Usage:
#   ./scripts/create_layout_demo.sh [BASE_URL]
#
# Examples:
#   ./scripts/create_layout_demo.sh                          # Uses http://localhost:8000
#   ./scripts/create_layout_demo.sh https://screens.example.com
#
# The script will:
#   1. Create a new screen
#   2. Add pages demonstrating each layout preset
#   3. Add custom layout examples
#   4. Enable rotation (5 second interval)
#   5. Print the screen URL and API key

set -e

BASE_URL="${1:-http://localhost:8000}"

echo "Creating layout demo screen on $BASE_URL..."
echo ""

# Create the screen
RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/screens")
SCREEN_ID=$(echo "$RESPONSE" | jq -r '.screen_id')
API_KEY=$(echo "$RESPONSE" | jq -r '.api_key')
SCREEN_URL=$(echo "$RESPONSE" | jq -r '.screen_url')

if [ "$SCREEN_ID" = "null" ] || [ -z "$SCREEN_ID" ]; then
    echo "Error: Failed to create screen"
    echo "$RESPONSE"
    exit 1
fi

echo "Created screen: $SCREEN_ID"
echo ""

# Helper function to create a page
create_page() {
    local name="$1"
    local data="$2"

    result=$(curl -s -X POST "$BASE_URL/api/v1/screens/$SCREEN_ID/pages/$name" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$data" | jq -r '.success')

    if [ "$result" = "true" ]; then
        echo "  + $name"
    else
        echo "  ! Failed: $name"
    fi
}

echo "Creating preset layout pages..."

# Vertical layouts
create_page "vertical" '{
    "content": ["# Vertical Layout", "Single column with auto rows", "Item 2", "Item 3", "Item 4", "Item 5"],
    "layout": "vertical"
}'

create_page "vertical-12" '{
    "content": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
    "layout": "vertical-12"
}'

# Horizontal layout
create_page "horizontal" '{
    "content": ["# H1", "# H2", "# H3", "# H4"],
    "layout": "horizontal"
}'

# Grid layouts
create_page "grid-2x2" '{
    "content": ["# Grid 2x2", "Panel A", "Panel B", "Panel C"],
    "layout": "grid-2x2"
}'

create_page "grid-3x3" '{
    "content": ["# 3x3", "A", "B", "C", "D", "E", "F", "G", "H"],
    "layout": "grid-3x3"
}'

create_page "grid-4x4" '{
    "content": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"],
    "layout": "grid-4x4"
}'

# Dashboard layouts
create_page "dashboard-header" '{
    "content": ["# Dashboard Header", "Metric 1", "Metric 2", "Metric 3", "Chart A", "Chart B", "Chart C"],
    "layout": "dashboard-header"
}'

create_page "dashboard-footer" '{
    "content": ["Data 1", "Data 2", "Data 3", "Info A", "Info B", "Info C", "# Footer"],
    "layout": "dashboard-footer"
}'

create_page "dashboard-both" '{
    "content": ["# Header", "Panel 1", "Panel 2", "Panel 3", "Panel 4", "Panel 5", "Panel 6", "# Footer"],
    "layout": "dashboard-both"
}'

# Menu/Schedule layouts
create_page "menu-board" '{
    "content": ["# Menu", "Burger - $8", "Pizza - $12", "Salad - $6", "Fries - $4", "Soda - $2", "Dessert - $5"],
    "layout": "menu-board"
}'

create_page "schedule" '{
    "content": ["# Schedule", "9:00 - Meeting", "10:00 - Review", "11:00 - Lunch", "12:00 - Workshop", "13:00 - Demo", "14:00 - Break"],
    "layout": "schedule"
}'

# Sidebar layouts
create_page "sidebar-left" '{
    "content": ["# Nav", "# Main Content Area"],
    "layout": "sidebar-left"
}'

create_page "sidebar-right" '{
    "content": ["# Main Content", "# Sidebar"],
    "layout": "sidebar-right"
}'

create_page "featured-top" '{
    "content": ["# Featured (2x height)", "Small 1", "Small 2", "Small 3"],
    "layout": "featured-top"
}'

echo ""
echo "Creating custom layout pages..."

# Custom: Asymmetric columns
create_page "custom-asymmetric" '{
    "content": ["# Left", "# Center (2x)", "# Right"],
    "layout": {"columns": "1fr 2fr 1fr", "rows": 1}
}'

# Custom: Mixed row heights
create_page "custom-mixed-heights" '{
    "content": ["# Title (auto)", "Main A", "Main B", "Main C", "Small 1", "Small 2", "Small 3"],
    "layout": {"columns": 3, "rows": "auto 2fr 1fr", "header_rows": 1}
}'

# Custom: Spanning panels
create_page "custom-spanning" '{
    "content": [
        {"type": "markdown", "value": "# Full Width Title", "grid_column": "1 / -1"},
        {"type": "markdown", "value": "# Large\n\n2x2 span", "grid_column": "span 2", "grid_row": "span 2"},
        {"type": "text", "value": "Small 1"},
        {"type": "text", "value": "Small 2"},
        {"type": "markdown", "value": "# Bottom Full Width", "grid_column": "1 / -1"}
    ],
    "layout": {"columns": 3, "rows": "auto 1fr 1fr auto"}
}'

# Custom: 5-column grid
create_page "custom-5col" '{
    "content": ["# 5-Column", "A", "B", "C", "D", "E", "F", "G", "H", "I"],
    "layout": {"columns": 5, "rows": "auto 1fr 1fr", "header_rows": 1}
}'

# Custom: Golden ratio
create_page "custom-golden" '{
    "content": ["# Sidebar\n\n(1fr)", "# Main\n\n(1.618fr - Golden Ratio)"],
    "layout": {"columns": "1fr 1.618fr"}
}'

# Custom: Dashboard with widgets
create_page "custom-widgets" '{
    "content": [
        {"type": "markdown", "value": "# Widget Dashboard", "grid_column": "1 / -1"},
        {"type": "widget", "widget_type": "clock", "widget_config": {"style": "digital", "show_seconds": true}},
        {"type": "widget", "widget_type": "chart", "widget_config": {"chart_type": "line", "labels": ["Mon","Tue","Wed","Thu","Fri"], "values": [65,72,68,80,75], "label": "CPU %", "color": "#89b4fa"}},
        {"type": "widget", "widget_type": "chart", "widget_config": {"chart_type": "bar", "labels": ["A","B","C","D"], "values": [30,50,40,60], "color": "#a6e3a1"}},
        {"type": "markdown", "value": "**Status:** All systems operational", "grid_column": "1 / -1"}
    ],
    "layout": {"columns": 3, "rows": "auto 1fr auto", "header_rows": 1, "footer_rows": 1}
}'

# Custom: Complex multi-span
create_page "custom-complex" '{
    "content": [
        {"type": "markdown", "value": "# Complex Layout Demo", "grid_column": "1 / -1"},
        {"type": "text", "value": "Wide Left", "grid_column": "span 2"},
        {"type": "text", "value": "Right"},
        {"type": "text", "value": "Tall", "grid_row": "span 2"},
        {"type": "text", "value": "Center"},
        {"type": "text", "value": "Bottom", "grid_column": "span 2"}
    ],
    "layout": {"columns": 3, "rows": "auto 1fr 1fr 1fr"}
}'

echo ""
echo "Enabling rotation..."

# Enable rotation with theme
curl -s -X PATCH "$BASE_URL/api/v1/screens/$SCREEN_ID" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{"rotation_enabled": true, "rotation_interval": 5, "theme": "catppuccin-mocha"}' > /dev/null

# Delete the default page
curl -s -X DELETE "$BASE_URL/api/v1/screens/$SCREEN_ID/pages/default" \
    -H "X-API-Key: $API_KEY" > /dev/null 2>&1 || true

echo ""
echo "=========================================="
echo "Layout Demo Screen Created!"
echo "=========================================="
echo ""
echo "Screen URL: $BASE_URL$SCREEN_URL"
echo "API Key:    $API_KEY"
echo ""
echo "The screen will rotate through all layouts every 5 seconds."
echo ""
echo "To adjust rotation speed:"
echo "  curl -X PATCH '$BASE_URL/api/v1/screens/$SCREEN_ID' \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -H 'X-API-Key: $API_KEY' \\"
echo "    -d '{\"rotation_interval\": 10}'"
echo ""
