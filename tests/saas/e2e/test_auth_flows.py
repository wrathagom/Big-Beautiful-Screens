"""E2E tests for Clerk authentication flows.

Tests sign-in, sign-out, and protected route behavior.
"""

import re

import pytest
from playwright.sync_api import Page, expect


class TestSignIn:
    """Test Clerk sign-in flows."""

    def test_unauthenticated_redirect_to_signin(self, page: Page, base_url: str):
        """Unauthenticated users should be redirected to sign-in."""
        # Try to access protected admin page
        page.goto(f"{base_url}/admin/screens")

        # Should be redirected to Clerk sign-in
        # Clerk hosted sign-in URLs vary, but should contain "sign-in" or be a Clerk domain
        page.wait_for_load_state("networkidle")

        # Check we're on a sign-in page (either hosted Clerk or embedded)
        current_url = page.url
        is_signin_page = (
            "sign-in" in current_url
            or "clerk" in current_url
            or page.locator('input[name="identifier"], input[type="email"]').count() > 0
        )
        assert is_signin_page, f"Expected sign-in page, got: {current_url}"

    def test_successful_signin(self, page: Page, base_url: str, test_credentials: dict[str, str]):
        """Valid credentials should authenticate and redirect to admin."""
        # Go to admin (redirects to sign-in)
        page.goto(f"{base_url}/admin/screens")

        # Wait for sign-in form
        page.wait_for_selector('input[name="identifier"], input[type="email"]', timeout=10000)

        # Enter email
        email_input = page.locator('input[name="identifier"], input[type="email"]').first
        email_input.fill(test_credentials["email"])

        # Click continue
        page.locator(
            'button:has-text("Continue"), button:has-text("Next"), button[type="submit"]'
        ).first.click()

        # Wait for and fill password
        page.wait_for_selector('input[name="password"], input[type="password"]')
        password_input = page.locator('input[name="password"], input[type="password"]').first
        password_input.fill(test_credentials["password"])

        # Sign in
        page.locator(
            'button:has-text("Sign in"), button:has-text("Continue"), button[type="submit"]'
        ).first.click()

        # Should redirect to admin
        page.wait_for_url(re.compile(rf"{base_url}/admin"), timeout=15000)

        # Verify we're on the admin page
        expect(page).to_have_url(re.compile(r"/admin"))

    def test_invalid_credentials_shows_error(
        self, page: Page, base_url: str, test_credentials: dict[str, str]
    ):
        """Invalid credentials should show an error message."""
        page.goto(f"{base_url}/admin/screens")

        # Wait for sign-in form
        page.wait_for_selector('input[name="identifier"], input[type="email"]', timeout=10000)

        # Enter email
        email_input = page.locator('input[name="identifier"], input[type="email"]').first
        email_input.fill(test_credentials["email"])

        # Click continue
        page.locator(
            'button:has-text("Continue"), button:has-text("Next"), button[type="submit"]'
        ).first.click()

        # Wait for and fill WRONG password
        page.wait_for_selector('input[name="password"], input[type="password"]')
        password_input = page.locator('input[name="password"], input[type="password"]').first
        password_input.fill("wrong_password_12345!")

        # Try to sign in
        page.locator(
            'button:has-text("Sign in"), button:has-text("Continue"), button[type="submit"]'
        ).first.click()

        # Should show error (Clerk shows various error messages)
        page.wait_for_selector(
            '[data-localization-key*="error"], .cl-formFieldError, [role="alert"], .error',
            timeout=10000,
        )

        # Should still be on sign-in page
        assert (
            "admin/screens" not in page.url or page.locator('input[type="password"]').is_visible()
        )


class TestSignOut:
    """Test sign-out functionality."""

    def test_signout_clears_session(self, authenticated_page: Page, base_url: str):
        """Signing out should clear the session and redirect."""
        page = authenticated_page

        # Verify we're authenticated (on admin page)
        expect(page).to_have_url(re.compile(r"/admin"))

        # Look for sign-out button/link
        # The app may have various ways to sign out
        signout_btn = page.locator(
            'button:has-text("Sign out"), a:has-text("Sign out"), '
            'button:has-text("Logout"), a:has-text("Logout"), '
            '[data-testid="sign-out"]'
        ).first

        if signout_btn.is_visible():
            signout_btn.click()
            page.wait_for_load_state("networkidle")

            # Try to access protected page again
            page.goto(f"{base_url}/admin/screens")
            page.wait_for_load_state("networkidle")

            # Should be redirected to sign-in
            current_url = page.url
            is_signin_page = (
                "sign-in" in current_url
                or "clerk" in current_url
                or page.locator('input[name="identifier"], input[type="email"]').count() > 0
            )
            assert is_signin_page, f"Expected sign-in redirect after logout, got: {current_url}"
        else:
            pytest.skip("Sign out button not found in current UI")


class TestProtectedRoutes:
    """Test that protected routes require authentication."""

    @pytest.mark.parametrize(
        "route",
        [
            "/admin/screens",
            "/admin/themes",
            "/admin/usage",
            "/admin/pricing",
            "/admin/media",
        ],
    )
    def test_admin_routes_require_auth(self, page: Page, base_url: str, route: str):
        """Admin routes should redirect to sign-in when not authenticated."""
        page.goto(f"{base_url}{route}")
        page.wait_for_load_state("networkidle")

        # Should be redirected to sign-in or show sign-in form
        current_url = page.url
        has_signin_form = page.locator('input[name="identifier"], input[type="email"]').count() > 0

        assert (
            "sign-in" in current_url
            or "clerk" in current_url
            or has_signin_form
            or route not in current_url  # Redirected away
        ), f"Route {route} should require auth, but got: {current_url}"

    def test_public_screen_view_no_auth_required(self, page: Page, base_url: str):
        """Public screen view should not require authentication."""
        # The screen view page should be public
        # We'll try to access a demo screen or any screen
        page.goto(f"{base_url}/screen/demo")

        # Should not redirect to sign-in
        # Either shows the screen or a 404, but not sign-in
        page.wait_for_load_state("networkidle")

        assert "sign-in" not in page.url.lower()
        assert "clerk" not in page.url.lower()
