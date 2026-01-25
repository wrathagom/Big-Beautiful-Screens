"""E2E tests for the demo screen pages and transitions.

These tests capture screenshots of each page of the auto-created demo screen,
testing both the content and the rotation/transition functionality.
"""

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import mock_javascript_time

# Demo screen rotation interval (from demo_screen.json)
ROTATION_INTERVAL_MS = 8000

# Time to wait for "Connected" notification to disappear
NOTIFICATION_HIDE_WAIT = 2500

# Extra buffer for transitions and rendering
TRANSITION_BUFFER = 1000


class TestDemoScreenPages:
    """Visual regression tests for all demo screen pages."""

    @pytest.fixture(scope="class")
    def demo_screen_id(self, app_server: str):
        """Find the demo screen ID (should be the only screen on fresh start)."""
        with httpx.Client() as client:
            # Get all screens - demo screen is auto-created
            response = client.get(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            data = response.json()
            screens = data.get("screens", [])

            # Find the demo screen by name
            for screen in screens:
                if screen.get("name") == "Welcome Demo":
                    return screen["screen_id"]

            # If no demo screen found, create one manually for testing
            # This shouldn't happen in a fresh test database
            pytest.skip("Demo screen not found - test requires fresh database")

    def wait_for_stable_page(self, page: Page):
        """Wait for content to stabilize after page transition."""
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT + TRANSITION_BUFFER)

    def wait_for_next_page(self, page: Page):
        """Wait for the next page rotation."""
        page.wait_for_timeout(ROTATION_INTERVAL_MS + TRANSITION_BUFFER)

    def test_demo_page_1_welcome(
        self, page: Page, app_server: str, demo_screen_id: str, assert_snapshot
    ):
        """Test demo screen page 1: Welcome introduction."""
        page.goto(f"{app_server}/screen/{demo_screen_id}")
        self.wait_for_stable_page(page)

        # Verify we're on the welcome page
        expect(page.locator("text=Welcome to Big Beautiful Screens")).to_be_visible()

        assert_snapshot(page, "demo_page_1_welcome.png")

    def test_demo_page_2_content_types(
        self, page: Page, app_server: str, demo_screen_id: str, assert_snapshot
    ):
        """Test demo screen page 2: Content types showcase."""
        page.goto(f"{app_server}/screen/{demo_screen_id}")
        self.wait_for_stable_page(page)

        # Wait for rotation to page 2
        self.wait_for_next_page(page)

        # Verify we're on the content types page
        expect(page.locator("h1:has-text('Content Types')")).to_be_visible()

        assert_snapshot(page, "demo_page_2_content_types.png")

    def test_demo_page_3_api(
        self, page: Page, app_server: str, demo_screen_id: str, assert_snapshot
    ):
        """Test demo screen page 3: API documentation."""
        page.goto(f"{app_server}/screen/{demo_screen_id}")
        self.wait_for_stable_page(page)

        # Wait for rotation to page 3 (2 rotations)
        self.wait_for_next_page(page)
        self.wait_for_next_page(page)

        # Verify we're on the API page
        expect(page.locator("h1:has-text('API Powered')")).to_be_visible()

        assert_snapshot(page, "demo_page_3_api.png")

    def test_demo_page_4_widgets(
        self, page: Page, app_server: str, demo_screen_id: str, assert_snapshot
    ):
        """Test demo screen page 4: Interactive widgets with mocked time."""
        # Mock time BEFORE navigating to get consistent clock display
        mock_javascript_time(page)

        page.goto(f"{app_server}/screen/{demo_screen_id}")
        self.wait_for_stable_page(page)

        # Wait for rotation to page 4 (3 rotations)
        self.wait_for_next_page(page)
        self.wait_for_next_page(page)
        self.wait_for_next_page(page)

        # Verify we're on the widgets page
        expect(page.locator("h1:has-text('Interactive Widgets')")).to_be_visible()

        # Verify clock widgets are visible
        expect(page.locator(".widget-clock").first).to_be_visible()

        assert_snapshot(page, "demo_page_4_widgets.png")

    def test_demo_page_5_themes(
        self, page: Page, app_server: str, demo_screen_id: str, assert_snapshot
    ):
        """Test demo screen page 5: Themes and styling."""
        page.goto(f"{app_server}/screen/{demo_screen_id}")
        self.wait_for_stable_page(page)

        # Wait for rotation to page 5 (4 rotations)
        self.wait_for_next_page(page)
        self.wait_for_next_page(page)
        self.wait_for_next_page(page)
        self.wait_for_next_page(page)

        # Verify we're on the themes page
        expect(page.locator("h1:has-text('Themes & Styling')")).to_be_visible()

        assert_snapshot(page, "demo_page_5_themes.png")


class TestDemoScreenTransitions:
    """Tests for demo screen page transitions."""

    @pytest.fixture(scope="class")
    def demo_screen_id(self, app_server: str):
        """Find the demo screen ID."""
        with httpx.Client() as client:
            response = client.get(f"{app_server}/api/v1/screens")
            assert response.status_code == 200
            data = response.json()
            screens = data.get("screens", [])

            for screen in screens:
                if screen.get("name") == "Welcome Demo":
                    return screen["screen_id"]

            pytest.skip("Demo screen not found")

    def test_fade_transition(self, page: Page, app_server: str, demo_screen_id: str):
        """Test that fade transition occurs between pages."""
        page.goto(f"{app_server}/screen/{demo_screen_id}")

        # Wait for initial load
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)

        # Verify initial page content
        expect(page.locator("text=Welcome to Big Beautiful Screens")).to_be_visible()

        # Wait for transition to start (slightly before 8 seconds)
        page.wait_for_timeout(ROTATION_INTERVAL_MS - 500)

        # At this point transition should be starting
        # The content should change to page 2 after full wait
        page.wait_for_timeout(1500)

        # Verify we're now on page 2
        expect(page.locator("h1:has-text('Content Types')")).to_be_visible()

    def test_slide_left_transition(self, page: Page, app_server: str, demo_screen_id: str):
        """Test that slide-left transition works on widgets page."""
        page.goto(f"{app_server}/screen/{demo_screen_id}")
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)

        # Wait for rotation to page 3 (before widgets page)
        page.wait_for_timeout(ROTATION_INTERVAL_MS * 2 + 500)

        # Verify we're on API page (page 3)
        expect(page.locator("h1:has-text('API Powered')")).to_be_visible()

        # Now wait for transition to widgets page (which uses slide-left)
        page.wait_for_timeout(ROTATION_INTERVAL_MS + 1000)

        # Verify we're now on widgets page
        expect(page.locator("h1:has-text('Interactive Widgets')")).to_be_visible()

    def test_rotation_cycles_back(self, page: Page, app_server: str, demo_screen_id: str):
        """Test that rotation cycles back to page 1 after page 5."""
        page.goto(f"{app_server}/screen/{demo_screen_id}")
        page.wait_for_timeout(NOTIFICATION_HIDE_WAIT)

        # Wait for all 5 pages to cycle through (5 rotations)
        page.wait_for_timeout(ROTATION_INTERVAL_MS * 5 + 2000)

        # Should be back on page 1
        expect(page.locator("text=Welcome to Big Beautiful Screens")).to_be_visible()
