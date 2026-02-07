"""E2E tests for the templates feature."""

import re

import pytest
from playwright.sync_api import Page, expect


class TestTemplatesPage:
    """Tests for the templates management page."""

    def test_templates_page_loads(self, page: Page, app_server: str):
        """Test that the templates management page loads."""
        page.goto(f"{app_server}/admin/templates")

        # Check page title
        expect(page).to_have_title("My Templates - Big Beautiful Screens")

        # Check header
        expect(page.locator("h1")).to_have_text("My Templates")

    def test_templates_page_shows_empty_state(self, page: Page, app_server: str):
        """Test that empty state is shown when no user templates exist."""
        page.goto(f"{app_server}/admin/templates")

        # Should show empty state since no user templates exist initially
        empty_state = page.locator(".empty-state")
        expect(empty_state).to_be_visible()
        expect(empty_state.locator("h3")).to_have_text("No templates yet")

    def test_templates_page_navigation_links(self, page: Page, app_server: str):
        """Test that navigation links are present in the dropdown menu."""
        page.goto(f"{app_server}/admin/templates")

        # Open the nav dropdown menu
        page.locator('button:has-text("Menu")').click()
        menu = page.locator(".nav-dropdown-menu")
        expect(menu).to_have_class(re.compile(r"show"))

        # Check nav links inside dropdown
        expect(menu.locator('a:has-text("Screens")')).to_be_visible()
        expect(menu.locator('a:has-text("Themes")')).to_be_visible()
        expect(menu.locator('a:has-text("Media")')).to_be_visible()

    def test_templates_link_in_screens_page(self, page: Page, app_server: str):
        """Test that Templates link exists in screens page navigation."""
        page.goto(f"{app_server}/admin/screens")

        # Open the nav dropdown menu
        page.locator('button:has-text("Menu")').click()
        menu = page.locator(".nav-dropdown-menu")
        expect(menu).to_have_class(re.compile(r"show"))

        # Check Templates link exists and click it
        templates_link = menu.locator('a:has-text("Templates")')
        expect(templates_link).to_be_visible()
        templates_link.click()
        expect(page).to_have_url(re.compile(r"/admin/templates"))


class TestTemplateGallery:
    """Tests for the template selection gallery when creating screens."""

    def test_template_modal_opens(self, page: Page, app_server: str):
        """Test that clicking create screen shows template options."""
        page.goto(f"{app_server}/admin/screens")

        # Click create button
        page.locator("#create-screen").click()

        # Template modal should appear
        modal = page.locator("#template-modal")
        expect(modal).to_be_visible()

        # Should have "Start from Scratch" and "Use a Template" options
        expect(page.locator('.template-option-btn:has-text("Start from Scratch")')).to_be_visible()
        expect(page.locator('.template-option-btn:has-text("Use a Template")')).to_be_visible()

    def test_blank_screen_option_works(self, page: Page, app_server: str):
        """Test that blank screen option creates a screen without template."""
        page.goto(f"{app_server}/admin/screens")
        initial_count = page.locator(".screen-card").count()

        # Click create button
        page.locator("#create-screen").click()

        # Click "Start from Scratch" (blank screen)
        page.locator('.template-option-btn:has-text("Start from Scratch")').click()

        # Should create a new screen
        expect(page.locator(".screen-card")).to_have_count(initial_count + 1)

    def test_template_gallery_shows_system_templates(self, page: Page, app_server: str):
        """Test that system templates are shown in the gallery."""
        page.goto(f"{app_server}/admin/screens")

        # Click create button
        page.locator("#create-screen").click()

        # Click "Use a Template"
        page.locator('.template-option-btn:has-text("Use a Template")').click()

        # Should show template gallery
        gallery = page.locator("#template-gallery")
        expect(gallery).to_be_visible()

        # Should have template cards (system templates are seeded)
        template_cards = page.locator(".template-card")
        expect(template_cards.first).to_be_visible()

        # Should have at least one system template
        count = template_cards.count()
        assert count > 0, "Expected at least one system template"

    def test_template_category_filter(self, page: Page, app_server: str):
        """Test that category filter dropdown works."""
        page.goto(f"{app_server}/admin/screens")

        # Open template gallery
        page.locator("#create-screen").click()
        page.locator('.template-option-btn:has-text("Use a Template")').click()

        # Use the category filter dropdown
        page.locator("#template-category-filter").select_option("restaurant")

        # Wait for filter to apply
        page.wait_for_timeout(300)

        # All visible templates should be in Restaurant category
        # (Check the category badges on visible cards)
        visible_badges = page.locator(".template-card:visible .template-category")
        count = visible_badges.count()
        if count > 0:
            for i in range(count):
                expect(visible_badges.nth(i)).to_have_text(re.compile(r"restaurant", re.IGNORECASE))

    def test_template_preview_modal(self, page: Page, app_server: str):
        """Test that clicking a template shows preview modal."""
        page.goto(f"{app_server}/admin/screens")

        # Open template gallery
        page.locator("#create-screen").click()
        page.locator('.template-option-btn:has-text("Use a Template")').click()

        # Click on first template card
        page.locator(".template-card").first.click()

        # Preview modal should appear
        preview_modal = page.locator("#template-preview-modal")
        expect(preview_modal).to_be_visible()

        # Should have template name
        expect(preview_modal.locator(".preview-name")).to_be_visible()

        # Should have "Use This Template" button
        expect(preview_modal.locator('button:has-text("Use This Template")')).to_be_visible()


