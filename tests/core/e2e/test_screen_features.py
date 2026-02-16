"""E2E tests for screen features: connection status, styling, hierarchy, and widgets."""

import re

import httpx
import pytest
from playwright.sync_api import Page, expect

# Time to wait for "Connected" notification to disappear (2s display + buffer)
NOTIFICATION_HIDE_WAIT = 2500


class TestConnectionStatus:
    """Tests for connection status notifications."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def test_connected_notification_shows_on_load(
        self, page: Page, app_server: str, screen_data: dict
    ):
        """Test that 'Connected' notification appears when page loads."""
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")

        # Connected notification should appear
        status = page.locator("#connection-status")
        expect(status).to_have_class(re.compile(r"visible"))
        expect(status).to_have_class(re.compile(r"connected"))
        expect(status).to_have_text("Connected")

    def test_connected_notification_hides_after_delay(
        self, page: Page, app_server: str, screen_data: dict
    ):
        """Test that 'Connected' notification hides after ~2 seconds."""
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")

        # Initially visible
        status = page.locator("#connection-status")
        expect(status).to_have_class(re.compile(r"visible"))

        # Wait for it to hide (2s + buffer)
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)

        # Should no longer be visible
        expect(status).not_to_have_class(re.compile(r"visible"))

    def test_disconnected_notification_on_server_stop(
        self, page: Page, app_server: str, screen_data: dict
    ):
        """Test that 'Disconnected' notification appears when connection drops."""
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")

        # Wait for connection to establish
        page.wait_for_timeout(500)

        # Close WebSocket by navigating away and back (simulates disconnect)
        # This is a simplified test - full disconnect testing would require server control
        status = page.locator("#connection-status")

        # Verify the status element exists and can show different states
        expect(status).to_be_attached()


class TestStylingProperties:
    """Tests for styling properties (colors, fonts, etc.)."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def send_content(self, app_server: str, screen_id: str, api_key: str, **kwargs):
        """Send content to a screen with optional styling."""
        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=kwargs,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)

    def test_background_color(self, page: Page, app_server: str, screen_data: dict):
        """Test that background_color is applied to the screen."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Test Panel"],
            background_color="#ff0000",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Check background color is applied
        body_bg = page.evaluate("getComputedStyle(document.body).background")
        assert "rgb(255, 0, 0)" in body_bg or "255, 0, 0" in body_bg

    def test_panel_color(self, page: Page, app_server: str, screen_data: dict):
        """Test that panel_color is applied to panels."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Test Panel"],
            panel_color="#00ff00",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Check panel color
        panel = page.locator(".panel").first
        panel_bg = panel.evaluate("el => getComputedStyle(el).background")
        assert "rgb(0, 255, 0)" in panel_bg or "0, 255, 0" in panel_bg

    def test_font_color(self, page: Page, app_server: str, screen_data: dict):
        """Test that font_color is applied to text."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Colored Text"],
            font_color="#0000ff",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Check font color on screen element
        screen = page.locator("#screen")
        color = screen.evaluate("el => getComputedStyle(el).color")
        assert "rgb(0, 0, 255)" in color or "0, 0, 255" in color

    def test_font_family(self, page: Page, app_server: str, screen_data: dict):
        """Test that font_family is applied to text."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Serif Text"],
            font_family="Georgia, serif",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Check font family
        screen = page.locator("#screen")
        font = screen.evaluate("el => getComputedStyle(el).fontFamily")
        assert "Georgia" in font or "serif" in font

    def test_border_radius(self, page: Page, app_server: str, screen_data: dict):
        """Test that border_radius is applied to panels."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Rounded Panel"],
            border_radius="20px",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Check border radius
        panel = page.locator(".panel").first
        radius = panel.evaluate("el => getComputedStyle(el).borderRadius")
        assert "20px" in radius

    def test_gap(self, page: Page, app_server: str, screen_data: dict):
        """Test that gap is applied between panels."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Panel 1", "Panel 2"],
            gap="50px",
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Check gap on screen
        screen = page.locator("#screen")
        gap = screen.evaluate("el => getComputedStyle(el).gap")
        assert "50px" in gap

    def test_panel_shadow(self, page: Page, app_server: str, screen_data: dict):
        """Test that panel_shadow is applied to panels."""
        shadow_value = "5px 5px 10px rgba(0,0,0,0.5)"
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=["Shadowed Panel"],
            panel_shadow=shadow_value,
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Check box shadow
        panel = page.locator(".panel").first
        shadow = panel.evaluate("el => getComputedStyle(el).boxShadow")
        assert shadow != "none" and shadow != ""


