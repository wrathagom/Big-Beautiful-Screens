"""E2E tests for the admin dashboard (self-hosted/local mode)."""

import re

import pytest
from playwright.sync_api import Page, expect


class TestAdminDashboard:
    """Tests for the admin dashboard page."""

    def test_admin_page_loads(self, page: Page, app_server: str):
        """Test that the admin page loads successfully."""
        page.goto(f"{app_server}/admin/screens")

        # Check page title
        expect(page).to_have_title("Big Beautiful Screens - Admin")

        # Check header elements
        expect(page.locator("h1")).to_have_text("Big Beautiful Screens")
        expect(page.locator(".subtitle")).to_have_text("Admin Dashboard")

        # Check create button exists
        expect(page.locator("#create-screen")).to_be_visible()
        expect(page.locator("#create-screen")).to_have_text("+ Create New Screen")

    def test_navigation_links_visible(self, page: Page, app_server: str):
        """Test that navigation links are present."""
        page.goto(f"{app_server}/admin/screens")

        # Check nav links
        expect(page.locator('a.nav-link:has-text("Themes")')).to_be_visible()
        expect(page.locator('a.nav-link:has-text("Media")')).to_be_visible()

    def test_screen_list_or_empty_state(self, page: Page, app_server: str):
        """Test that screen list or empty state is shown."""
        page.goto(f"{app_server}/admin/screens")

        # Should show either screen cards OR empty message
        screen_list = page.locator(".screen-list")
        expect(screen_list).to_be_visible()

        # Either has screens or shows empty message
        has_screens = page.locator(".screen-card").count() > 0
        has_empty = page.locator(".empty").count() > 0
        assert has_screens or has_empty, "Expected either screens or empty message"


class TestScreenCreation:
    """Tests for creating screens."""

    def test_create_screen_button_works(self, page: Page, app_server: str):
        """Test that clicking create screen button creates a new screen."""
        page.goto(f"{app_server}/admin/screens")

        # Click create button
        page.locator("#create-screen").click()

        # Wait for the screen card to appear
        screen_card = page.locator(".screen-card").first
        expect(screen_card).to_be_visible()

        # The card should be expanded by default
        expect(screen_card).to_have_class(re.compile(r"expanded"))

        # Should have an unnamed screen
        expect(screen_card.locator(".screen-name")).to_have_text("Unnamed Screen")

    def test_create_screen_shows_toast(self, page: Page, app_server: str):
        """Test that creating a screen shows a success toast."""
        page.goto(f"{app_server}/admin/screens")

        # Click create button
        page.locator("#create-screen").click()

        # Check for success toast
        toast = page.locator(".toast.success")
        expect(toast).to_be_visible()
        expect(toast).to_have_text(re.compile(r"Screen created"))

    def test_create_screen_shows_api_details(self, page: Page, app_server: str):
        """Test that newly created screen shows API key and endpoint."""
        page.goto(f"{app_server}/admin/screens")

        # Click create button
        page.locator("#create-screen").click()

        # Wait for card
        card = page.locator(".screen-card").first
        expect(card).to_be_visible()

        # API key should be visible (starts with sk_)
        api_key = card.locator(".api-key")
        expect(api_key).to_have_text(re.compile(r"sk_"))

        # API URL should be visible
        api_url = card.locator(".api-url")
        expect(api_url).to_have_text(re.compile(r"/api/v1/screens/"))