class TestCreateScreenFromTemplate:
    """Tests for creating screens from templates."""

    def test_create_screen_from_system_template(self, page: Page, app_server: str):
        """Test creating a screen from a system template."""
        page.goto(f"{app_server}/admin/screens")
        initial_count = page.locator(".screen-card").count()

        # Open template gallery
        page.locator("#create-screen").click()
        page.locator('.template-option-btn:has-text("Use a Template")').click()

        # Click on first template
        page.locator(".template-card").first.click()

        # Click "Use This Template"
        page.locator('button:has-text("Use This Template")').click()

        # Should create a new screen
        expect(page.locator(".screen-card")).to_have_count(initial_count + 1)

        # Success toast should appear
        toast = page.locator(".toast.success")
        expect(toast).to_be_visible()

    def test_screen_from_template_has_content(self, page: Page, app_server: str):
        """Test that screen created from template has content."""
        page.goto(f"{app_server}/admin/screens")

        # Open template gallery
        page.locator("#create-screen").click()
        page.locator('.template-option-btn:has-text("Use a Template")').click()

        # Click on first template
        page.locator(".template-card").first.click()

        # Click "Use This Template"
        page.locator('button:has-text("Use This Template")').click()

        # Wait for screen to be created
        page.wait_for_timeout(500)

        # Open the JSON view to verify content
        card = page.locator(".screen-card").first
        card.locator('button:has-text("Screen Actions")').click()
        card.locator('button:has-text("View JSON")').click()

        # Modal should show JSON with pages
        modal = page.locator("#json-modal")
        expect(modal).to_be_visible()

        json_content = modal.locator("#json-content").text_content()
        assert '"pages"' in json_content, "Expected pages in JSON"
        assert '"content"' in json_content, "Expected content in JSON"


