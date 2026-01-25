"""Visual regression tests for screen layouts.

These tests verify that screen layouts render consistently across code changes.
Screenshots are stored in tests/e2e/screenshots/ and compared against baseline.
"""

import httpx
import pytest
from playwright.sync_api import Page, expect

# Time to wait for "Connected" notification to disappear (2s display + buffer)
NOTIFICATION_HIDE_WAIT = 2500


class TestLayoutVisualRegression:
    """Visual regression tests for different layout presets."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def send_content(
        self,
        app_server: str,
        screen_id: str,
        api_key: str,
        content: list,
        layout: str | None = None,
        **kwargs,
    ):
        """Send content to a screen."""
        payload = {"content": content, **kwargs}
        if layout:
            payload["layout"] = layout

        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=payload,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear and content to stabilize."""
        # Wait for notification to hide (shows for 2s after connect)
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)
        # Verify notification is hidden
        expect(page.locator("#connection-status")).not_to_have_class("visible")

    def test_auto_layout_4_items(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test auto layout with 4 content items."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Panel 1", "Panel 2", "Panel 3", "Panel 4"],
            layout="auto",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "auto_layout_4_items.png")

    def test_grid_2x2_layout(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test 2x2 grid layout."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Top Left", "Top Right", "Bottom Left", "Bottom Right"],
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "grid_2x2_layout.png")

    def test_grid_3x3_layout(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test 3x3 grid layout."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[f"Panel {i}" for i in range(1, 10)],
            layout="grid-3x3",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "grid_3x3_layout.png")

    def test_vertical_layout(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test vertical (single column) layout."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Row 1", "Row 2", "Row 3", "Row 4"],
            layout="vertical",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "vertical_layout.png")

    def test_horizontal_layout(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test horizontal (single row) layout."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Col 1", "Col 2", "Col 3", "Col 4"],
            layout="horizontal",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "horizontal_layout.png")

    def test_dashboard_header_layout(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test dashboard layout with full-width header."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                "Dashboard Header",
                "Widget 1",
                "Widget 2",
                "Widget 3",
                "Widget 4",
                "Widget 5",
                "Widget 6",
            ],
            layout="dashboard-header",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "dashboard_header_layout.png")

    def test_sidebar_left_layout(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test sidebar left layout."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Sidebar", "Main Content"],
            layout="sidebar-left",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "sidebar_left_layout.png")

    def test_menu_board_layout(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test menu board layout with header and items."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                "Today's Menu",
                "Appetizers",
                "$12",
                "Main Course",
                "$25",
                "Desserts",
                "$8",
            ],
            layout="menu-board",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "menu_board_layout.png")


class TestScreenContentRendering:
    """Tests for various content types and rendering."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def send_content(
        self,
        app_server: str,
        screen_id: str,
        api_key: str,
        content: list,
        layout: str | None = None,
        **kwargs,
    ):
        """Send content to a screen."""
        payload = {"content": content, **kwargs}
        if layout:
            payload["layout"] = layout

        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=payload,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)
        expect(page.locator("#connection-status")).not_to_have_class("visible")

    def test_simple_text_content(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test simple text content rendering."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Hello, World!"],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "simple_text_content.png")

    def test_html_content(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test HTML content rendering."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["<h1>Title</h1><p>This is a paragraph with <strong>bold</strong> text.</p>"],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "html_content.png")

    def test_multiple_panels_different_content(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test multiple panels with different content types."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                "<h2>Status</h2><p>All systems operational</p>",
                "Simple text panel",
                "<ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>",
                "<div style='text-align:center'><h1>42</h1><p>Active users</p></div>",
            ],
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "multiple_content_types.png")


class TestStylingVisualRegression:
    """Visual regression tests for styling properties."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def send_content(
        self,
        app_server: str,
        screen_id: str,
        api_key: str,
        content: list,
        **kwargs,
    ):
        """Send content to a screen with styling options."""
        payload = {"content": content, **kwargs}

        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=payload,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)
        expect(page.locator("#connection-status")).not_to_have_class("visible")

    def test_custom_font_family(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test custom serif font family."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Georgia Serif Font", "Second Panel"],
            layout="grid-2x2",
            font_family="Georgia, serif",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_font_family.png")

    def test_custom_font_color(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test custom bright red font color."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Red Text", "Second Panel"],
            layout="grid-2x2",
            font_color="#ff3333",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_font_color.png")

    def test_custom_panel_color(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test custom blue panel color."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Blue Panel 1", "Blue Panel 2"],
            layout="grid-2x2",
            panel_color="#3366cc",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_panel_color.png")

    def test_custom_background_color(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test custom dark red background color."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Panel 1", "Panel 2"],
            layout="grid-2x2",
            background_color="#661111",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_background_color.png")

    def test_gradient_background(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test linear gradient background."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Gradient BG 1", "Gradient BG 2"],
            layout="grid-2x2",
            background_color="linear-gradient(135deg, #667eea, #764ba2)",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_gradient_background.png")

    def test_custom_border_radius(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test large 30px border radius."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Rounded 1", "Rounded 2", "Rounded 3", "Rounded 4"],
            layout="grid-2x2",
            border_radius="30px",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_border_radius.png")

    def test_custom_gap(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test large 50px gap between panels."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Gap 1", "Gap 2", "Gap 3", "Gap 4"],
            layout="grid-2x2",
            gap="50px",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_gap.png")

    def test_custom_panel_shadow(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test prominent drop shadow on panels."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Shadow 1", "Shadow 2", "Shadow 3", "Shadow 4"],
            layout="grid-2x2",
            panel_shadow="8px 8px 20px rgba(0,0,0,0.5)",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_panel_shadow.png")

    def test_no_gap_no_radius(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test edge-to-edge panels with no gap or border radius."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Edge 1", "Edge 2", "Edge 3", "Edge 4"],
            layout="grid-2x2",
            gap="0",
            border_radius="0",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_no_gap_no_radius.png")

    def test_combined_styling(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test all styling options combined."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Combined 1", "Combined 2", "Combined 3", "Combined 4"],
            layout="grid-2x2",
            background_color="linear-gradient(180deg, #1a1a2e, #16213e)",
            panel_color="rgba(30, 30, 50, 0.8)",
            font_family="'Courier New', monospace",
            font_color="#00ff88",
            gap="20px",
            border_radius="15px",
            panel_shadow="0 4px 15px rgba(0,255,136,0.2)",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "styling_combined.png")


