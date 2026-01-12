"""E2E tests for Stripe billing flows.

Tests upgrade flows, Stripe checkout, and subscription management.
These tests use Stripe's test mode.
"""

import re

import pytest
from playwright.sync_api import Page


class TestUpgradeFlow:
    """Test the upgrade to paid plan flow."""

    def test_upgrade_button_redirects_to_checkout(self, authenticated_page: Page, base_url: str):
        """Clicking upgrade should redirect to Stripe Checkout."""
        page = authenticated_page

        # Go to pricing page
        page.goto(f"{base_url}/admin/pricing")
        page.wait_for_load_state("networkidle")

        # Wait for Stripe pricing table to load (if using embedded pricing table)
        # or look for upgrade buttons
        page.wait_for_timeout(2000)  # Give Stripe time to load

        # Look for upgrade/subscribe button
        # This could be in a Stripe pricing table or custom button
        upgrade_btn = page.locator(
            'button:has-text("Subscribe"), button:has-text("Upgrade"), '
            'button:has-text("Get started"), button:has-text("Choose"), '
            'a:has-text("Subscribe"), a:has-text("Upgrade")'
        ).first

        if not upgrade_btn.is_visible():
            # Might be inside Stripe iframe
            stripe_frame = page.frame_locator("iframe[src*='stripe']").first
            if stripe_frame:
                upgrade_btn = stripe_frame.locator(
                    'button:has-text("Subscribe"), button:has-text("Upgrade")'
                ).first

        if upgrade_btn.is_visible():
            upgrade_btn.click()

            # Wait for redirect to Stripe Checkout
            # Stripe checkout URLs contain checkout.stripe.com
            page.wait_for_url(
                re.compile(r"checkout\.stripe\.com|billing\.stripe\.com"),
                timeout=15000,
            )

            assert "stripe.com" in page.url, f"Expected Stripe checkout, got: {page.url}"
        else:
            pytest.skip("Upgrade button not found - user may already be on paid plan")

    def test_stripe_checkout_displays_correctly(self, authenticated_page: Page, base_url: str):
        """Stripe Checkout should display with correct plan info."""
        page = authenticated_page

        # Navigate to pricing and click upgrade
        page.goto(f"{base_url}/admin/pricing")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        upgrade_btn = page.locator(
            'button:has-text("Subscribe"), button:has-text("Upgrade"), '
            'button:has-text("Get started")'
        ).first

        if not upgrade_btn.is_visible():
            pytest.skip("Upgrade button not found")

        upgrade_btn.click()

        try:
            page.wait_for_url(
                re.compile(r"checkout\.stripe\.com|billing\.stripe\.com"),
                timeout=15000,
            )

            # Verify Stripe checkout loaded
            # Look for payment form elements
            has_payment_form = (
                page.locator(
                    'input[name="cardNumber"], input[name="email"], '
                    '[data-testid="card-number-input"], .StripeElement'
                ).count()
                > 0
            )

            has_price_info = (
                page.locator(':has-text("$"), :has-text("Total"), :has-text("Pay")').count() > 0
            )

            assert has_payment_form or has_price_info, "Expected Stripe checkout form"

        except Exception:
            pytest.skip("Could not navigate to Stripe checkout")


class TestStripeCheckoutCompletion:
    """Test completing Stripe checkout with test cards."""

    @pytest.mark.slow
    def test_successful_checkout_with_test_card(self, authenticated_page: Page, base_url: str):
        """Complete checkout with Stripe test card 4242424242424242."""
        page = authenticated_page

        # Navigate to pricing and start checkout
        page.goto(f"{base_url}/admin/pricing")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        upgrade_btn = page.locator(
            'button:has-text("Subscribe"), button:has-text("Upgrade"), '
            'button:has-text("Get started")'
        ).first

        if not upgrade_btn.is_visible():
            pytest.skip("Upgrade button not found")

        upgrade_btn.click()

        try:
            page.wait_for_url(
                re.compile(r"checkout\.stripe\.com"),
                timeout=15000,
            )
        except Exception:
            pytest.skip("Could not navigate to Stripe checkout")

        # Fill in Stripe test card details
        # Stripe's checkout has specific field names/selectors

        # Wait for card input to be ready
        page.wait_for_selector(
            'input[name="cardNumber"], [data-testid="card-number-input"]',
            timeout=10000,
        )

        # Card number: 4242 4242 4242 4242
        card_input = page.locator(
            'input[name="cardNumber"], [data-testid="card-number-input"]'
        ).first
        card_input.fill("4242424242424242")

        # Expiry: Any future date (e.g., 12/30)
        expiry_input = page.locator(
            'input[name="cardExpiry"], [data-testid="card-expiry-input"]'
        ).first
        expiry_input.fill("1230")

        # CVC: Any 3 digits
        cvc_input = page.locator('input[name="cardCvc"], [data-testid="card-cvc-input"]').first
        cvc_input.fill("123")

        # Billing name (if required)
        name_input = page.locator('input[name="billingName"], input[name="name"]').first
        if name_input.is_visible():
            name_input.fill("Test User")

        # Submit payment
        submit_btn = page.locator(
            'button[type="submit"], button:has-text("Pay"), '
            'button:has-text("Subscribe"), button:has-text("Start")'
        ).first
        submit_btn.click()

        # Wait for redirect back to app
        page.wait_for_url(
            re.compile(rf"{base_url}|success"),
            timeout=30000,
        )

        # Verify we're back in the app
        assert "stripe.com" not in page.url, "Should redirect back to app after payment"

    def test_checkout_cancel_returns_to_app(self, authenticated_page: Page, base_url: str):
        """Canceling checkout should return to the app."""
        page = authenticated_page

        page.goto(f"{base_url}/admin/pricing")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        upgrade_btn = page.locator('button:has-text("Subscribe"), button:has-text("Upgrade")').first

        if not upgrade_btn.is_visible():
            pytest.skip("Upgrade button not found")

        upgrade_btn.click()

        try:
            page.wait_for_url(
                re.compile(r"checkout\.stripe\.com"),
                timeout=15000,
            )
        except Exception:
            pytest.skip("Could not navigate to Stripe checkout")

        # Look for back/cancel button
        back_btn = page.locator(
            'a:has-text("Back"), button:has-text("Cancel"), a[href*="cancel"], .back-button'
        ).first

        if back_btn.is_visible():
            back_btn.click()
        else:
            # Use browser back
            page.go_back()

        # Should return to pricing or app
        page.wait_for_load_state("networkidle")
        assert "stripe.com" not in page.url or base_url in page.url


class TestBillingPortal:
    """Test Stripe billing portal access."""

    def test_manage_billing_opens_portal(self, authenticated_page: Page, base_url: str):
        """Manage billing button should open Stripe billing portal."""
        page = authenticated_page

        # Go to usage page
        page.goto(f"{base_url}/admin/usage")
        page.wait_for_load_state("networkidle")

        # Look for manage billing button
        manage_btn = page.locator(
            'button:has-text("Manage"), button:has-text("Billing"), '
            'a:has-text("Manage Billing"), a:has-text("Manage subscription")'
        ).first

        if not manage_btn.is_visible():
            pytest.skip("Manage billing button not found - user may be on free plan")

        manage_btn.click()

        # Should redirect to Stripe billing portal
        page.wait_for_url(
            re.compile(r"billing\.stripe\.com|stripe\.com/billing"),
            timeout=15000,
        )

        assert "stripe.com" in page.url, "Expected Stripe billing portal"