class TestSaveAsTemplate:
    """Tests for saving screens as templates."""

    @pytest.fixture
    def page_with_screen(self, page: Page, app_server: str):
        """Set up a page with a screen created from a template."""
        page.goto(f"{app_server}/admin/screens")

        # Create a screen from template to have content
        page.locator("#create-screen").click()
        page.locator('.template-option-btn:has-text("Use a Template")').click()
        page.locator(".template-card").first.click()
        page.locator('button:has-text("Use This Template")').click()

        # Wait for screen creation
        page.wait_for_timeout(500)
        return page

    def test_save_as_template_button_visible(self, page_with_screen: Page):
        """Test that Save as Template button is visible in screen card."""
        card = page_with_screen.locator(".screen-card").first

        # Open the Screen Actions dropdown
        card.locator('button:has-text("Screen Actions")').click()

        # Should see "Save as Template" option
        expect(card.locator('button:has-text("Save as Template")')).to_be_visible()

    def test_save_as_template_modal_opens(self, page_with_screen: Page):
        """Test that clicking Save as Template opens the modal."""
        card = page_with_screen.locator(".screen-card").first

        # Open dropdown and click Save as Template
        card.locator('button:has-text("Screen Actions")').click()
        card.locator('button:has-text("Save as Template")').click()

        # Modal should appear
        modal = page_with_screen.locator("#save-template-modal")
        expect(modal).to_be_visible()

        # Should have form fields
        expect(modal.locator("#template-name")).to_be_visible()
        expect(modal.locator("#template-description")).to_be_visible()
        expect(modal.locator("#template-category-select")).to_be_visible()

    def test_save_template_creates_user_template(self, page_with_screen: Page, app_server: str):
        """Test that saving a template creates a user template."""
        card = page_with_screen.locator(".screen-card").first

        # Open dropdown and click Save as Template
        card.locator('button:has-text("Screen Actions")').click()
        card.locator('button:has-text("Save as Template")').click()

        # Fill in form
        modal = page_with_screen.locator("#save-template-modal")
        modal.locator("#template-name").fill("My E2E Test Template")
        modal.locator("#template-description").fill("Created during E2E testing")
        modal.locator("#template-category-select").select_option("custom")

        # Save
        modal.locator('button:has-text("Save Template")').click()

        # Should show success toast
        toast = page_with_screen.locator(".toast.success")
        expect(toast).to_be_visible()

        # Navigate to templates page and verify template exists
        page_with_screen.goto(f"{app_server}/admin/templates")

        # Should see the template card
        template_card = page_with_screen.locator('.template-card:has-text("My E2E Test Template")')
        expect(template_card).to_be_visible()

    def test_save_template_requires_name(self, page_with_screen: Page):
        """Test that name is required when saving template."""
        card = page_with_screen.locator(".screen-card").first

        # Open dropdown and click Save as Template
        card.locator('button:has-text("Screen Actions")').click()
        card.locator('button:has-text("Save as Template")').click()

        # Leave name empty and try to save
        modal = page_with_screen.locator("#save-template-modal")
        modal.locator("#template-name").fill("")
        modal.locator('button:has-text("Save Template")').click()

        # Modal should still be visible (not closed)
        expect(modal).to_be_visible()