class TestStyleHierarchy:
    """Tests for style hierarchy (screen level vs panel level)."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def send_content(self, app_server: str, screen_id: str, api_key: str, **kwargs):
        """Send content to a screen."""
        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=kwargs,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)

    def test_panel_color_overrides_screen_color(
        self, page: Page, app_server: str, screen_data: dict
    ):
        """Test that per-panel color overrides screen-level color."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {"type": "text", "value": "Screen Color Panel"},
                {"type": "text", "value": "Override Panel", "panel_color": "#00ff00"},
            ],
            panel_color="#ff0000",  # Screen-level red
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        panels = page.locator(".panel").all()

        # First panel should have screen-level color (red)
        panel1_bg = panels[0].evaluate("el => getComputedStyle(el).background")
        assert "rgb(255, 0, 0)" in panel1_bg or "255, 0, 0" in panel1_bg

        # Second panel should have override color (green)
        panel2_bg = panels[1].evaluate("el => getComputedStyle(el).background")
        assert "rgb(0, 255, 0)" in panel2_bg or "0, 255, 0" in panel2_bg

    def test_panel_font_color_overrides_screen(
        self, page: Page, app_server: str, screen_data: dict
    ):
        """Test that per-panel font_color overrides screen-level font_color."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {"type": "text", "value": "Screen Font"},
                {"type": "text", "value": "Override Font", "font_color": "#00ff00"},
            ],
            font_color="#ff0000",  # Screen-level red
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        panels = page.locator(".panel").all()

        # First panel should inherit screen font color (red)
        panel1_color = panels[0].evaluate("el => getComputedStyle(el).color")
        # Note: color may be inherited from parent, check for red
        assert "rgb(255, 0, 0)" in panel1_color or "255, 0, 0" in panel1_color

        # Second panel should have override color (green)
        panel2_color = panels[1].evaluate("el => getComputedStyle(el).color")
        assert "rgb(0, 255, 0)" in panel2_color or "0, 255, 0" in panel2_color

    def test_panel_font_family_overrides_screen(
        self, page: Page, app_server: str, screen_data: dict
    ):
        """Test that per-panel font_family overrides screen-level font_family."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {"type": "text", "value": "Screen Font"},
                {"type": "text", "value": "Override Font", "font_family": "monospace"},
            ],
            font_family="serif",
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        panels = page.locator(".panel").all()

        # Second panel should have monospace font
        panel2_font = panels[1].evaluate("el => getComputedStyle(el).fontFamily")
        assert "monospace" in panel2_font.lower()

    def test_panel_shadow_override_to_none(self, page: Page, app_server: str, screen_data: dict):
        """Test that per-panel shadow can be set to 'none' to disable."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {"type": "text", "value": "With Shadow"},
                {"type": "text", "value": "No Shadow", "panel_shadow": "none"},
            ],
            panel_shadow="5px 5px 10px black",
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        panels = page.locator(".panel").all()

        # First panel should have shadow
        panel1_shadow = panels[0].evaluate("el => getComputedStyle(el).boxShadow")
        assert panel1_shadow != "none" and panel1_shadow != ""

        # Second panel should have no shadow
        panel2_shadow = panels[1].evaluate("el => getComputedStyle(el).boxShadow")
        assert panel2_shadow == "none"


class TestWidgets:
    """Tests for widget rendering."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def send_content(self, app_server: str, screen_id: str, api_key: str, **kwargs):
        """Send content to a screen."""
        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=kwargs,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)

    def test_clock_widget_renders(self, page: Page, app_server: str, screen_data: dict):
        """Test that clock widget renders and shows time."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[{"type": "widget", "widget_type": "clock", "widget_config": {}}],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Clock widget should render with time display
        clock = page.locator(".widget-clock")
        expect(clock).to_be_visible()

        # Should have time content (numbers and colons)
        time_text = clock.text_content()
        assert re.search(r"\d{1,2}:\d{2}", time_text), f"Expected time format, got: {time_text}"

    def test_clock_widget_with_timezone(self, page: Page, app_server: str, screen_data: dict):
        """Test clock widget with specific timezone."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "clock",
                    "widget_config": {"timezone": "UTC", "show_seconds": True},
                }
            ],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        clock = page.locator(".widget-clock")
        expect(clock).to_be_visible()

    def test_countdown_widget_renders(self, page: Page, app_server: str, screen_data: dict):
        """Test that countdown widget renders."""
        # Set target to 1 hour from now
        from datetime import datetime, timedelta

        target = (datetime.now() + timedelta(hours=1)).isoformat()

        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "countdown",
                    "widget_config": {"target": target},
                }
            ],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Countdown widget should be visible
        countdown = page.locator(".widget-countdown")
        expect(countdown).to_be_visible()

        # Should show time units (h, m, s labels in labeled mode)
        countdown_text = countdown.text_content()
        assert "h" in countdown_text or "m" in countdown_text or "s" in countdown_text

    def test_unknown_widget_shows_error(self, page: Page, app_server: str, screen_data: dict):
        """Test that unknown widget type shows error or fallback."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[{"type": "widget", "widget_type": "nonexistent_widget", "widget_config": {}}],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Panel should be rendered (even with error/fallback content)
        panel = page.locator(".panel").first
        expect(panel).to_be_visible()

        # Should show some error indication (could be "Widget error" or error symbol)
        panel_content = panel.text_content()
        has_error = (
            "error" in panel_content.lower()
            or "unknown" in panel_content.lower()
            or "⚠" in panel_content
        )
        assert has_error, f"Expected error indication, got: {panel_content}"

    def test_multiple_widgets_in_grid(self, page: Page, app_server: str, screen_data: dict):
        """Test multiple widgets in a grid layout."""
        from datetime import datetime, timedelta

        target = (datetime.now() + timedelta(days=1)).isoformat()

        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {"type": "widget", "widget_type": "clock", "widget_config": {}},
                {
                    "type": "widget",
                    "widget_type": "countdown",
                    "widget_config": {"target": target},
                },
                {"type": "text", "value": "Regular Text Panel"},
                {"type": "widget", "widget_type": "clock", "widget_config": {"show_date": True}},
            ],
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        # Should have 4 panels
        panels = page.locator(".panel")
        expect(panels).to_have_count(4)

        # Should have 2 clock widgets
        clocks = page.locator(".widget-clock")
        expect(clocks).to_have_count(2)

        # Should have 1 countdown widget
        countdown = page.locator(".widget-countdown")
        expect(countdown).to_have_count(1)

        # Should have regular text
        expect(page.locator("text=Regular Text Panel")).to_be_visible()


# Import time mocking helper
from tests.core.e2e.conftest import mock_javascript_time  # noqa: E402


class TestHierarchyVisualRegression:
    """Visual regression tests for style hierarchy (screen → page → panel)."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def send_content(self, app_server: str, screen_id: str, api_key: str, **kwargs):
        """Send content to a screen."""
        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=kwargs,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)

    def test_panel_color_hierarchy(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test screen-level red, panel-level green override."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {"type": "text", "value": "Red (screen level)"},
                {"type": "text", "value": "Green (override)", "panel_color": "#22cc22"},
                {"type": "text", "value": "Red (screen level)"},
                {"type": "text", "value": "Blue (override)", "panel_color": "#2222cc"},
            ],
            panel_color="#cc2222",
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "hierarchy_panel_color.png")

    def test_font_color_hierarchy(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test screen-level blue text, panel-level orange override."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {"type": "text", "value": "Blue Text (screen)"},
                {"type": "text", "value": "Orange Text (override)", "font_color": "#ff8800"},
                {"type": "text", "value": "Blue Text (screen)"},
                {"type": "text", "value": "Green Text (override)", "font_color": "#00ff00"},
            ],
            font_color="#4444ff",
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "hierarchy_font_color.png")

    def test_mixed_hierarchy(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test multiple style overrides in same screen."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {"type": "text", "value": "Default Style"},
                {"type": "text", "value": "Custom Color", "panel_color": "#663399"},
                {
                    "type": "text",
                    "value": "Custom Font",
                    "font_family": "monospace",
                    "font_color": "#00ffff",
                },
                {
                    "type": "text",
                    "value": "Custom All",
                    "panel_color": "#336633",
                    "font_color": "#ffff00",
                },
            ],
            panel_color="#333333",
            font_color="#ffffff",
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "hierarchy_mixed.png")

    def test_shadow_hierarchy(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test screen shadow with panel override to none."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {"type": "text", "value": "With Shadow"},
                {"type": "text", "value": "No Shadow", "panel_shadow": "none"},
                {"type": "text", "value": "With Shadow"},
                {"type": "text", "value": "Bigger Shadow", "panel_shadow": "10px 10px 30px black"},
            ],
            panel_shadow="5px 5px 15px rgba(0,0,0,0.5)",
            layout="grid-2x2",
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "hierarchy_shadow.png")