class TestThemeVisualRegression:
    """Visual regression tests for built-in themes."""

    # All built-in themes to test
    THEMES = [
        "default",
        "minimal",
        "elegant",
        "modern",
        "mono",
        "catppuccin-mocha",
        "catppuccin-latte",
        "solarized-dark",
        "solarized-light",
        "dracula",
        "nord",
        "gruvbox-dark",
        "tokyo-night",
    ]

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def set_theme(self, app_server: str, screen_id: str, api_key: str, theme_name: str):
        """Set a theme on a screen using PATCH endpoint."""
        with httpx.Client() as client:
            response = client.patch(
                f"{app_server}/api/v1/screens/{screen_id}",
                headers={"X-API-Key": api_key},
                json={"theme": theme_name},
            )
            assert response.status_code == 200
            return response.json()

    def send_content(
        self,
        app_server: str,
        screen_id: str,
        api_key: str,
        content: list,
        **kwargs,
    ):
        """Send content to a screen."""
        payload = {"content": content, **kwargs}

        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=payload,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)
        expect(page.locator("#connection-status")).not_to_have_class("visible")

    @pytest.mark.parametrize("theme_name", THEMES)
    def test_theme(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot, theme_name: str
    ):
        """Test each built-in theme renders correctly."""
        # First set the theme via PATCH
        self.set_theme(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            theme_name,
        )

        # Then send content
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                f"Theme: {theme_name}",
                "Panel Two",
                "Panel Three",
                "Panel Four",
            ],
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, f"theme_{theme_name}.png")


class TestScreenBasicFunctionality:
    """Basic functionality tests for screen display (non-visual)."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def test_screen_page_loads(self, page: Page, app_server: str, screen_data: dict):
        """Test that the screen page loads successfully."""
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")

        # Page should load without errors
        expect(page.locator("body")).to_be_visible()

    def test_nonexistent_screen_shows_404(self, page: Page, app_server: str):
        """Test that a nonexistent screen returns 404."""
        response = page.goto(f"{app_server}/screen/nonexistent123")
        assert response.status == 404

    def test_screen_updates_via_websocket(self, page: Page, app_server: str, screen_data: dict):
        """Test that screen content updates via WebSocket."""
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        page.wait_for_timeout(500)

        # Send content
        with httpx.Client() as client:
            client.post(
                f"{app_server}/api/v1/screens/{screen_data['screen_id']}/message",
                headers={"X-API-Key": screen_data["api_key"]},
                json={"content": ["WebSocket Test Content"]},
            )

        # Wait for WebSocket update
        page.wait_for_timeout(1000)

        # Content should be visible
        expect(page.locator("text=WebSocket Test Content")).to_be_visible()


class TestAdditionalLayouts:
    """Additional visual regression tests for layout presets."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def send_content(
        self,
        app_server: str,
        screen_id: str,
        api_key: str,
        content: list,
        layout=None,
        **kwargs,
    ):
        """Send content to a screen."""
        payload = {"content": content, **kwargs}
        if layout:
            payload["layout"] = layout

        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=payload,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)
        expect(page.locator("#connection-status")).not_to_have_class("visible")

    def test_grid_4x4_layout(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test 4x4 grid layout with 16 panels."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[f"Panel {i}" for i in range(1, 17)],
            layout="grid-4x4",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "layout_grid_4x4.png")

    def test_dashboard_footer_layout(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test dashboard layout with footer."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                "Widget 1",
                "Widget 2",
                "Widget 3",
                "Widget 4",
                "Widget 5",
                "Widget 6",
                "Dashboard Footer",
            ],
            layout="dashboard-footer",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "layout_dashboard_footer.png")

    def test_sidebar_right_layout(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test sidebar right layout."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Main Content", "Sidebar"],
            layout="sidebar-right",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "layout_sidebar_right.png")

    def test_featured_top_layout(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test featured top layout with large header."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                "Featured Header",
                "Small Panel 1",
                "Small Panel 2",
                "Small Panel 3",
            ],
            layout="featured-top",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "layout_featured_top.png")

    def test_custom_column_widths(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test custom column widths with 1fr 2fr 1fr."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Narrow Left", "Wide Center", "Narrow Right"],
            layout={"columns": "1fr 2fr 1fr"},
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "layout_custom_columns.png")

    def test_custom_rows(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test custom row heights with auto 1fr 1fr auto."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Header (auto)", "Content Row 1", "Content Row 2", "Footer (auto)"],
            layout={"rows": "auto 1fr 1fr auto", "columns": 1},
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "layout_custom_rows.png")