class TestScreenCardInteractions:
    """Tests for screen card expand/collapse and other interactions."""

    @pytest.fixture
    def page_with_screen(self, page: Page, app_server: str):
        """Set up a page with one screen created."""
        page.goto(f"{app_server}/admin/screens")
        page.locator("#create-screen").click()
        page.locator(".screen-card").first.wait_for()
        # Wait for toast to disappear
        page.wait_for_timeout(500)
        return page

    def test_card_collapse_expand(self, page_with_screen: Page):
        """Test that clicking card header toggles expansion."""
        card = page_with_screen.locator(".screen-card").first

        # Initially expanded
        expect(card).to_have_class(re.compile(r"expanded"))

        # Click header to collapse
        card.locator(".card-header").click()
        expect(card).not_to_have_class(re.compile(r"expanded"))

        # Click again to expand
        card.locator(".card-header").click()
        expect(card).to_have_class(re.compile(r"expanded"))

    def test_copy_api_key_button(self, page_with_screen: Page, app_server: str):
        """Test copy API key button shows feedback."""
        card = page_with_screen.locator(".screen-card").first

        # Click copy button
        copy_btn = card.locator(".copy-api-key")
        copy_btn.click()

        # Button should show checkmark
        expect(copy_btn).to_have_text("✓")
        expect(copy_btn).to_have_class(re.compile(r"copied"))

    def test_dropdown_menu_opens(self, page_with_screen: Page):
        """Test that dropdown menus open when clicked."""
        card = page_with_screen.locator(".screen-card").first

        # Click the Screen Actions dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Menu should be visible
        dropdown = card.locator(".dropdown-menu-right")
        expect(dropdown).to_have_class(re.compile(r"show"))

        # Should see options
        expect(dropdown.locator('button:has-text("View JSON")')).to_be_visible()
        expect(dropdown.locator('button:has-text("Toggle Debug")')).to_be_visible()
        expect(dropdown.locator('button:has-text("Reload Viewers")')).to_be_visible()
        expect(dropdown.locator('button:has-text("Delete Screen")')).to_be_visible()

    def test_dropdown_closes_on_outside_click(self, page_with_screen: Page):
        """Test that dropdown closes when clicking outside."""
        card = page_with_screen.locator(".screen-card").first

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()
        dropdown = card.locator(".dropdown-menu-right")
        expect(dropdown).to_have_class(re.compile(r"show"))

        # Click outside
        page_with_screen.locator("h1").click()

        # Dropdown should close
        expect(dropdown).not_to_have_class(re.compile(r"show"))


class TestScreenNameEditing:
    """Tests for inline name editing."""

    @pytest.fixture
    def page_with_screen(self, page: Page, app_server: str):
        """Set up a page with one screen created."""
        page.goto(f"{app_server}/admin/screens")
        page.locator("#create-screen").click()
        page.locator(".screen-card").first.wait_for()
        page.wait_for_timeout(500)
        return page

    def test_click_name_shows_input(self, page_with_screen: Page):
        """Test that clicking the name shows an input field."""
        card = page_with_screen.locator(".screen-card").first

        # Click the name
        card.locator(".screen-name").click()

        # Should show input
        name_input = card.locator(".name-input")
        expect(name_input).to_be_visible()
        expect(name_input).to_be_focused()

    def test_edit_name_saves_on_blur(self, page_with_screen: Page):
        """Test that editing name and blurring saves the change."""
        card = page_with_screen.locator(".screen-card").first

        # Click the name
        card.locator(".screen-name").click()

        # Type new name
        name_input = card.locator(".name-input")
        name_input.fill("Test Screen Name")

        # Blur by clicking elsewhere
        card.locator(".card-header").click()

        # Name should be updated
        expect(card.locator(".screen-name")).to_have_text("Test Screen Name")

    def test_edit_name_saves_on_enter(self, page_with_screen: Page):
        """Test that pressing Enter saves the name."""
        card = page_with_screen.locator(".screen-card").first

        # Click the name
        card.locator(".screen-name").click()

        # Type new name and press Enter
        name_input = card.locator(".name-input")
        name_input.fill("Enter Key Test")
        name_input.press("Enter")

        # Name should be updated
        expect(card.locator(".screen-name")).to_have_text("Enter Key Test")

    def test_edit_name_escape_cancels(self, page_with_screen: Page):
        """Test that pressing Escape cancels the edit."""
        card = page_with_screen.locator(".screen-card").first

        # Click the name
        card.locator(".screen-name").click()

        # Type new name and press Escape
        name_input = card.locator(".name-input")
        name_input.fill("Should Not Save")
        name_input.press("Escape")

        # Name should remain unchanged (Unnamed Screen)
        expect(card.locator(".screen-name")).to_have_text("Unnamed Screen")


