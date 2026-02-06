"""E2E tests for the admin dashboard (self-hosted/local mode)."""

import re

import pytest
from playwright.sync_api import Page, expect


def _create_screen_and_find_card(page: Page, app_server: str):
    """Create a new screen and return the Playwright locator for its card.

    Uses data-screen-id diffing so we always target the newly created card,
    never the demo screen or any other pre-existing screen.
    """
    page.goto(f"{app_server}/admin/screens")
    initial_count = page.locator(".screen-card").count()
    initial_id_count = page.locator(".screen-card[data-screen-id]").count()
    existing_ids = set(
        page.locator(".screen-card").evaluate_all(
            "els => els.map(el => el.dataset.screenId).filter(Boolean)"
        )
    )
    # Click create button - opens template modal
    page.locator("#create-screen").click()
    # Wait for template modal and click "Start from Scratch"
    expect(page.locator("#template-modal")).to_be_visible()
    page.locator(".template-option-btn", has_text="Start from Scratch").click()
    # Wait for a new screen card to appear (count increases)
    expect(page.locator(".screen-card")).to_have_count(initial_count + 1)
    page.wait_for_timeout(500)
    # Ensure the new card has a data-screen-id before diffing
    expect(page.locator(".screen-card[data-screen-id]")).to_have_count(initial_id_count + 1)
    # Find the newly created card by diffing screen IDs
    all_ids = set(
        page.locator(".screen-card").evaluate_all(
            "els => els.map(el => el.dataset.screenId).filter(Boolean)"
        )
    )
    diff = all_ids - existing_ids
    assert diff, "Expected at least one new screen id after creation"
    new_id = diff.pop()
    return page.locator(f'.screen-card[data-screen-id="{new_id}"]')


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
        card = _create_screen_and_find_card(page, app_server)

        # The new card should be expanded by default
        expect(card).to_have_class(re.compile(r"expanded"))

        # Should have an unnamed screen
        expect(card.locator(".screen-name")).to_have_text("Unnamed Screen")

    def test_create_screen_shows_toast(self, page: Page, app_server: str):
        """Test that creating a screen shows a success toast."""
        _create_screen_and_find_card(page, app_server)

        # Check for success toast
        toast = page.locator(".toast.success")
        expect(toast).to_be_visible()
        expect(toast).to_have_text(re.compile(r"Screen created"))

    def test_create_screen_shows_api_details(self, page: Page, app_server: str):
        """Test that newly created screen shows API key and endpoint."""
        card = _create_screen_and_find_card(page, app_server)

        # API key should be visible (starts with sk_)
        api_key = card.locator(".api-key")
        expect(api_key).to_have_text(re.compile(r"sk_"))

        # API URL should be visible
        api_url = card.locator(".api-url")
        expect(api_url).to_have_text(re.compile(r"/api/v1/screens/"))


class TestScreenCardInteractions:
    """Tests for screen card expand/collapse and other interactions."""

    @pytest.fixture
    def new_card(self, page: Page, app_server: str):
        """Create a screen and return the locator for the new card."""
        return _create_screen_and_find_card(page, app_server)

    def test_card_collapse_expand(self, page: Page, new_card):
        """Test that clicking card header toggles expansion."""
        # Initially expanded
        expect(new_card).to_have_class(re.compile(r"expanded"))

        # Click header to collapse
        new_card.locator(".card-header").click()
        expect(new_card).not_to_have_class(re.compile(r"expanded"))

        # Click again to expand
        new_card.locator(".card-header").click()
        expect(new_card).to_have_class(re.compile(r"expanded"))

    def test_copy_api_key_button(self, page: Page, new_card):
        """Test copy API key button shows feedback."""
        # Click copy button
        copy_btn = new_card.locator(".copy-api-key")
        copy_btn.click()

        # Button should show checkmark
        expect(copy_btn).to_have_text("✓")
        expect(copy_btn).to_have_class(re.compile(r"copied"))

    def test_dropdown_menu_opens(self, page: Page, new_card):
        """Test that dropdown menus open when clicked."""
        # Click the Screen Actions dropdown
        new_card.locator('button:has-text("Screen Actions")').click()

        # Menu should be visible
        dropdown = new_card.locator(".dropdown-menu-right")
        expect(dropdown).to_have_class(re.compile(r"show"))

        # Should see options
        expect(dropdown.locator('button:has-text("View JSON")')).to_be_visible()
        expect(dropdown.locator('button:has-text("Toggle Debug")')).to_be_visible()
        expect(dropdown.locator('button:has-text("Reload Viewers")')).to_be_visible()
        expect(dropdown.locator('button:has-text("Delete Screen")')).to_be_visible()

    def test_dropdown_closes_on_outside_click(self, page: Page, new_card):
        """Test that dropdown closes when clicking outside."""
        # Open dropdown
        new_card.locator('button:has-text("Screen Actions")').click()
        dropdown = new_card.locator(".dropdown-menu-right")
        expect(dropdown).to_have_class(re.compile(r"show"))

        # Click outside
        page.locator("h1").click()

        # Dropdown should close
        expect(dropdown).not_to_have_class(re.compile(r"show"))


