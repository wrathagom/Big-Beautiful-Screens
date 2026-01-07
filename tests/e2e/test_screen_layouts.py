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

        assert_snapshot(page.screenshot(), "auto_layout_4_items.png")

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

        assert_snapshot(page.screenshot(), "grid_2x2_layout.png")

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

        assert_snapshot(page.screenshot(), "grid_3x3_layout.png")

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

        assert_snapshot(page.screenshot(), "vertical_layout.png")

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

        assert_snapshot(page.screenshot(), "horizontal_layout.png")

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

        assert_snapshot(page.screenshot(), "dashboard_header_layout.png")

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

        assert_snapshot(page.screenshot(), "sidebar_left_layout.png")

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

        assert_snapshot(page.screenshot(), "menu_board_layout.png")


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

        assert_snapshot(page.screenshot(), "simple_text_content.png")

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

        assert_snapshot(page.screenshot(), "html_content.png")

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

        assert_snapshot(page.screenshot(), "multiple_content_types.png")


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


# Fixture for snapshot testing
@pytest.fixture
def assert_snapshot(request):
    """Fixture for visual snapshot comparison.

    Usage:
        def test_example(page, assert_snapshot):
            assert_snapshot(page.screenshot(), "test_name.png")
    """
    from pathlib import Path

    screenshots_dir = Path(__file__).parent / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    def _assert_snapshot(image_bytes: bytes, name: str):
        """Compare screenshot against baseline or create new baseline."""
        baseline_path = screenshots_dir / name

        if baseline_path.exists():
            # Compare against existing baseline
            baseline_bytes = baseline_path.read_bytes()
            if image_bytes != baseline_bytes:
                # Save the new screenshot for comparison
                new_path = screenshots_dir / f"new_{name}"
                new_path.write_bytes(image_bytes)
                pytest.fail(
                    f"Screenshot '{name}' differs from baseline. "
                    f"New screenshot saved to {new_path}. "
                    f"If the change is expected, replace {baseline_path} with {new_path}."
                )
        else:
            # Create new baseline
            baseline_path.write_bytes(image_bytes)
            print(f"Created new baseline screenshot: {baseline_path}")

    return _assert_snapshot
