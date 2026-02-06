"""Integration tests for Clerk and Stripe webhook handlers.

These tests verify that webhooks correctly sync user data without
accidentally overwriting important fields like subscription plan.

Uses mocked database to test webhook handler logic independently.
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.saas.saas_utils import load_fixture


@pytest.fixture(scope="module", autouse=True)
def saas_environment():
    """Set up SaaS environment for all tests in this module."""
    # Save original env vars
    original_env = {
        "TESTING": os.environ.get("TESTING"),
        "APP_MODE": os.environ.get("APP_MODE"),
        "CLERK_SECRET_KEY": os.environ.get("CLERK_SECRET_KEY"),
        "CLERK_PUBLISHABLE_KEY": os.environ.get("CLERK_PUBLISHABLE_KEY"),
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "STRIPE_SECRET_KEY": os.environ.get("STRIPE_SECRET_KEY"),
        "STRIPE_WEBHOOK_SECRET": os.environ.get("STRIPE_WEBHOOK_SECRET"),
    }

    # Set SaaS environment
    os.environ["TESTING"] = "1"
    os.environ["APP_MODE"] = "saas"
    os.environ["CLERK_SECRET_KEY"] = "sk_test_fake"
    os.environ["CLERK_PUBLISHABLE_KEY"] = "pk_test_fake"
    os.environ["DATABASE_URL"] = "postgresql://fake:fake@localhost/fake"
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
    os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_fake"

    # Clear cached settings
    from app.config import get_settings

    get_settings.cache_clear()

    yield

    # Restore original env vars
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    get_settings.cache_clear()


class MockDatabase:
    """Mock database for testing SaaS functionality."""

    def __init__(self):
        self.users = {}
        self.organizations = {}

    async def get_user(self, user_id: str):
        return self.users.get(user_id)

    async def get_user_by_stripe_customer(self, customer_id: str):
        for user in self.users.values():
            if user.get("stripe_customer_id") == customer_id:
                return user
        return None

    async def create_or_update_user(
        self, user_id: str, email: str, name: str | None = None, plan: str = "free"
    ):
        if user_id in self.users:
            # Update existing user (but NOT the plan - this is the fix!)
            self.users[user_id]["email"] = email
            self.users[user_id]["name"] = name
        else:
            # Create new user
            self.users[user_id] = {
                "id": user_id,
                "email": email,
                "name": name,
                "plan": plan,
                "stripe_customer_id": None,
                "stripe_subscription_id": None,
                "subscription_status": "inactive",
            }
        return self.users[user_id]

    async def update_user_plan(
        self,
        user_id: str,
        plan: str,
        subscription_id: str | None = None,
        subscription_status: str = "inactive",
    ):
        if user_id in self.users:
            self.users[user_id]["plan"] = plan
            self.users[user_id]["stripe_subscription_id"] = subscription_id
            self.users[user_id]["subscription_status"] = subscription_status
        return self.users.get(user_id)

    async def set_stripe_customer_id(self, user_id: str, customer_id: str):
        if user_id in self.users:
            self.users[user_id]["stripe_customer_id"] = customer_id
        return True

    async def delete_user(self, user_id: str):
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False


@pytest.fixture
def mock_db():
    """Create a fresh mock database for each test."""
    return MockDatabase()


@pytest.fixture
def saas_client(mock_db):
    """Create test client with mocked SaaS dependencies."""
    from app.main import app

    # Patch the database to use our mock
    with patch("app.webhooks.get_database", return_value=mock_db):
        client = TestClient(app)
        yield client, mock_db


class TestClerkWebhooks:
    """Tests for Clerk webhook handlers."""

    def test_user_created_sets_free_plan(self, saas_client):
        """New user from Clerk webhook should get free plan."""
        client, db = saas_client

        payload = load_fixture("recorded/clerk_user_created.json")

        response = client.post(
            "/webhooks/clerk",
            json=payload,
        )

        assert response.status_code == 200

        # Verify user was created with free plan
        user = db.users.get("user_2abc123def456")
        assert user is not None
        assert user["email"] == "newuser@example.com"
        assert user["plan"] == "free"

    def test_user_updated_preserves_paid_plan(self, saas_client):
        """CRITICAL: user.updated webhook must NOT overwrite paid plan.

        This test catches the bug where logging in would reset plan to free.
        """
        client, db = saas_client

        # Setup: Create user with starter plan (simulating existing subscriber)
        db.users["user_existing123"] = {
            "id": "user_existing123",
            "email": "existing@example.com",
            "name": "Existing User",
            "plan": "starter",  # Paid plan!
            "stripe_customer_id": "cus_test123",
            "stripe_subscription_id": "sub_test123",
            "subscription_status": "active",
        }

        # Verify setup
        assert db.users["user_existing123"]["plan"] == "starter"

        # Simulate Clerk user.updated webhook (happens on login)
        payload = load_fixture("recorded/clerk_user_updated.json")

        response = client.post(
            "/webhooks/clerk",
            json=payload,
        )

        assert response.status_code == 200

        # CRITICAL ASSERTION: Plan must still be starter!
        user = db.users.get("user_existing123")
        assert (
            user["plan"] == "starter"
        ), f"user.updated webhook overwrote paid plan! Expected 'starter', got '{user['plan']}'"
        assert user["stripe_subscription_id"] == "sub_test123"

    def test_user_updated_preserves_premium_plan(self, saas_client):
        """Premium plan should also be preserved on user.updated."""
        client, db = saas_client

        # Setup: Create user with premium plan
        db.users["user_existing123"] = {
            "id": "user_existing123",
            "email": "existing@example.com",
            "name": "Existing User",
            "plan": "premium",
            "stripe_customer_id": "cus_test123",
            "stripe_subscription_id": "sub_team123",
            "subscription_status": "active",
        }

        # Simulate webhook
        payload = load_fixture("recorded/clerk_user_updated.json")

        response = client.post(
            "/webhooks/clerk",
            json=payload,
        )

        assert response.status_code == 200

        # Verify plan preserved
        user = db.users.get("user_existing123")
        assert user["plan"] == "premium"

    def test_user_no_email_skips_creation(self, saas_client):
        """User without email should not be created (edge case)."""
        client, db = saas_client

        payload = load_fixture("synthetic/clerk_user_no_email.json")

        response = client.post(
            "/webhooks/clerk",
            json=payload,
        )

        assert response.status_code == 200

        # User should NOT be created without email
        user = db.users.get("user_noemail123")
        assert user is None


class TestStripeWebhooks:
    """Tests for Stripe webhook handlers."""

    def test_subscription_deleted_downgrades_to_free(self, mock_db):
        """Canceled subscription should downgrade user to free plan."""
        from app.main import app

        # Setup: Create user with starter plan
        mock_db.users["user_existing123"] = {
            "id": "user_existing123",
            "email": "existing@example.com",
            "name": "Existing User",
            "plan": "starter",
            "stripe_customer_id": "cus_test123",
            "stripe_subscription_id": "sub_canceled123",
            "subscription_status": "active",
        }

        # Simulate Stripe subscription.deleted webhook
        payload = load_fixture("recorded/stripe_subscription_deleted.json")

        # Mock both Stripe signature verification and database
        with (
            patch("stripe.Webhook.construct_event", return_value=payload),
            patch("app.webhooks.get_database", return_value=mock_db),
        ):
            client = TestClient(app)
            response = client.post(
                "/webhooks/stripe",
                json=payload,
                headers={"stripe-signature": "fake_sig"},
            )

        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"

        # Verify downgraded to free
        user = mock_db.users.get("user_existing123")
        assert user["plan"] == "free"
        assert user["subscription_status"] == "canceled"


class TestWebhookIdempotency:
    """Tests for webhook idempotency (same event twice shouldn't break things)."""

    def test_duplicate_user_created_is_idempotent(self, saas_client):
        """Receiving user.created twice should not cause errors."""
        client, db = saas_client

        payload = load_fixture("recorded/clerk_user_created.json")

        # First webhook
        response1 = client.post("/webhooks/clerk", json=payload)
        assert response1.status_code == 200

        # Duplicate webhook (should not error)
        response2 = client.post("/webhooks/clerk", json=payload)
        assert response2.status_code == 200

        # User should still exist with correct data
        user = db.users.get("user_2abc123def456")
        assert user is not None
        assert user["email"] == "newuser@example.com"

    def test_user_updated_multiple_times_preserves_plan(self, saas_client):
        """Multiple user.updated webhooks should preserve plan each time."""
        client, db = saas_client

        # Setup: Create paid user
        db.users["user_existing123"] = {
            "id": "user_existing123",
            "email": "existing@example.com",
            "name": "Existing User",
            "plan": "starter",
            "stripe_customer_id": "cus_test123",
            "stripe_subscription_id": "sub_test123",
            "subscription_status": "active",
        }

        payload = load_fixture("recorded/clerk_user_updated.json")

        # Simulate multiple logins
        for _ in range(5):
            response = client.post("/webhooks/clerk", json=payload)
            assert response.status_code == 200

        # Plan should STILL be starter after all those webhooks
        user = db.users.get("user_existing123")
        assert user["plan"] == "starter"