class TestScreenNameEditing:
    """Tests for inline name editing."""

    @pytest.fixture
    def new_card(self, page: Page, app_server: str):
        """Create a screen and return the locator for the new card."""
        return _create_screen_and_find_card(page, app_server)

    def test_click_name_shows_input(self, page: Page, new_card):
        """Test that clicking the name shows an input field."""
        # Click the name
        new_card.locator(".screen-name").click()

        # Should show input
        name_input = new_card.locator(".name-input")
        expect(name_input).to_be_visible()
        expect(name_input).to_be_focused()

    def test_edit_name_saves_on_blur(self, page: Page, new_card):
        """Test that editing name and blurring saves the change."""
        # Click the name
        new_card.locator(".screen-name").click()

        # Type new name
        name_input = new_card.locator(".name-input")
        name_input.fill("Test Screen Name")

        # Blur by clicking elsewhere
        new_card.locator(".card-header").click()

        # Name should be updated
        expect(new_card.locator(".screen-name")).to_have_text("Test Screen Name")

    def test_edit_name_saves_on_enter(self, page: Page, new_card):
        """Test that pressing Enter saves the name."""
        # Click the name
        new_card.locator(".screen-name").click()

        # Type new name and press Enter
        name_input = new_card.locator(".name-input")
        name_input.fill("Enter Key Test")
        name_input.press("Enter")

        # Name should be updated
        expect(new_card.locator(".screen-name")).to_have_text("Enter Key Test")

    def test_edit_name_escape_cancels(self, page: Page, new_card):
        """Test that pressing Escape cancels the edit."""
        # Click the name
        new_card.locator(".screen-name").click()

        # Type new name and press Escape
        name_input = new_card.locator(".name-input")
        name_input.fill("Should Not Save")
        name_input.press("Escape")

        # Name should remain unchanged (Unnamed Screen)
        expect(new_card.locator(".screen-name")).to_have_text("Unnamed Screen")


class TestScreenDeletion:
    """Tests for deleting screens."""

    @pytest.fixture
    def page_and_card(self, page: Page, app_server: str):
        """Create a screen and return (page, card) for that screen."""
        card = _create_screen_and_find_card(page, app_server)
        return page, card

    def test_delete_screen_with_confirmation(self, page_and_card):
        """Test that deleting a screen requires confirmation."""
        page, card = page_and_card
        # Wait for any existing toasts to disappear
        page.wait_for_timeout(3500)

        initial_count = page.locator(".screen-card").count()

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Set up dialog handler to accept
        page.on("dialog", lambda dialog: dialog.accept())

        # Click delete
        card.locator('button:has-text("Delete Screen")').click()

        # Wait for deletion
        page.wait_for_timeout(500)

        # Card count should decrease by 1
        expect(page.locator(".screen-card")).to_have_count(initial_count - 1)

    def test_delete_screen_shows_toast(self, page_and_card):
        """Test that deleting shows a success toast."""
        page, card = page_and_card
        # Wait for any existing toasts to disappear
        page.wait_for_timeout(3500)

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Accept confirmation
        page.on("dialog", lambda dialog: dialog.accept())

        # Click delete
        card.locator('button:has-text("Delete Screen")').click()

        # Check for success toast with delete message
        toast = page.locator(".toast.success:has-text('deleted')")
        expect(toast).to_be_visible()

    def test_delete_screen_cancel_keeps_screen(self, page_and_card):
        """Test that canceling delete keeps the screen."""
        page, card = page_and_card

        # Open dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Dismiss confirmation
        page.on("dialog", lambda dialog: dialog.dismiss())

        # Click delete
        card.locator('button:has-text("Delete Screen")').click()

        # Wait a bit
        page.wait_for_timeout(500)

        # Card should still be there
        expect(card).to_be_visible()


