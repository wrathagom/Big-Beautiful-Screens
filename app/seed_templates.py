"""System template seed data for Big Beautiful Screens.

Contains predefined templates for various use cases that are seeded
on first application startup.
"""

from .utils import generate_template_thumbnail


def get_system_templates() -> list[dict]:
    """Generate all system templates with their configurations.

    Returns a list of template dicts ready for insertion into the database.
    """
    templates = []

    # Restaurant templates
    templates.extend(_get_restaurant_templates())

    # IT/Tech templates
    templates.extend(_get_it_tech_templates())

    # Small Business templates
    templates.extend(_get_small_business_templates())

    # Education templates
    templates.extend(_get_education_templates())

    # Healthcare templates
    templates.extend(_get_healthcare_templates())

    # Generate thumbnails for all templates
    for template in templates:
        template["thumbnail_url"] = generate_template_thumbnail(template["configuration"])

    return templates


def _get_restaurant_templates() -> list[dict]:
    """Restaurant category templates."""
    return [
        {
            "name": "Menu Board",
            "description": "Classic digital menu board with sections for different food categories",
            "category": "restaurant",
            "configuration": {
                "background_color": "#1a0f00",
                "panel_color": "#2d1f10",
                "font_color": "#f5e6d3",
                "gap": 12,
                "border_radius": 8,
                "pages": [
                    {
                        "name": "Menu",
                        "layout": "3",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "# Appetizers\n\n- Garlic Bread $5\n- Wings $12\n- Soup of the Day $6",
                            },
                            {
                                "type": "markdown",
                                "value": "# Main Courses\n\n- Grilled Salmon $24\n- Ribeye Steak $32\n- Pasta Primavera $18",
                            },
                            {
                                "type": "markdown",
                                "value": "# Desserts\n\n- Cheesecake $8\n- Ice Cream $5\n- Tiramisu $9",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
        {
            "name": "Daily Specials",
            "description": "Highlight today's specials with featured images and prices",
            "category": "restaurant",
            "configuration": {
                "background_color": "#0d1117",
                "panel_color": "#161b22",
                "font_color": "#e6edf3",
                "gap": 16,
                "border_radius": 12,
                "pages": [
                    {
                        "name": "Specials",
                        "layout": "1-2",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "# Today's Specials\n\n*Fresh ingredients, exceptional taste*",
                            },
                            {
                                "type": "markdown",
                                "value": "## Lunch Special\n**Chef's Salad**\n$12.99",
                            },
                            {
                                "type": "markdown",
                                "value": "## Dinner Special\n**Prime Rib**\n$29.99",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
    ]


def _get_it_tech_templates() -> list[dict]:
    """IT/Tech category templates."""
    return [
        {
            "name": "System Status Dashboard",
            "description": "Monitor system health with status indicators and metrics",
            "category": "it_tech",
            "configuration": {
                "background_color": "#0a0a0f",
                "panel_color": "#12121a",
                "font_color": "#00ff88",
                "gap": 8,
                "border_radius": 4,
                "pages": [
                    {
                        "name": "Status",
                        "layout": "4",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "## API Server\n\n**Status:** Online\n\nUptime: 99.9%",
                            },
                            {
                                "type": "markdown",
                                "value": "## Database\n\n**Status:** Online\n\nConnections: 42",
                            },
                            {
                                "type": "markdown",
                                "value": "## Cache\n\n**Status:** Online\n\nHit Rate: 94%",
                            },
                            {
                                "type": "markdown",
                                "value": "## Queue\n\n**Status:** Online\n\nPending: 12",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
        {
            "name": "DevOps Metrics",
            "description": "Display CI/CD pipeline status and deployment metrics",
            "category": "it_tech",
            "configuration": {
                "background_color": "#1a1b26",
                "panel_color": "#24283b",
                "font_color": "#a9b1d6",
                "gap": 10,
                "border_radius": 6,
                "pages": [
                    {
                        "name": "Pipeline",
                        "layout": "2-1",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "## Build Status\n\nProduction: Passing\nStaging: Passing\nDev: Running",
                            },
                            {
                                "type": "markdown",
                                "value": "## Deployments\n\nLast Deploy: 2h ago\nVersion: v2.4.1",
                            },
                            {
                                "type": "markdown",
                                "value": "# Current Sprint Progress\n\nCompleted: 15/20 tasks | 75%",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
        {
            "name": "Network Monitor",
            "description": "Real-time network traffic and connectivity status",
            "category": "it_tech",
            "configuration": {
                "background_color": "#000000",
                "panel_color": "#0f0f0f",
                "font_color": "#33ff33",
                "font_family": "monospace",
                "gap": 6,
                "border_radius": 2,
                "pages": [
                    {
                        "name": "Network",
                        "layout": "sidebar",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "## Uplinks\n\n```\nISP1: OK\nISP2: OK\nVPN: OK\n```",
                            },
                            {
                                "type": "markdown",
                                "value": "# Network Traffic\n\nIn: 245 Mbps\nOut: 128 Mbps\n\nActive Connections: 1,247",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
    ]


def _get_small_business_templates() -> list[dict]:
    """Small Business category templates."""
    return [
        {
            "name": "Welcome Display",
            "description": "Professional welcome screen for lobbies and reception areas",
            "category": "small_business",
            "configuration": {
                "background_color": "#1e3a5f",
                "panel_color": "#2a4a6f",
                "font_color": "#ffffff",
                "gap": 20,
                "border_radius": 12,
                "pages": [
                    {
                        "name": "Welcome",
                        "layout": "1-2",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "# Welcome to Our Office\n\n*We're glad you're here*",
                            },
                            {
                                "type": "widget",
                                "widget_type": "clock",
                                "widget_config": {"format": "12h"},
                            },
                            {
                                "type": "widget",
                                "widget_type": "weather",
                                "widget_config": {"location": "auto"},
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
        {
            "name": "Announcement Board",
            "description": "Share company news and announcements with staff",
            "category": "small_business",
            "configuration": {
                "background_color": "#2d3436",
                "panel_color": "#3d4446",
                "font_color": "#dfe6e9",
                "gap": 15,
                "border_radius": 8,
                "pages": [
                    {
                        "name": "Announcements",
                        "layout": "2",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "# Company News\n\nQ4 All-Hands Meeting\nFriday at 3pm in the Main Conference Room",
                            },
                            {
                                "type": "markdown",
                                "value": "# Upcoming Events\n\n- Team Lunch - Thursday\n- Training Session - Next Monday\n- Holiday Party - Dec 15",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
    ]


def _get_education_templates() -> list[dict]:
    """Education category templates."""
    return [
        {
            "name": "Class Schedule",
            "description": "Display daily class schedules and room assignments",
            "category": "education",
            "configuration": {
                "background_color": "#1a1a2e",
                "panel_color": "#16213e",
                "font_color": "#eaeaea",
                "gap": 10,
                "border_radius": 8,
                "pages": [
                    {
                        "name": "Schedule",
                        "layout": "3",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "## Morning\n\n8:00 - Math 101\n9:30 - English\n11:00 - Science",
                            },
                            {
                                "type": "markdown",
                                "value": "## Afternoon\n\n1:00 - History\n2:30 - Art\n4:00 - P.E.",
                            },
                            {
                                "type": "markdown",
                                "value": "## Room Info\n\nMath: Room 201\nEnglish: Room 105\nScience: Lab A",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
        {
            "name": "Campus Info Board",
            "description": "General campus information and event announcements",
            "category": "education",
            "configuration": {
                "background_color": "#0f4c75",
                "panel_color": "#1b5f85",
                "font_color": "#bbe1fa",
                "gap": 12,
                "border_radius": 10,
                "pages": [
                    {
                        "name": "Campus",
                        "layout": "1-3",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "# Campus Announcements\n\n*Stay informed about what's happening*",
                            },
                            {
                                "type": "widget",
                                "widget_type": "clock",
                                "widget_config": {"format": "12h"},
                            },
                            {
                                "type": "markdown",
                                "value": "## Library Hours\n\nMon-Fri: 8am-9pm\nSat: 10am-6pm",
                            },
                            {
                                "type": "markdown",
                                "value": "## Cafeteria\n\nLunch: 11am-2pm\nDinner: 5pm-8pm",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
    ]


def _get_healthcare_templates() -> list[dict]:
    """Healthcare category templates."""
    return [
        {
            "name": "Waiting Room Display",
            "description": "Patient-friendly display for waiting areas",
            "category": "healthcare",
            "configuration": {
                "background_color": "#e8f4f8",
                "panel_color": "#ffffff",
                "font_color": "#2c3e50",
                "gap": 15,
                "border_radius": 12,
                "pages": [
                    {
                        "name": "Welcome",
                        "layout": "2-1",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "# Welcome\n\nPlease check in at the front desk.\nWe'll call your name when ready.",
                            },
                            {
                                "type": "widget",
                                "widget_type": "clock",
                                "widget_config": {"format": "12h"},
                            },
                            {
                                "type": "markdown",
                                "value": "## Health Tip of the Day\n\nStay hydrated! Aim for 8 glasses of water daily.",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
        {
            "name": "Clinic Hours & Services",
            "description": "Display clinic hours and available services",
            "category": "healthcare",
            "configuration": {
                "background_color": "#1a5276",
                "panel_color": "#21618c",
                "font_color": "#d4e6f1",
                "gap": 12,
                "border_radius": 8,
                "pages": [
                    {
                        "name": "Services",
                        "layout": "sidebar",
                        "content": [
                            {
                                "type": "markdown",
                                "value": "## Hours\n\nMon-Fri\n8am - 6pm\n\nSat\n9am - 2pm\n\nSun\nClosed",
                            },
                            {
                                "type": "markdown",
                                "value": "# Our Services\n\n- Primary Care\n- Pediatrics\n- Lab Services\n- Immunizations\n- Wellness Checks\n\n**Walk-ins Welcome**",
                            },
                        ],
                        "display_order": 0,
                    }
                ],
            },
        },
    ]
