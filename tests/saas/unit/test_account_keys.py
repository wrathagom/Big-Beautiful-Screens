"""Tests for account-level API keys.

These tests verify:
- Account key generation and validation
- Account key CRUD operations (create, list, delete)
- Account key authentication for account-level operations
- Multi-user isolation with account keys
- Key expiration handling
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.saas.saas_utils import MockClerkUser


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


class MockAccountKeyDatabase:
    """Mock database with account key support for testing."""

    def __init__(self):
        self.screens = {}
        self.users = {}
        self.account_api_keys = {}
        self.pages = {}
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
        if screen_id in self.rotation_settings:
            return self.rotation_settings[screen_id]
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

    async def create_account_api_key(
        self,
        key_id: str,
        key: str,
        user_id: str,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> dict:
        now = datetime.now(UTC).isoformat()
        self.account_api_keys[key_id] = {
            "id": key_id,
            "key": key,
            "user_id": user_id,
            "name": name,
            "scopes": scopes or ["*"],
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": now,
            "last_used_at": None,
        }
        return self.account_api_keys[key_id]

    async def get_account_api_key_by_key(self, key: str) -> dict | None:
        for key_data in self.account_api_keys.values():
            if key_data.get("key") == key:
                return key_data
        return None

    async def get_account_api_keys_by_user(
        self, user_id: str, limit: int | None = None, offset: int = 0
    ) -> list[dict]:
        keys = [k for k in self.account_api_keys.values() if k.get("user_id") == user_id]
        if limit:
            return keys[offset : offset + limit]
        return keys[offset:]

    async def get_account_api_keys_count(self, user_id: str) -> int:
        return len([k for k in self.account_api_keys.values() if k.get("user_id") == user_id])

    async def update_account_api_key_last_used(self, key_id: str) -> bool:
        if key_id in self.account_api_keys:
            self.account_api_keys[key_id]["last_used_at"] = datetime.now(UTC).isoformat()
            return True
        return False

    async def delete_account_api_key(self, key_id: str) -> bool:
        if key_id in self.account_api_keys:
            del self.account_api_keys[key_id]
            return True
        return False

    async def init(self):
        pass


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


@pytest.fixture
def mock_db():
    """Create a fresh mock database for each test."""
    db = MockAccountKeyDatabase()

    db.users["user_alice"] = {
        "id": "user_alice",
        "email": "alice@example.com",
        "name": "Alice",
        "plan": "starter",
    }
    db.users["user_bob"] = {
        "id": "user_bob",
        "email": "bob@example.com",
        "name": "Bob",
        "plan": "starter",
    }

    return db


@pytest.fixture
def patched_app(mock_db):
    """Create app with mocked database."""
    import app.db.factory as factory

    original_db = factory._db_instance
    factory._db_instance = mock_db

    from app.config import get_settings

    get_settings.cache_clear()

    with patch("app.database.init_db", new_callable=AsyncMock):
        from app.main import app

        yield app, mock_db

    factory._db_instance = original_db
    get_settings.cache_clear()


class TestAccountKeyGeneration:
    """Tests for account key generation and format."""

    def test_account_key_has_correct_prefix(self, patched_app):
        """Account keys should have ak_ prefix."""
        from app.auth import AuthUser, get_current_user, require_auth

        app, mock_db = patched_app

        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        async def mock_require_auth():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[require_auth] = mock_require_auth
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/account/keys",
                json={"name": "Test Key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["key"].startswith("ak_")
        finally:
            app.dependency_overrides.clear()

    def test_account_key_is_unique(self, patched_app):
        """Each account key should be unique."""
        from app.auth import AuthUser, get_current_user, require_auth

        app, mock_db = patched_app

        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        async def mock_require_auth():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[require_auth] = mock_require_auth
        try:
            client = TestClient(app)

            response1 = client.post(
                "/api/v1/account/keys",
                json={"name": "Key 1"},
            )
            response2 = client.post(
                "/api/v1/account/keys",
                json={"name": "Key 2"},
            )

            assert response1.status_code == 200
            assert response2.status_code == 200

            key1 = response1.json()["key"]
            key2 = response2.json()["key"]
            assert key1 != key2
        finally:
            app.dependency_overrides.clear()


class TestAccountKeyManagement:
    """Tests for account key CRUD operations."""

    def test_create_account_key(self, patched_app):
        """Users can create account keys."""
        from app.auth import AuthUser, get_current_user, require_auth

        app, mock_db = patched_app

        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        async def mock_require_auth():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[require_auth] = mock_require_auth
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/account/keys",
                json={"name": "My API Key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "My API Key"
            assert "key" in data
            assert "id" in data
            assert data["key"].startswith("ak_")
        finally:
            app.dependency_overrides.clear()

    def test_create_account_key_with_expiration(self, patched_app):
        """Users can create account keys with expiration."""
        from app.auth import AuthUser, get_current_user, require_auth

        app, mock_db = patched_app

        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        async def mock_require_auth():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[require_auth] = mock_require_auth
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/account/keys",
                json={"name": "Expiring Key", "expires_in_days": 30},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["expires_at"] is not None
        finally:
            app.dependency_overrides.clear()

    def test_list_account_keys(self, patched_app):
        """Users can list their account keys."""
        from app.auth import AuthUser, get_current_user, require_auth

        app, mock_db = patched_app

        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        async def mock_require_auth():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[require_auth] = mock_require_auth
        try:
            client = TestClient(app)

            client.post("/api/v1/account/keys", json={"name": "Key 1"})
            client.post("/api/v1/account/keys", json={"name": "Key 2"})

            response = client.get("/api/v1/account/keys")

            assert response.status_code == 200
            data = response.json()
            assert len(data["keys"]) == 2
            assert data["total_count"] == 2
            for key in data["keys"]:
                assert "key" not in key
                assert "key_preview" in key
        finally:
            app.dependency_overrides.clear()

    def test_delete_account_key(self, patched_app):
        """Users can delete their account keys."""
        from app.auth import AuthUser, get_current_user, require_auth

        app, mock_db = patched_app

        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        async def mock_require_auth():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[require_auth] = mock_require_auth
        try:
            client = TestClient(app)

            create_response = client.post(
                "/api/v1/account/keys",
                json={"name": "To Delete"},
            )
            key_id = create_response.json()["id"]

            delete_response = client.delete(f"/api/v1/account/keys/{key_id}")
            assert delete_response.status_code == 200

            list_response = client.get("/api/v1/account/keys")
            assert list_response.json()["total_count"] == 0
        finally:
            app.dependency_overrides.clear()


class TestAccountKeyAuthentication:
    """Tests for account key authentication flow."""

    def test_account_key_authenticates_list_screens(self, patched_app):
        """Account keys can authenticate list screens endpoint."""
        app, mock_db = patched_app

        mock_db.screens["screen_alice"] = {
            "id": "screen_alice",
            "api_key": "sk_alice",
            "owner_id": "user_alice",
            "org_id": None,
            "name": "Alice's Screen",
        }

        mock_db.account_api_keys["key_alice"] = {
            "id": "key_alice",
            "key": "ak_test_alice_key",
            "user_id": "user_alice",
            "name": "Alice's Key",
            "scopes": ["*"],
            "expires_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
        }

        client = TestClient(app)
        response = client.get(
            "/api/v1/screens",
            headers={"X-API-Key": "ak_test_alice_key"},
        )

        assert response.status_code == 200
        data = response.json()
        screen_ids = [s["screen_id"] for s in data["screens"]]
        assert "screen_alice" in screen_ids

    def test_account_key_authenticates_create_screen(self, patched_app):
        """Account keys can authenticate screen creation."""
        app, mock_db = patched_app

        mock_db.account_api_keys["key_alice"] = {
            "id": "key_alice",
            "key": "ak_test_alice_key",
            "user_id": "user_alice",
            "name": "Alice's Key",
            "scopes": ["*"],
            "expires_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
        }

        client = TestClient(app)
        response = client.post(
            "/api/v1/screens",
            headers={"X-API-Key": "ak_test_alice_key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "screen_id" in data
        assert "api_key" in data

    def test_invalid_account_key_rejected(self, patched_app):
        """Invalid account keys should be rejected."""
        app, mock_db = patched_app

        client = TestClient(app)
        response = client.get(
            "/api/v1/screens",
            headers={"X-API-Key": "ak_invalid_key"},
        )

        assert response.status_code == 401

    def test_expired_account_key_rejected(self, patched_app):
        """Expired account keys should be rejected."""
        app, mock_db = patched_app

        expired_time = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        mock_db.account_api_keys["key_expired"] = {
            "id": "key_expired",
            "key": "ak_expired_key",
            "user_id": "user_alice",
            "name": "Expired Key",
            "scopes": ["*"],
            "expires_at": expired_time,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
        }

        client = TestClient(app)
        response = client.get(
            "/api/v1/screens",
            headers={"X-API-Key": "ak_expired_key"},
        )

        assert response.status_code == 401

    def test_screen_key_not_accepted_for_account_operations(self, patched_app):
        """Screen keys (sk_) should not work for account-level operations."""
        app, mock_db = patched_app

        mock_db.screens["screen_alice"] = {
            "id": "screen_alice",
            "api_key": "sk_alice_screen_key",
            "owner_id": "user_alice",
            "org_id": None,
            "name": "Alice's Screen",
        }

        client = TestClient(app)
        response = client.get(
            "/api/v1/screens",
            headers={"X-API-Key": "sk_alice_screen_key"},
        )

        assert response.status_code == 401


class TestAccountKeyIsolation:
    """Tests for multi-user isolation with account keys."""

    def test_user_cannot_see_other_users_keys(self, patched_app):
        """Users should only see their own account keys."""
        from app.auth import AuthUser, get_current_user, require_auth

        app, mock_db = patched_app

        mock_db.account_api_keys["key_alice"] = {
            "id": "key_alice",
            "key": "ak_alice_key",
            "user_id": "user_alice",
            "name": "Alice's Key",
            "scopes": ["*"],
            "expires_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
        }
        mock_db.account_api_keys["key_bob"] = {
            "id": "key_bob",
            "key": "ak_bob_key",
            "user_id": "user_bob",
            "name": "Bob's Key",
            "scopes": ["*"],
            "expires_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
        }

        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        async def mock_require_auth():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[require_auth] = mock_require_auth
        try:
            client = TestClient(app)
            response = client.get("/api/v1/account/keys")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1
            assert data["keys"][0]["id"] == "key_alice"
        finally:
            app.dependency_overrides.clear()

    def test_user_cannot_delete_other_users_keys(self, patched_app):
        """Users should not be able to delete other users' keys."""
        from app.auth import AuthUser, get_current_user, require_auth

        app, mock_db = patched_app

        mock_db.account_api_keys["key_bob"] = {
            "id": "key_bob",
            "key": "ak_bob_key",
            "user_id": "user_bob",
            "name": "Bob's Key",
            "scopes": ["*"],
            "expires_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
        }

        alice_auth = AuthUser(
            user_id="user_alice",
            email="alice@example.com",
            name="Alice",
        )

        async def mock_get_current_user():
            return alice_auth

        async def mock_require_auth():
            return alice_auth

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[require_auth] = mock_require_auth
        try:
            client = TestClient(app)
            response = client.delete("/api/v1/account/keys/key_bob")

            assert response.status_code == 404
            assert "key_bob" in mock_db.account_api_keys
        finally:
            app.dependency_overrides.clear()

    def test_account_key_only_accesses_owners_screens(self, patched_app):
        """Account keys should only access the owner's screens."""
        app, mock_db = patched_app

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

        mock_db.account_api_keys["key_alice"] = {
            "id": "key_alice",
            "key": "ak_alice_key",
            "user_id": "user_alice",
            "name": "Alice's Key",
            "scopes": ["*"],
            "expires_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
        }

        client = TestClient(app)
        response = client.get(
            "/api/v1/screens",
            headers={"X-API-Key": "ak_alice_key"},
        )

        assert response.status_code == 200
        data = response.json()
        screen_ids = [s["screen_id"] for s in data["screens"]]
        assert "screen_alice" in screen_ids
        assert "screen_bob" not in screen_ids