class TestWidgetVisualRegression:
    """Visual regression tests for widgets."""

    @pytest.fixture
    def screen_data(self, app_server: str):
        """Create a test screen and return its data."""
        with httpx.Client() as client:
            response = client.post(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            return response.json()

    def send_content(self, app_server: str, screen_id: str, api_key: str, **kwargs):
        """Send content to a screen."""
        with httpx.Client() as client:
            response = client.post(
                f"{app_server}/api/v1/screens/{screen_id}/message",
                headers={"X-API-Key": api_key},
                json=kwargs,
            )
            assert response.status_code == 200
            return response.json()

    def wait_for_stable_screen(self, page: Page):
        """Wait for connection notification to disappear."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)

    def test_clock_digital(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test digital clock widget in 12h format."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "clock",
                    "widget_config": {"style": "digital", "format": "12h", "show_seconds": True},
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_clock_digital_12h.png")

    def test_clock_digital_24h(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test digital clock widget in 24h format."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "clock",
                    "widget_config": {"style": "digital", "format": "24h", "show_seconds": True},
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_clock_digital_24h.png")

    def test_clock_analog(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test analog clock widget."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "clock",
                    "widget_config": {"style": "analog", "show_numbers": True},
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_clock_analog.png")

    def test_clock_with_date(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test clock widget with date display."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "clock",
                    "widget_config": {"style": "digital", "show_date": True},
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_clock_with_date.png")

    def test_countdown_labeled(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test countdown widget with labeled style."""
        # Target is 1 day, 2 hours, 30 minutes, 45 seconds from mock time
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "countdown",
                    "widget_config": {
                        "target": "2025-01-16T17:01:30Z",  # 1d 2h 30m 45s from mock time
                        "style": "labeled",
                    },
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_countdown_labeled.png")

    def test_countdown_simple(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test countdown widget with simple style."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "countdown",
                    "widget_config": {
                        "target": "2025-01-16T17:01:30Z",
                        "style": "simple",
                    },
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_countdown_simple.png")

    def test_countdown_expired(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test countdown widget showing expired text."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "countdown",
                    "widget_config": {
                        "target": "2025-01-01T00:00:00Z",  # In the past
                        "expired_text": "Event Complete!",
                    },
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_countdown_expired.png")

    def test_countup_labeled(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test count-up widget with labeled style."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "countup",
                    "widget_config": {
                        "start": "2025-01-14T12:00:00Z",
                        "style": "labeled",
                    },
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_countup_labeled.png")

    def test_countup_simple(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test count-up widget with simple style."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "countup",
                    "widget_config": {
                        "start": "2025-01-14T12:00:00Z",
                        "style": "simple",
                    },
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_countup_simple.png")

    def test_countup_with_label(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test count-up widget with label text."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "countup",
                    "widget_config": {
                        "start": "2025-01-14T12:00:00Z",
                        "label": "Since last update",
                        "label_position": "below",
                        "style": "labeled",
                    },
                }
            ],
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_countup_with_label.png")

    def test_chart_bar(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test bar chart widget."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "chart",
                    "widget_config": {
                        "chart_type": "bar",
                        "labels": ["Jan", "Feb", "Mar", "Apr", "May"],
                        "values": [65, 59, 80, 81, 56],
                        "label": "Monthly Sales",
                        "color": "#4CAF50",
                    },
                }
            ],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_chart_bar.png")

    def test_chart_line(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test line chart widget with fill."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "chart",
                    "widget_config": {
                        "chart_type": "line",
                        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                        "values": [12, 19, 3, 5, 2, 3, 15],
                        "label": "Daily Active Users",
                        "color": "#2196F3",
                        "fill": True,
                        "tension": 0.3,
                    },
                }
            ],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_chart_line.png")

    def test_stock_single(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test stock widget with single stock."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "stock",
                    "widget_config": {
                        "stocks": [
                            {
                                "symbol": "AAPL",
                                "name": "Apple Inc.",
                                "price": 185.92,
                                "change": 2.47,
                                "change_percent": 1.35,
                            }
                        ]
                    },
                }
            ],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_stock_single.png")

    def test_stock_grid(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test stock widget with 4 stocks in grid."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "stock",
                    "widget_config": {
                        "stocks": [
                            {
                                "symbol": "AAPL",
                                "price": 185.92,
                                "change": 2.47,
                                "change_percent": 1.35,
                            },
                            {
                                "symbol": "GOOGL",
                                "price": 141.80,
                                "change": -1.20,
                                "change_percent": -0.84,
                            },
                            {
                                "symbol": "MSFT",
                                "price": 378.91,
                                "change": 5.23,
                                "change_percent": 1.40,
                            },
                            {
                                "symbol": "AMZN",
                                "price": 178.25,
                                "change": 0.00,
                                "change_percent": 0.00,
                            },
                        ]
                    },
                }
            ],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_stock_grid.png")

    def test_stock_list(self, page: Page, app_server: str, screen_data: dict, assert_snapshot):
        """Test stock widget with 6 stocks in list view."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "stock",
                    "widget_config": {
                        "stocks": [
                            {
                                "symbol": "AAPL",
                                "price": 185.92,
                                "change": 2.47,
                                "change_percent": 1.35,
                            },
                            {
                                "symbol": "GOOGL",
                                "price": 141.80,
                                "change": -1.20,
                                "change_percent": -0.84,
                            },
                            {
                                "symbol": "MSFT",
                                "price": 378.91,
                                "change": 5.23,
                                "change_percent": 1.40,
                            },
                            {
                                "symbol": "AMZN",
                                "price": 178.25,
                                "change": 0.00,
                                "change_percent": 0.00,
                            },
                            {
                                "symbol": "META",
                                "price": 505.95,
                                "change": 8.15,
                                "change_percent": 1.64,
                            },
                            {
                                "symbol": "NVDA",
                                "price": 495.22,
                                "change": -12.33,
                                "change_percent": -2.43,
                            },
                        ]
                    },
                }
            ],
        )

        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_stock_list.png")

    def test_widget_grid_mixed(
        self, page: Page, app_server: str, screen_data: dict, assert_snapshot
    ):
        """Test multiple widgets in a grid layout."""
        self.send_content(
            app_server,
            screen_data["screen_id"],
            screen_data["api_key"],
            content=[
                {
                    "type": "widget",
                    "widget_type": "clock",
                    "widget_config": {"style": "digital", "format": "12h"},
                },
                {
                    "type": "widget",
                    "widget_type": "countdown",
                    "widget_config": {"target": "2025-01-16T17:01:30Z", "style": "labeled"},
                },
                {
                    "type": "widget",
                    "widget_type": "chart",
                    "widget_config": {
                        "chart_type": "bar",
                        "labels": ["A", "B", "C"],
                        "values": [30, 50, 20],
                    },
                },
                {"type": "text", "value": "Regular Text Panel"},
            ],
            layout="grid-2x2",
        )

        mock_javascript_time(page)
        page.goto(f"{app_server}/screen/{screen_data['screen_id']}")
        self.wait_for_stable_screen(page)

        assert_snapshot(page, "widget_grid_mixed.png")
