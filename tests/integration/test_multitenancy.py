"""Multi-tenancy isolation tests for SaaS mode.

These tests verify that users can only access their own resources
and cannot see or modify other users' data.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# MockClerkUser imported for type reference only (used in module-level user definitions)
from tests.saas_utils import MockClerkUser  # noqa: F401


@pytest.fixture(scope="module", autouse=True)
def saas_environment():
    """Set up SaaS environment for all tests in this module."""
    original_env = {
        "TESTING": os.environ.get("TESTING"),
        "APP_MODE": os.environ.get("APP_MODE"),
        "CLERK_SECRET_KEY": os.environ.get("CLERK_SECRET_KEY"),
        "CLERK_PUBLISHABLE_KEY": os.environ.get("CLERK_PUBLISHABLE_KEY"),
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "STRIPE_SECRET_KEY": os.environ.get("STRIPE_SECRET_KEY"),
        "STRIPE_WEBHOOK_SECRET": os.environ.get("STRIPE_WEBHOOK_SECRET"),
    }

    os.environ["TESTING"] = "1"
    os.environ["APP_MODE"] = "saas"
    os.environ["CLERK_SECRET_KEY"] = "sk_test_fake"
    os.environ["CLERK_PUBLISHABLE_KEY"] = "pk_test_fake"
    os.environ["DATABASE_URL"] = "postgresql://fake:fake@localhost/fake"
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
    os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_fake"

    from app.config import get_settings

    get_settings.cache_clear()

    yield

    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    get_settings.cache_clear()


class MockScreenDatabase:
    """Mock database with screen support for multi-tenancy testing."""

    def __init__(self):
        self.screens = {}
        self.pages = {}
        self.users = {}
        self.rotation_settings = {}

    async def get_screen_by_id(self, screen_id: str):
        return self.screens.get(screen_id)

    async def get_screen_by_api_key(self, api_key: str):
        for screen in self.screens.values():
            if screen.get("api_key") == api_key:
                return screen
        return None

    async def get_all_screens(
        self,
        limit: int = 100,
        offset: int = 0,
        owner_id: str | None = None,
        org_id: str | None = None,
    ):
        screens = []
        for screen in self.screens.values():
            # Filter by owner/org if specified
            if (
                owner_id
                and screen.get("owner_id") != owner_id
                and not (org_id and screen.get("org_id") == org_id)
            ):
                continue
            screens.append(screen)
        return screens[offset : offset + limit]

    async def get_screens_count(self, owner_id: str | None = None, org_id: str | None = None):
        count = 0
        for screen in self.screens.values():
            if (
                owner_id
                and screen.get("owner_id") != owner_id
                and not (org_id and screen.get("org_id") == org_id)
            ):
                continue
            count += 1
        return count

    async def create_screen(
        self,
        screen_id: str,
        api_key: str,
        created_at: str,
        owner_id: str | None = None,
        org_id: str | None = None,
        name: str | None = None,
    ):
        self.screens[screen_id] = {
            "id": screen_id,
            "api_key": api_key,
            "created_at": created_at,
            "owner_id": owner_id,
            "org_id": org_id,
            "name": name,
            "rotation_enabled": False,
            "rotation_interval": 30,
        }
        return self.screens[screen_id]

    async def update_screen(self, screen_id: str, **kwargs):
        if screen_id in self.screens:
            self.screens[screen_id].update(kwargs)
            return True
        return False

    async def update_screen_name(self, screen_id: str, name: str):
        if screen_id in self.screens:
            self.screens[screen_id]["name"] = name
            return True
        return False

    async def delete_screen(self, screen_id: str):
        if screen_id in self.screens:
            del self.screens[screen_id]
            return True
        return False

    async def get_rotation_settings(self, screen_id: str):
        """Get rotation settings for a screen."""
        if screen_id in self.rotation_settings:
            return self.rotation_settings[screen_id]
        # Return default settings
        screen = self.screens.get(screen_id)
        if screen:
            return {
                "enabled": screen.get("rotation_enabled", False),
                "interval": screen.get("rotation_interval", 30),
            }
        return {"enabled": False, "interval": 30}

    async def update_rotation_settings(
        self,
        screen_id: str,
        enabled: bool | None = None,
        interval: int | None = None,
        **kwargs,
    ):
        """Update rotation settings for a screen."""
        if screen_id not in self.rotation_settings:
            self.rotation_settings[screen_id] = {"enabled": False, "interval": 30}
        if enabled is not None:
            self.rotation_settings[screen_id]["enabled"] = enabled
        if interval is not None:
            self.rotation_settings[screen_id]["interval"] = interval
        self.rotation_settings[screen_id].update(kwargs)
        return self.rotation_settings[screen_id]

    async def get_user(self, user_id: str):
        return self.users.get(user_id)

    async def create_or_update_user(
        self, user_id: str, email: str, name: str | None = None, plan: str = "free"
    ):
        if user_id not in self.users:
            self.users[user_id] = {
                "id": user_id,
                "email": email,
                "name": name,
                "plan": plan,
            }
        return self.users[user_id]

    # Stub methods for any other database calls
    async def init(self):
        """Initialize database - no-op for mock."""
        pass


# Test users
USER_ALICE = MockClerkUser(
    user_id="user_alice",
    email="alice@example.com",
    name="Alice",
)

USER_BOB = MockClerkUser(
    user_id="user_bob",
    email="bob@example.com",
    name="Bob",
)

USER_CHARLIE_ORG = MockClerkUser(
    user_id="user_charlie",
    email="charlie@example.com",
    name="Charlie",
    org_id="org_acme",
    org_role="member",
)

USER_DIANA_ORG = MockClerkUser(
    user_id="user_diana",
    email="diana@example.com",
    name="Diana",
    org_id="org_acme",
    org_role="admin",
)


@pytest.fixture
def mock_db():
    """Create a fresh mock database for each test with all necessary mocks."""
    db = MockScreenDatabase()

    # Pre-create users with pro plan (to bypass plan limits)
    db.users["user_alice"] = {
        "id": "user_alice",
        "email": "alice@example.com",
        "name": "Alice",
        "plan": "pro",
    }
    db.users["user_bob"] = {
        "id": "user_bob",
        "email": "bob@example.com",
        "name": "Bob",
        "plan": "pro",
    }
    db.users["user_charlie"] = {
        "id": "user_charlie",
        "email": "charlie@example.com",
        "name": "Charlie",
        "plan": "pro",
    }
    db.users["user_diana"] = {
        "id": "user_diana",
        "email": "diana@example.com",
        "name": "Diana",
        "plan": "pro",
    }

    return db


@pytest.fixture
def patched_app(mock_db):
    """Create app with mocked database - uses direct singleton injection."""
    import app.db.factory as factory

    # Save original singleton
    original_db = factory._db_instance

    # Inject mock database directly into the singleton
    factory._db_instance = mock_db

    # Also clear the settings cache to ensure fresh config
    from app.config import get_settings

    get_settings.cache_clear()

    # Patch init_db to be a no-op (prevents real DB connection on startup)
    with patch("app.database.init_db", new_callable=AsyncMock):
        from app.main import app

        yield app, mock_db

    # Restore original database singleton - critical for cleanup
    factory._db_instance = original_db

    # Clear settings cache again
    get_settings.cache_clear()


class TestScreenIsolation:
    """Tests for screen isolation between users."""

    def test_user_can_list_own_screens(self, patched_app):
        """Users should only see their own screens in the list."""
        from app.auth import AuthUser, get_current_user

        app, mock_db = patched_app

        # Create screens for both users
        mock_db.screens["screen_alice"] = {
            "id": "screen_alice",
            "api_key": "sk_alice",
            "owner_id": "user_alice",
            "org_id": None,
            "name": "Alice's Screen",
        }
        mock_db.screens["screen_bob"] = {
            "id": "screen_bob",
            "api_key": "sk_bob",
            "owner_id": "user_bob",
            "org_id": None,
            "name": "Bob's Screen",
        }

        # Mock auth as Alice
        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            client = TestClient(app)
            response = client.get("/api/v1/screens")

            assert response.status_code == 200
            data = response.json()

            # Alice should only see her screen
            screen_ids = [s["screen_id"] for s in data["screens"]]
            assert "screen_alice" in screen_ids
            assert "screen_bob" not in screen_ids
        finally:
            app.dependency_overrides.clear()

    def test_screen_view_is_public(self, patched_app):
        """Individual screen viewing is public (for display purposes).

        Security model: Screens are viewable by anyone with the URL.
        Modification requires API key authentication, not user ownership.
        """
        from app.auth import AuthUser, get_current_user

        app, mock_db = patched_app

        # Create Bob's screen
        mock_db.screens["screen_bob"] = {
            "id": "screen_bob",
            "api_key": "sk_bob",
            "owner_id": "user_bob",
            "org_id": None,
            "name": "Bob's Public Screen",
        }

        # Mock auth as Alice (viewing Bob's screen)
        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            client = TestClient(app)

            # Alice can view Bob's screen (by design - screens are for public display)
            response = client.get("/api/v1/screens/screen_bob")

            # Screen viewing is allowed (public for display purposes)
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_wrong_api_key_cannot_modify_screen(self, patched_app):
        """Modification requires correct API key, not just user ownership."""
        app, mock_db = patched_app

        # Create Bob's screen
        mock_db.screens["screen_bob"] = {
            "id": "screen_bob",
            "api_key": "sk_bob_secret",
            "owner_id": "user_bob",
            "org_id": None,
            "name": "Bob's Screen",
            "rotation_enabled": False,
            "rotation_interval": 30,
        }

        client = TestClient(app)

        # Try to modify with wrong API key
        response = client.patch(
            "/api/v1/screens/screen_bob",
            json={"name": "Hacked"},
            headers={"X-API-Key": "wrong_key"},
        )

        # Should be denied (401 Unauthorized)
        assert response.status_code == 401

        # Verify screen wasn't modified
        assert mock_db.screens["screen_bob"]["name"] == "Bob's Screen"

    def test_missing_api_key_cannot_delete_screen(self, patched_app):
        """Deletion requires API key authentication."""
        app, mock_db = patched_app

        # Create Bob's screen
        mock_db.screens["screen_bob"] = {
            "id": "screen_bob",
            "api_key": "sk_bob_secret",
            "owner_id": "user_bob",
            "org_id": None,
            "name": "Bob's Screen",
        }

        client = TestClient(app)

        # Try to delete without API key
        response = client.delete("/api/v1/screens/screen_bob")

        # Should require API key (422 Unprocessable Entity for missing header)
        assert response.status_code == 422

        # Verify screen still exists
        assert "screen_bob" in mock_db.screens

    def test_correct_api_key_can_modify_screen(self, patched_app):
        """Correct API key allows screen modification."""
        app, mock_db = patched_app

        # Create Alice's screen
        mock_db.screens["screen_alice"] = {
            "id": "screen_alice",
            "api_key": "sk_alice_secret",
            "owner_id": "user_alice",
            "org_id": None,
            "name": "Old Name",
            "rotation_enabled": False,
            "rotation_interval": 30,
        }

        client = TestClient(app)

        # Modify with correct API key
        response = client.patch(
            "/api/v1/screens/screen_alice",
            json={"name": "New Name"},
            headers={"X-API-Key": "sk_alice_secret"},
        )

        assert response.status_code == 200

        # Verify screen was modified
        assert mock_db.screens["screen_alice"]["name"] == "New Name"


class TestApiKeyAccess:
    """Tests for API key-based access (for external integrations)."""

    def test_api_key_allows_modification(self, patched_app):
        """X-API-Key header allows modification regardless of user session."""
        app, mock_db = patched_app

        # Create screen with API key
        mock_db.screens["screen_public"] = {
            "id": "screen_public",
            "api_key": "sk_test_key_123",
            "owner_id": "user_bob",
            "org_id": None,
            "name": "Public API Screen",
            "rotation_enabled": False,
            "rotation_interval": 30,
        }

        client = TestClient(app)

        # Use X-API-Key header to modify screen
        response = client.patch(
            "/api/v1/screens/screen_public",
            json={"name": "Modified via API"},
            headers={"X-API-Key": "sk_test_key_123"},
        )

        assert response.status_code == 200
        assert mock_db.screens["screen_public"]["name"] == "Modified via API"

    def test_wrong_api_key_denied(self, patched_app):
        """Wrong X-API-Key should be denied."""
        app, mock_db = patched_app

        # Create screen with API key
        mock_db.screens["screen_secure"] = {
            "id": "screen_secure",
            "api_key": "sk_correct_key",
            "owner_id": "user_bob",
            "org_id": None,
            "name": "Secure Screen",
            "rotation_enabled": False,
            "rotation_interval": 30,
        }

        client = TestClient(app)

        # Use wrong API key
        response = client.patch(
            "/api/v1/screens/screen_secure",
            json={"name": "Hacked"},
            headers={"X-API-Key": "sk_wrong_key"},
        )

        # Should be denied (401 Unauthorized)
        assert response.status_code == 401

        # Verify not modified
        assert mock_db.screens["screen_secure"]["name"] == "Secure Screen"


class TestOrganizationAccess:
    """Tests for organization-level access control."""

    def test_org_members_can_see_org_screens(self, patched_app):
        """Organization members should see org screens."""
        from app.auth import AuthUser, get_current_user

        app, mock_db = patched_app

        # Create org screen
        mock_db.screens["screen_org"] = {
            "id": "screen_org",
            "api_key": "sk_org",
            "owner_id": "user_charlie",
            "org_id": "org_acme",
            "name": "ACME Dashboard",
        }

        # Mock auth as Diana (same org as Charlie)
        diana_auth = AuthUser(
            user_id="user_diana",
            email="diana@example.com",
            name="Diana",
            org_id="org_acme",
            org_role="admin",
        )

        async def mock_get_current_user():
            return diana_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            client = TestClient(app)

            # Diana lists screens - should see org screen
            response = client.get("/api/v1/screens")

            assert response.status_code == 200
            data = response.json()
            screen_ids = [s["screen_id"] for s in data["screens"]]
            assert "screen_org" in screen_ids
        finally:
            app.dependency_overrides.clear()

    def test_non_org_member_cannot_see_org_screens(self, patched_app):
        """Users outside an org should not see that org's screens."""
        from app.auth import AuthUser, get_current_user

        app, mock_db = patched_app

        # Create org screen
        mock_db.screens["screen_org"] = {
            "id": "screen_org",
            "api_key": "sk_org",
            "owner_id": "user_charlie",
            "org_id": "org_acme",
            "name": "ACME Dashboard",
        }

        # Mock auth as Alice (not in org_acme)
        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
            org_id=None,
        )

        async def mock_get_current_user():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            client = TestClient(app)

            # Alice lists screens - should NOT see org screen
            response = client.get("/api/v1/screens")

            assert response.status_code == 200
            data = response.json()
            screen_ids = [s["screen_id"] for s in data["screens"]]
            assert "screen_org" not in screen_ids
        finally:
            app.dependency_overrides.clear()