class TestScreenDeletion:
    """Tests for deleting screens."""

    @pytest.fixture
    def page_with_screen(self, page: Page, app_server: str):
        """Set up a page with one screen created."""
        page.goto(f"{app_server}/admin/screens")
        page.locator("#create-screen").click()
        page.locator(".screen-card").first.wait_for()
        page.wait_for_timeout(500)
        return page

    def test_delete_screen_with_confirmation(self, page_with_screen: Page):
        """Test that deleting a screen requires confirmation."""
        # Wait for any existing toasts to disappear
        page_with_screen.wait_for_timeout(3500)

        initial_count = page_with_screen.locator(".screen-card").count()
        card = page_with_screen.locator(".screen-card").first

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Set up dialog handler to accept
        page_with_screen.on("dialog", lambda dialog: dialog.accept())

        # Click delete
        card.locator('button:has-text("Delete Screen")').click()

        # Wait for deletion
        page_with_screen.wait_for_timeout(500)

        # Card count should decrease by 1
        expect(page_with_screen.locator(".screen-card")).to_have_count(initial_count - 1)

    def test_delete_screen_shows_toast(self, page_with_screen: Page):
        """Test that deleting shows a success toast."""
        # Wait for any existing toasts to disappear
        page_with_screen.wait_for_timeout(3500)

        card = page_with_screen.locator(".screen-card").first

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Accept confirmation
        page_with_screen.on("dialog", lambda dialog: dialog.accept())

        # Click delete
        card.locator('button:has-text("Delete Screen")').click()

        # Check for success toast with delete message
        toast = page_with_screen.locator(".toast.success:has-text('deleted')")
        expect(toast).to_be_visible()

    def test_delete_screen_cancel_keeps_screen(self, page_with_screen: Page):
        """Test that canceling delete keeps the screen."""
        card = page_with_screen.locator(".screen-card").first

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Dismiss confirmation
        page_with_screen.on("dialog", lambda dialog: dialog.dismiss())

        # Click delete
        card.locator('button:has-text("Delete Screen")').click()

        # Wait a bit
        page_with_screen.wait_for_timeout(500)

        # Card should still be there
        expect(card).to_be_visible()


class TestScreenActions:
    """Tests for screen action buttons (reload, debug, etc.)."""

    @pytest.fixture
    def page_with_screen(self, page: Page, app_server: str):
        """Set up a page with one screen created."""
        page.goto(f"{app_server}/admin/screens")
        page.locator("#create-screen").click()
        page.locator(".screen-card").first.wait_for()
        page.wait_for_timeout(500)
        return page

    def test_reload_viewers_shows_toast(self, page_with_screen: Page):
        """Test that reload viewers shows a toast notification."""
        card = page_with_screen.locator(".screen-card").first

        # Wait for any existing toasts to disappear
        page_with_screen.wait_for_timeout(3500)

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Click reload
        card.locator('button:has-text("Reload Viewers")').click()

        # Should show success toast with reload message
        toast = page_with_screen.locator(".toast.success:has-text('Reload')")
        expect(toast).to_be_visible()

    def test_toggle_debug_shows_toast(self, page_with_screen: Page):
        """Test that toggle debug shows a toast notification."""
        card = page_with_screen.locator(".screen-card").first

        # Wait for any existing toasts to disappear
        page_with_screen.wait_for_timeout(3500)

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Click toggle debug
        card.locator('button:has-text("Toggle Debug")').click()

        # Should show success toast with debug message
        toast = page_with_screen.locator(".toast.success:has-text('Debug')")
        expect(toast).to_be_visible()

    def test_view_json_opens_modal(self, page_with_screen: Page):
        """Test that view JSON opens a modal with the screen data."""
        card = page_with_screen.locator(".screen-card").first

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Click view JSON
        card.locator('button:has-text("View JSON")').click()

        # Modal should be visible
        modal = page_with_screen.locator("#json-modal")
        expect(modal).to_be_visible()

        # Should have JSON content
        json_content = modal.locator("#json-content")
        expect(json_content).to_be_visible()

        # Close modal
        modal.locator('button:has-text("Close")').click()
        expect(modal).not_to_be_visible()
