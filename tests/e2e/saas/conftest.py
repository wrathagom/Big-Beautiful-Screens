"""SaaS E2E test configuration for Playwright tests.

These tests run against a deployed environment (dev/staging) with real
Clerk authentication and Stripe billing in test mode.

Required environment variables:
    E2E_BASE_URL: The deployed app URL (e.g., https://bbs-dev.up.railway.app)
    E2E_TEST_EMAIL: Test user email (created in Clerk test mode)
    E2E_TEST_PASSWORD: Test user password

Optional environment variables:
    E2E_HEADLESS: Run browser in headless mode (default: true)
    E2E_SLOW_MO: Slow down browser actions by N ms (default: 0)
"""

import os
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Page


def get_env_or_skip(var_name: str) -> str:
    """Get an environment variable or skip the test."""
    value = os.environ.get(var_name)
    if not value:
        pytest.skip(f"Environment variable {var_name} not set")
    return value


@pytest.fixture(scope="session")
def base_url() -> str:
    """Get the deployed SaaS environment URL."""
    return get_env_or_skip("E2E_BASE_URL")


@pytest.fixture(scope="session")
def test_credentials() -> dict[str, str]:
    """Get test user credentials."""
    return {
        "email": get_env_or_skip("E2E_TEST_EMAIL"),
        "password": get_env_or_skip("E2E_TEST_PASSWORD"),
    }


@pytest.fixture(scope="session")
def browser_context_args() -> dict:
    """Configure browser context for SaaS tests."""
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="session")
def screenshots_dir() -> Path:
    """Directory for saving test screenshots."""
    path = Path(__file__).parent / "screenshots"
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture
def saas_context(browser: Browser, browser_context_args: dict) -> BrowserContext:
    """Create a fresh browser context for each test."""
    context = browser.new_context(**browser_context_args)
    context.set_default_timeout(15000)  # 15 second timeout for SaaS tests
    yield context
    context.close()


@pytest.fixture
def page(saas_context: BrowserContext) -> Page:
    """Create a fresh page for each test."""
    page = saas_context.new_page()
    yield page
    page.close()


@pytest.fixture
def authenticated_page(
    browser: Browser,
    browser_context_args: dict,
    base_url: str,
    test_credentials: dict[str, str],
) -> Page:
    """Provide a page with an authenticated Clerk session.

    This fixture:
    1. Creates a new browser context
    2. Navigates to the app
    3. Completes Clerk sign-in flow
    4. Returns the authenticated page
    """
    context = browser.new_context(**browser_context_args)
    context.set_default_timeout(30000)  # 30 second timeout for auth
    page = context.new_page()

    try:
        # Navigate to admin (will redirect to sign-in)
        page.goto(f"{base_url}/admin/screens")

        # Wait for Clerk sign-in form to load
        # Clerk renders its own UI components
        page.wait_for_selector(
            'input[name="identifier"], input[type="email"], [data-testid="sign-in-email-input"]',
            timeout=10000,
        )

        # Enter email
        email_input = page.locator(
            'input[name="identifier"], input[type="email"], [data-testid="sign-in-email-input"]'
        ).first
        email_input.fill(test_credentials["email"])

        # Click continue/next button
        continue_btn = page.locator(
            'button:has-text("Continue"), button:has-text("Next"), button[type="submit"]'
        ).first
        continue_btn.click()

        # Wait for password field
        page.wait_for_selector('input[name="password"], input[type="password"]', timeout=10000)

        # Enter password
        password_input = page.locator('input[name="password"], input[type="password"]').first
        password_input.fill(test_credentials["password"])

        # Click sign in
        sign_in_btn = page.locator(
            'button:has-text("Sign in"), button:has-text("Continue"), button[type="submit"]'
        ).first
        sign_in_btn.click()

        # Wait for redirect to admin dashboard
        page.wait_for_url(f"{base_url}/admin/*", timeout=15000)

        yield page

    finally:
        page.close()
        context.close()


@pytest.fixture
def save_screenshot(screenshots_dir: Path):
    """Fixture to save screenshots on test failure or manually."""

    def _save(page: Page, name: str):
        path = screenshots_dir / f"{name}.png"
        page.screenshot(path=str(path))
        print(f"Screenshot saved: {path}")
        return path

    return _save
