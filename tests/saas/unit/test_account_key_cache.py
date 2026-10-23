"""Tests for the in-memory cache in validate_account_key.

MCP clients reconnect frequently, and each connect validates the account key.
Without a cache every reconnect hits the database, which keeps serverless
Postgres computes from ever suspending.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app import auth
from app.auth import invalidate_account_key_cache, validate_account_key


class CountingKeyDatabase:
    """Minimal fake DB that counts the queries validate_account_key makes."""

    def __init__(self):
        self.keys = {}
        self.users = {"user_alice": {"id": "user_alice", "email": "alice@example.com"}}
        self.key_lookups = 0
        self.last_used_updates = 0

    def add_key(self, key_id: str, key: str, expires_at: datetime | None = None):
        self.keys[key] = {
            "id": key_id,
            "key": key,
            "user_id": "user_alice",
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

    async def get_account_api_key_by_key(self, key: str):
        self.key_lookups += 1
        return self.keys.get(key)

    async def update_account_api_key_last_used(self, key_id: str) -> bool:
        self.last_used_updates += 1
        return True

    async def get_user(self, user_id: str):
        return self.users.get(user_id)


@pytest.fixture
def db():
    fake = CountingKeyDatabase()
    auth._account_key_cache.clear()
    with patch("app.auth.get_database", return_value=fake):
        yield fake
    auth._account_key_cache.clear()


@pytest.fixture
def clock():
    """Controllable replacement for time.monotonic used by the cache."""
    now = [1000.0]
    with patch("app.auth.time.monotonic", side_effect=lambda: now[0]):
        yield now


async def test_repeat_validation_within_ttl_skips_database(db, clock):
    db.add_key("key_1", "ak_alice")

    first = await validate_account_key("ak_alice")
    second = await validate_account_key("ak_alice")

    assert first.user_id == second.user_id == "user_alice"
    assert db.key_lookups == 1
    assert db.last_used_updates == 1


async def test_validation_after_ttl_hits_database_again(db, clock):
    db.add_key("key_1", "ak_alice")

    await validate_account_key("ak_alice")
    clock[0] += auth.ACCOUNT_KEY_CACHE_TTL_SECONDS + 1
    await validate_account_key("ak_alice")

    assert db.key_lookups == 2
    assert db.last_used_updates == 2


async def test_invalid_keys_are_not_cached(db, clock):
    assert await validate_account_key("ak_unknown") is None

    db.add_key("key_1", "ak_unknown")

    assert await validate_account_key("ak_unknown") is not None


async def test_cached_key_stops_working_once_expired(db, clock):
    db.add_key("key_1", "ak_alice", expires_at=datetime.now(UTC) + timedelta(seconds=2))

    assert await validate_account_key("ak_alice") is not None

    with patch("app.auth.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime.now(UTC) + timedelta(seconds=5)
        mock_datetime.fromisoformat = datetime.fromisoformat
        assert await validate_account_key("ak_alice") is None


async def test_invalidate_removes_cached_key(db, clock):
    db.add_key("key_1", "ak_alice")
    await validate_account_key("ak_alice")

    del db.keys["ak_alice"]
    invalidate_account_key_cache("key_1")

    assert await validate_account_key("ak_alice") is None