class TestManageUserTemplates:
    """Tests for managing user templates on the templates page."""

    @pytest.fixture
    def page_with_user_template(self, page: Page, app_server: str):
        """Set up a page with a user template created."""
        page.goto(f"{app_server}/admin/screens")

        # Create a screen from template
        page.locator("#create-screen").click()
        page.locator('.template-option-btn:has-text("Use a Template")').click()
        page.locator(".template-card").first.click()
        page.locator('button:has-text("Use This Template")').click()
        page.wait_for_timeout(500)

        # Save as template
        card = page.locator(".screen-card").first
        card.locator('button:has-text("Screen Actions")').click()
        card.locator('button:has-text("Save as Template")').click()

        modal = page.locator("#save-template-modal")
        modal.locator("#template-name").fill("Test User Template")
        modal.locator("#template-description").fill("For E2E testing")
        modal.locator("#template-category-select").select_option("custom")
        modal.locator('button:has-text("Save Template")').click()

        # Wait for success
        page.wait_for_timeout(500)

        # Navigate to templates page
        page.goto(f"{app_server}/admin/templates")
        return page

    def test_user_template_displayed(self, page_with_user_template: Page):
        """Test that user template is displayed on templates page."""
        template_card = page_with_user_template.locator(
            '.template-card:has-text("Test User Template")'
        ).first
        expect(template_card).to_be_visible()

        # Should show description
        expect(template_card.locator(".template-description")).to_have_text("For E2E testing")

    def test_edit_template(self, page_with_user_template: Page):
        """Test editing a user template."""
        template_card = page_with_user_template.locator(
            '.template-card:has-text("Test User Template")'
        ).first

        # Click edit button
        template_card.locator('button:has-text("Edit")').click()

        # Edit modal should appear
        modal = page_with_user_template.locator("#edit-modal")
        expect(modal).to_be_visible()

        # Change the name
        modal.locator("#edit-name").fill("Updated Template Name")
        modal.locator('button:has-text("Save Changes")').click()

        # Wait for update
        page_with_user_template.wait_for_timeout(500)

        # Verify name changed
        expect(
            page_with_user_template.locator('.template-card:has-text("Updated Template Name")')
        ).to_be_visible()

    def test_delete_template(self, page_with_user_template: Page):
        """Test deleting a user template."""
        # Count templates before deletion
        initial_count = page_with_user_template.locator(".template-card").count()

        template_card = page_with_user_template.locator(
            '.template-card:has-text("Test User Template")'
        ).first

        # Accept confirmation dialog
        page_with_user_template.on("dialog", lambda dialog: dialog.accept())

        # Click delete button
        template_card.locator('button:has-text("Delete")').click()

        # Wait for deletion
        page_with_user_template.wait_for_timeout(500)

        # Should have one less template
        expect(page_with_user_template.locator(".template-card")).to_have_count(initial_count - 1)

    def test_delete_template_cancel(self, page_with_user_template: Page):
        """Test that canceling delete keeps the template."""
        template_card = page_with_user_template.locator(
            '.template-card:has-text("Test User Template")'
        ).first

        # Dismiss confirmation dialog
        page_with_user_template.on("dialog", lambda dialog: dialog.dismiss())

        # Click delete button
        template_card.locator('button:has-text("Delete")').click()

        # Wait
        page_with_user_template.wait_for_timeout(500)

        # Template should still exist
        expect(template_card).to_be_visible()

    def test_use_user_template(self, page_with_user_template: Page, app_server: str):
        """Test creating a screen from a user template."""
        # Accept confirmation dialog
        page_with_user_template.on("dialog", lambda dialog: dialog.accept())

        template_card = page_with_user_template.locator(
            '.template-card:has-text("Test User Template")'
        ).first

        # Click use button
        template_card.locator('button:has-text("Use")').click()

        # Should redirect to screens page
        page_with_user_template.wait_for_url(re.compile(r"/admin/screens"))

        # Should have screens visible (at least one was created)
        expect(page_with_user_template.locator(".screen-card").first).to_be_visible()


class TestTemplateGalleryMyTemplates:
    """Tests for My Templates tab in the template selection gallery."""

    @pytest.fixture
    def page_with_user_template(self, page: Page, app_server: str):
        """Set up with a user template created."""
        page.goto(f"{app_server}/admin/screens")

        # Create a screen from template
        page.locator("#create-screen").click()
        page.locator('.template-option-btn:has-text("Use a Template")').click()
        page.locator(".template-card").first.click()
        page.locator('button:has-text("Use This Template")').click()
        page.wait_for_timeout(500)

        # Save as template
        card = page.locator(".screen-card").first
        card.locator('button:has-text("Screen Actions")').click()
        card.locator('button:has-text("Save as Template")').click()

        modal = page.locator("#save-template-modal")
        modal.locator("#template-name").fill("My Custom Template")
        modal.locator("#template-category-select").select_option("custom")
        modal.locator('button:has-text("Save Template")').click()

        page.wait_for_timeout(500)
        return page

    def test_my_templates_tab_visible(self, page_with_user_template: Page):
        """Test that My Templates tab is visible when user has templates."""
        # Open template gallery
        page_with_user_template.locator("#create-screen").click()
        page_with_user_template.locator('.template-option-btn:has-text("Use a Template")').click()

        # My Templates tab should be visible
        my_templates_tab = page_with_user_template.locator('.type-tab:has-text("My Templates")')
        expect(my_templates_tab).to_be_visible()

    def test_my_templates_shows_user_templates(self, page_with_user_template: Page):
        """Test that My Templates tab shows user's templates."""
        # Open template gallery
        page_with_user_template.locator("#create-screen").click()
        page_with_user_template.locator('.template-option-btn:has-text("Use a Template")').click()

        # Click My Templates tab
        page_with_user_template.locator('.type-tab:has-text("My Templates")').click()

        # Wait for filter
        page_with_user_template.wait_for_timeout(300)

        # Should see user template
        expect(
            page_with_user_template.locator('.template-card:has-text("My Custom Template")').first
        ).to_be_visible()

    def test_create_screen_from_my_template_in_gallery(self, page_with_user_template: Page):
        """Test creating a screen from user template via gallery."""
        initial_count = page_with_user_template.locator(".screen-card").count()

        # Open template gallery
        page_with_user_template.locator("#create-screen").click()
        page_with_user_template.locator('.template-option-btn:has-text("Use a Template")').click()

        # Click My Templates tab
        page_with_user_template.locator('.type-tab:has-text("My Templates")').click()
        page_with_user_template.wait_for_timeout(300)

        # Click on user template
        page_with_user_template.locator(
            '.template-card:has-text("My Custom Template")'
        ).first.click()

        # Click Use This Template
        page_with_user_template.locator('button:has-text("Use This Template")').click()

        # Should create new screen
        expect(page_with_user_template.locator(".screen-card")).to_have_count(initial_count + 1)