class TestAccountKeyLastUsed:
    """Tests for last_used_at tracking."""

    def test_last_used_updated_on_use(self, patched_app):
        """last_used_at should be updated when key is used."""
        app, mock_db = patched_app

        mock_db.account_api_keys["key_alice"] = {
            "id": "key_alice",
            "key": "ak_alice_key",
            "user_id": "user_alice",
            "name": "Alice's Key",
            "scopes": ["*"],
            "expires_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
        }

        assert mock_db.account_api_keys["key_alice"]["last_used_at"] is None

        client = TestClient(app)
        response = client.get(
            "/api/v1/screens",
            headers={"X-API-Key": "ak_alice_key"},
        )

        assert response.status_code == 200
        assert mock_db.account_api_keys["key_alice"]["last_used_at"] is not None


class TestAccountKeySaaSOnly:
    """Tests verifying account keys are SaaS-only."""

    def test_account_key_endpoints_require_saas_mode(self):
        """Account key endpoints should require SaaS mode."""
        original_env = os.environ.get("APP_MODE")
        os.environ["APP_MODE"] = "self-hosted"

        from app.config import get_settings

        get_settings.cache_clear()

        try:
            from app.main import app

            client = TestClient(app)
            response = client.post(
                "/api/v1/account/keys",
                json={"name": "Test Key"},
            )

            assert response.status_code == 404 or response.status_code == 403
        finally:
            if original_env:
                os.environ["APP_MODE"] = original_env
            else:
                os.environ.pop("APP_MODE", None)
            get_settings.cache_clear()
