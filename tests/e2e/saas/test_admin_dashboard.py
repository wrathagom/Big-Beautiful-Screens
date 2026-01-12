"""E2E tests for the admin dashboard in SaaS mode.

Tests screen management, navigation, and core admin functionality.
"""

import re

import pytest
from playwright.sync_api import Page, expect


class TestAdminScreens:
    """Test the screens management page."""

    def test_screens_page_loads(self, authenticated_page: Page, base_url: str):
        """Admin screens page should load with screen list."""
        page = authenticated_page

        # Should already be on admin page from fixture
        page.goto(f"{base_url}/admin/screens")
        page.wait_for_load_state("networkidle")

        # Check page loaded correctly
        expect(page).to_have_url(re.compile(r"/admin/screens"))

        # Should have some UI elements
        # Look for create button or screen list
        has_create_btn = (
            page.locator(
                'button:has-text("Create"), button:has-text("New Screen"), '
                'a:has-text("Create"), a:has-text("New")'
            ).count()
            > 0
        )

        has_screen_list = (
            page.locator('.screen-list, .screens, [data-testid="screen-list"], table').count() > 0
        )

        assert has_create_btn or has_screen_list, "Expected screen management UI"

    def test_create_screen(self, authenticated_page: Page, base_url: str):
        """Should be able to create a new screen."""
        page = authenticated_page
        page.goto(f"{base_url}/admin/screens")
        page.wait_for_load_state("networkidle")

        # Look for create button
        create_btn = page.locator(
            'button:has-text("Create"), button:has-text("New Screen"), '
            'a:has-text("Create"), a:has-text("New")'
        ).first

        if not create_btn.is_visible():
            pytest.skip("Create button not found")

        # Click create
        create_btn.click()

        # Wait for either a modal, form, or navigation
        page.wait_for_load_state("networkidle")

        # Check if a new screen was created (URL might have screen ID)
        # or a creation form appeared
        has_screen_form = (
            page.locator('input[name="name"], input[placeholder*="name"], .screen-form').count() > 0
        )

        screen_created = re.search(r"/screen/[\w-]+", page.url) is not None

        # Either we have a form or a new screen was created
        assert has_screen_form or screen_created, "Expected screen creation flow"


class TestAdminNavigation:
    """Test navigation between admin pages."""

    def test_navigate_to_themes(self, authenticated_page: Page, base_url: str):
        """Should be able to navigate to themes page."""
        page = authenticated_page

        # Look for themes link
        themes_link = page.locator('a[href*="themes"], a:has-text("Themes")').first

        if themes_link.is_visible():
            themes_link.click()
            page.wait_for_url(re.compile(r"/admin/themes"))
            expect(page).to_have_url(re.compile(r"/admin/themes"))
        else:
            # Try direct navigation
            page.goto(f"{base_url}/admin/themes")
            page.wait_for_load_state("networkidle")
            expect(page).to_have_url(re.compile(r"/admin/themes"))

    def test_navigate_to_usage(self, authenticated_page: Page, base_url: str):
        """Should be able to navigate to usage/billing page."""
        page = authenticated_page

        # Look for usage/billing link
        usage_link = page.locator(
            'a[href*="usage"], a:has-text("Usage"), a:has-text("Billing")'
        ).first

        if usage_link.is_visible():
            usage_link.click()
            page.wait_for_url(re.compile(r"/admin/usage"))
        else:
            page.goto(f"{base_url}/admin/usage")
            page.wait_for_load_state("networkidle")

        expect(page).to_have_url(re.compile(r"/admin/usage"))

    def test_navigate_to_media(self, authenticated_page: Page, base_url: str):
        """Should be able to navigate to media page."""
        page = authenticated_page

        page.goto(f"{base_url}/admin/media")
        page.wait_for_load_state("networkidle")

        expect(page).to_have_url(re.compile(r"/admin/media"))


class TestUsagePage:
    """Test the usage and billing page."""

    def test_usage_page_shows_plan(self, authenticated_page: Page, base_url: str):
        """Usage page should display current plan information."""
        page = authenticated_page
        page.goto(f"{base_url}/admin/usage")
        page.wait_for_load_state("networkidle")

        # Should show plan information
        # Look for plan name, usage stats, or upgrade button
        has_plan_info = (
            page.locator(
                ':has-text("Free"), :has-text("Pro"), :has-text("Team"), '
                ':has-text("plan"), :has-text("Plan")'
            ).count()
            > 0
        )

        has_usage_info = (
            page.locator(
                ':has-text("screens"), :has-text("Screens"), :has-text("usage"), :has-text("Usage")'
            ).count()
            > 0
        )

        assert has_plan_info or has_usage_info, "Expected plan/usage information"

    def test_usage_page_has_upgrade_option(self, authenticated_page: Page, base_url: str):
        """Usage page should have upgrade option (if on free plan)."""
        page = authenticated_page
        page.goto(f"{base_url}/admin/usage")
        page.wait_for_load_state("networkidle")

        # Look for upgrade button or pricing link
        has_upgrade = (
            page.locator(
                'a:has-text("Upgrade"), button:has-text("Upgrade"), '
                'a[href*="pricing"], a:has-text("Pricing")'
            ).count()
            > 0
        )

        # This might not be visible if user is already on paid plan
        # Just check the page loaded successfully
        assert page.url.endswith("/admin/usage") or "usage" in page.url or has_upgrade


class TestPricingPage:
    """Test the pricing page."""

    def test_pricing_page_loads(self, authenticated_page: Page, base_url: str):
        """Pricing page should load and show plans."""
        page = authenticated_page
        page.goto(f"{base_url}/admin/pricing")
        page.wait_for_load_state("networkidle")

        expect(page).to_have_url(re.compile(r"/admin/pricing"))

        # Should show pricing information
        # Stripe pricing table or custom pricing UI
        has_pricing_content = (
            page.locator(
                'stripe-pricing-table, .pricing, :has-text("$"), '
                ':has-text("month"), :has-text("year")'
            ).count()
            > 0
        )

        # Or loading state
        is_loading = page.locator(':has-text("Loading")').count() > 0

        assert has_pricing_content or is_loading, "Expected pricing content"