class TestTemplateFilterOnManagePage:
    """Tests for filtering on the templates management page."""

    @pytest.fixture
    def page_with_templates(self, page: Page, app_server: str):
        """Set up with multiple user templates in different categories."""
        page.goto(f"{app_server}/admin/screens")

        categories = ["restaurant", "education"]
        for category in categories:
            # Create a screen from template
            page.locator("#create-screen").click()
            page.locator('.template-option-btn:has-text("Use a Template")').click()
            page.locator(".template-card").first.click()
            page.locator('button:has-text("Use This Template")').click()
            page.wait_for_timeout(500)

            # Save as template with specific category
            card = page.locator(".screen-card").first
            card.locator('button:has-text("Screen Actions")').click()
            card.locator('button:has-text("Save as Template")').click()

            modal = page.locator("#save-template-modal")
            modal.locator("#template-name").fill(f"Template {category.title()}")
            modal.locator("#template-category-select").select_option(category)
            modal.locator('button:has-text("Save Template")').click()
            page.wait_for_timeout(500)

        page.goto(f"{app_server}/admin/templates")
        return page

    def test_category_filter_dropdown(self, page_with_templates: Page):
        """Test that category filter dropdown exists."""
        filter_dropdown = page_with_templates.locator("#category-filter")
        expect(filter_dropdown).to_be_visible()

    def test_filter_by_category(self, page_with_templates: Page, app_server: str):
        """Test filtering templates by category."""
        # Filter by restaurant
        page_with_templates.locator("#category-filter").select_option("restaurant")

        # Wait for page reload with filter
        page_with_templates.wait_for_url(re.compile(r"category=restaurant"))

        # Should only show restaurant template
        expect(
            page_with_templates.locator('.template-card:has-text("Template Restaurant")').first
        ).to_be_visible()
        expect(
            page_with_templates.locator('.template-card:has-text("Template Education")')
        ).not_to_be_visible()

    def test_clear_category_filter(self, page_with_templates: Page, app_server: str):
        """Test clearing the category filter shows all templates."""
        # First filter by category
        page_with_templates.locator("#category-filter").select_option("restaurant")
        page_with_templates.wait_for_url(re.compile(r"category=restaurant"))

        # Clear filter
        page_with_templates.locator("#category-filter").select_option("")

        # Wait for page reload without filter
        page_with_templates.wait_for_timeout(500)

        # Should show both templates
        expect(
            page_with_templates.locator('.template-card:has-text("Template Restaurant")').first
        ).to_be_visible()
        expect(
            page_with_templates.locator('.template-card:has-text("Template Education")').first
        ).to_be_visible()
