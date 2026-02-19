"""Utilities for SaaS integration testing.

Provides helpers for:
- Loading webhook fixtures
- Mocking Clerk authentication
- Generating webhook signatures
- Database setup/teardown
"""

import hashlib
import hmac
import json
import time
from base64 import b64encode
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

# Path to fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ============== Fixture Loading ==============


def load_fixture(fixture_path: str) -> dict:
    """Load a JSON fixture file.

    Args:
        fixture_path: Path relative to fixtures/, e.g. "recorded/clerk_user_updated.json"

    Returns:
        Parsed JSON as dict
    """
    full_path = FIXTURES_DIR / fixture_path
    if not full_path.exists():
        raise FileNotFoundError(f"Fixture not found: {full_path}")
    return json.loads(full_path.read_text())


def load_fixture_raw(fixture_path: str) -> bytes:
    """Load a fixture file as raw bytes (for webhook signature testing)."""
    full_path = FIXTURES_DIR / fixture_path
    if not full_path.exists():
        raise FileNotFoundError(f"Fixture not found: {full_path}")
    return full_path.read_bytes()


# ============== Clerk Auth Mocking ==============


class MockClerkUser:
    """Mock Clerk authenticated user for testing."""

    def __init__(
        self,
        user_id: str = "user_test123",
        email: str = "test@example.com",
        name: str = "Test User",
        org_id: str | None = None,
        org_role: str | None = None,
    ):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.org_id = org_id
        self.org_role = org_role


def mock_clerk_auth(user: MockClerkUser | None = None):
    """Create a context manager that mocks Clerk authentication.

    Usage:
        with mock_clerk_auth(MockClerkUser(user_id="user_123")):
            response = client.get("/api/v1/billing/subscription")
    """
    if user is None:
        user = MockClerkUser()

    # Create the AuthUser object that get_current_user would return
    from app.auth import AuthUser

    auth_user = AuthUser(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        org_id=user.org_id,
        org_role=user.org_role,
    )

    async def mock_get_current_user(*args, **kwargs):
        return auth_user

    async def mock_require_auth(*args, **kwargs):
        return auth_user

    return patch.multiple(
        "app.auth",
        get_current_user=mock_get_current_user,
        require_auth=mock_require_auth,
    )


def get_auth_override(user: MockClerkUser | None = None):
    """Get dependency override dict for FastAPI testing.

    Usage:
        app.dependency_overrides.update(get_auth_override(mock_user))
    """
    if user is None:
        user = MockClerkUser()

    from app.auth import AuthUser, get_current_user, require_auth

    auth_user = AuthUser(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        org_id=user.org_id,
        org_role=user.org_role,
    )

    async def override_get_current_user():
        return auth_user

    async def override_require_auth():
        return auth_user

    return {
        get_current_user: override_get_current_user,
        require_auth: override_require_auth,
    }


# ============== Webhook Signature Helpers ==============


def generate_clerk_signature(payload: bytes, secret: str) -> tuple[str, str, str]:
    """Generate Clerk webhook signature headers.

    Returns:
        Tuple of (svix_id, svix_timestamp, svix_signature)
    """
    svix_id = "msg_test123"
    svix_timestamp = str(int(time.time()))

    signed_payload = f"{svix_timestamp}.{payload.decode('utf-8')}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_b64 = b64encode(signature).decode("utf-8")

    return svix_id, svix_timestamp, f"v1,{signature_b64}"


def generate_stripe_signature(payload: bytes, secret: str) -> str:
    """Generate Stripe webhook signature header.

    Returns:
        The stripe-signature header value
    """
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"t={timestamp},v1={signature}"


# ============== Database Helpers ==============


class SaaSTestDatabase:
    """Helper for managing test database state in SaaS tests.

    Provides methods to:
    - Create test users with specific plans
    - Set up Stripe customer associations
    - Clean up after tests
    """

    def __init__(self, db):
        self.db = db
        self._created_users: list[str] = []
        self._created_screens: list[str] = []

    async def create_test_user(
        self,
        user_id: str = "user_test123",
        email: str = "test@example.com",
        name: str = "Test User",
        plan: str = "free",
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        subscription_status: str = "inactive",
    ) -> dict:
        """Create a test user with specified attributes."""
        await self.db.create_or_update_user(
            user_id=user_id,
            email=email,
            name=name,
            plan=plan,
        )

        # Update plan and subscription if specified
        if plan != "free" or stripe_subscription_id:
            await self.db.update_user_plan(
                user_id=user_id,
                plan=plan,
                subscription_id=stripe_subscription_id,
                subscription_status=subscription_status,
            )

        if stripe_customer_id:
            await self.db.set_stripe_customer_id(user_id, stripe_customer_id)

        self._created_users.append(user_id)
        return await self.db.get_user(user_id)

    async def get_user(self, user_id: str) -> dict | None:
        """Get a user by ID."""
        return await self.db.get_user(user_id)

    async def cleanup(self):
        """Clean up all created test data."""
        import contextlib

        for user_id in self._created_users:
            with contextlib.suppress(Exception):
                await self.db.delete_user(user_id)
        self._created_users.clear()


# ============== Test App Factory ==============


def create_saas_test_app():
    """Create a test app configured for SaaS mode.

    Returns a tuple of (app, client, db_helper)
    """
    import os

    # Set SaaS mode environment variables
    os.environ["APP_MODE"] = "saas"
    os.environ["CLERK_SECRET_KEY"] = "sk_test_fake"
    os.environ["CLERK_PUBLISHABLE_KEY"] = "pk_test_fake"
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
    os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_fake"
    os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_test_fake"

    # Import app after setting env vars
    from app.main import app

    client = TestClient(app)

    return app, client