class TestUnauthenticatedAccess:
    """Tests for unauthenticated access in SaaS mode."""

    def test_unauthenticated_cannot_create_screen(self, patched_app):
        """Unauthenticated users should not be able to create screens in SaaS mode."""
        from app.auth import get_current_user

        app, mock_db = patched_app

        async def mock_no_user():
            return None

        app.dependency_overrides[get_current_user] = mock_no_user
        try:
            client = TestClient(app)

            response = client.post("/api/v1/screens")

            # Should require auth
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_unauthenticated_cannot_list_screens(self, patched_app):
        """Unauthenticated users should not be able to list screens in SaaS mode."""
        from app.auth import get_current_user

        app, mock_db = patched_app

        # Create a screen
        mock_db.screens["screen_private"] = {
            "id": "screen_private",
            "api_key": "sk_private",
            "owner_id": "user_alice",
            "org_id": None,
            "name": "Private Screen",
        }

        async def mock_no_user():
            return None

        app.dependency_overrides[get_current_user] = mock_no_user
        try:
            client = TestClient(app)

            response = client.get("/api/v1/screens")

            # Should require auth or return empty
            assert response.status_code in (200, 401)
            if response.status_code == 200:
                # If 200, should be empty (no screens visible)
                data = response.json()
                assert len(data.get("screens", [])) == 0
        finally:
            app.dependency_overrides.clear()