class TestScreenActions:
    """Tests for screen action buttons (reload, debug, etc.)."""

    @pytest.fixture
    def new_card(self, page: Page, app_server: str):
        """Create a screen and return the locator for the new card."""
        return _create_screen_and_find_card(page, app_server)

    def test_reload_viewers_shows_toast(self, page: Page, new_card):
        """Test that reload viewers shows a toast notification."""
        # Wait for any existing toasts to disappear
        page.wait_for_timeout(3500)

        # Open dropdown
        new_card.locator('button:has-text("Screen Actions")').click()

        # Click reload
        new_card.locator('button:has-text("Reload Viewers")').click()

        # Should show success toast with reload message
        toast = page.locator(".toast.success:has-text('Reload')")
        expect(toast).to_be_visible()

    def test_toggle_debug_shows_toast(self, page: Page, new_card):
        """Test that toggle debug shows a toast notification."""
        # Wait for any existing toasts to disappear
        page.wait_for_timeout(3500)

        # Open dropdown
        new_card.locator('button:has-text("Screen Actions")').click()

        # Click toggle debug
        new_card.locator('button:has-text("Toggle Debug")').click()

        # Should show success toast with debug message
        toast = page.locator(".toast.success:has-text('Debug')")
        expect(toast).to_be_visible()

    def test_view_json_opens_modal(self, page: Page, new_card):
        """Test that view JSON opens a modal with the screen data."""
        # Open dropdown
        new_card.locator('button:has-text("Screen Actions")').click()

        # Click view JSON
        new_card.locator('button:has-text("View JSON")').click()

        # Modal should be visible
        modal = page.locator("#json-modal")
        expect(modal).to_be_visible()

        # Should have JSON content
        json_content = modal.locator("#json-content")
        expect(json_content).to_be_visible()

        # Close modal
        modal.locator('button:has-text("Close")').click()
        expect(modal).not_to_be_visible()


class TestDuplicateScreen:
    """Tests for duplicating screens."""

    @pytest.fixture
    def new_card(self, page: Page, app_server: str):
        """Create a screen and return the locator for the new card."""
        return _create_screen_and_find_card(page, app_server)

    def test_duplicate_screen_creates_copy(self, page: Page, new_card):
        """Test that duplicate screen creates a new screen card."""
        # Wait for any existing toasts to disappear
        page.wait_for_timeout(3500)

        initial_count = page.locator(".screen-card").count()

        # Open dropdown
        new_card.locator('button:has-text("Screen Actions")').click()

        # Click duplicate
        new_card.locator('button:has-text("Duplicate Screen")').click()

        # Should show success toast
        toast = page.locator(".toast.success:has-text('duplicated')")
        expect(toast).to_be_visible()

        # Should have one more screen
        expect(page.locator(".screen-card")).to_have_count(initial_count + 1)

    def test_duplicate_screen_has_copy_name(self, page: Page, new_card):
        """Test that duplicated screen has (Copy) in its name."""
        # Wait for any existing toasts to disappear
        page.wait_for_timeout(3500)

        # Name the original screen first
        new_card.locator(".screen-name").click()
        name_input = new_card.locator(".name-input")
        name_input.fill("Original Screen")
        name_input.press("Enter")

        # Wait for name to be saved and displayed
        expect(new_card.locator(".screen-name")).to_have_text("Original Screen")

        # Open dropdown and duplicate
        new_card.locator('button:has-text("Screen Actions")').click()
        new_card.locator('button:has-text("Duplicate Screen")').click()

        # Wait for duplication success toast
        toast = page.locator(".toast.success:has-text('duplicated')")
        expect(toast).to_be_visible()

        # The duplicate should be first and have (Copy) in name
        duplicate_card = page.locator(".screen-card").first
        expect(duplicate_card.locator(".screen-name")).to_have_text(re.compile(r"\(Copy\)"))

    def test_duplicated_screen_actions_work(self, page: Page, new_card):
        """Test that action buttons work on the duplicated screen card."""
        # Wait for any existing toasts to disappear
        page.wait_for_timeout(3500)

        # Duplicate the screen
        new_card.locator('button:has-text("Screen Actions")').click()
        new_card.locator('button:has-text("Duplicate Screen")').click()

        # Wait for new card
        page.wait_for_timeout(500)

        # Wait for duplicate toast to disappear
        page.wait_for_timeout(3500)

        # The duplicate is now the first card
        duplicate_card = page.locator(".screen-card").first

        # Open dropdown on the DUPLICATE and click View JSON
        duplicate_card.locator('button:has-text("Screen Actions")').click()
        duplicate_card.locator('button:has-text("View JSON")').click()

        # Modal should open
        modal = page.locator("#json-modal")
        expect(modal).to_be_visible()

        # Close modal
        modal.locator('button:has-text("Close")').click()

        # Now test Toggle Debug on the duplicate
        page.wait_for_timeout(500)
        duplicate_card.locator('button:has-text("Screen Actions")').click()
        duplicate_card.locator('button:has-text("Toggle Debug")').click()

        # Should show toast
        toast = page.locator(".toast.success:has-text('Debug')")
        expect(toast).to_be_visible()
