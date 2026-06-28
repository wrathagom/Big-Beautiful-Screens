"""Tests for iframe-embedding security headers on the screen viewer.

Covers the config-driven embeddable-demo-screen feature: a screen whose ID is
listed in EMBED_SCREEN_IDS (with a non-empty EMBED_ALLOWED_ORIGINS) is served
with a relaxed CSP frame-ancestors allowlist and no X-Frame-Options header.
Every other screen stays locked to frame-ancestors 'none' + X-Frame-Options.
"""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module", autouse=True)
def setup_test_db() -> Iterator:
    """Set up a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["SQLITE_PATH"] = str(Path(tmpdir) / "test_embed.db")

        from app.config import get_settings

        get_settings.cache_clear()

        from app.db.factory import reset_database

        reset_database()

        import asyncio
        import concurrent.futures

        import app.database as db_module
        from app.main import app

        try:
            asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(asyncio.run, db_module.init_db()).result()
        except RuntimeError:
            asyncio.run(db_module.init_db())

        yield app

        reset_database()
        get_settings.cache_clear()


@pytest.fixture
def client(setup_test_db) -> TestClient:
    return TestClient(setup_test_db)


@pytest.fixture
def screen_id(client) -> str:
    """Create a screen and return its id."""
    response = client.post("/api/v1/screens")
    assert response.status_code == 200
    return response.json()["screen_id"]


ORIGINS = "https://bigbeautifulscreens.com https://www.bigbeautifulscreens.com"


@pytest.fixture
def embed_env() -> Iterator[None]:
    """Context where EMBED_* env vars are set; cleaned up + cache cleared after."""
    from app.config import get_settings

    def _apply(screen_ids: str, origins: str) -> None:
        os.environ["EMBED_SCREEN_IDS"] = screen_ids
        os.environ["EMBED_ALLOWED_ORIGINS"] = origins
        get_settings.cache_clear()

    yield _apply

    os.environ.pop("EMBED_SCREEN_IDS", None)
    os.environ.pop("EMBED_ALLOWED_ORIGINS", None)
    get_settings.cache_clear()


class TestDefaultLockedDown:
    """With no embed config, all screens stay unframeable (current behavior)."""

    def test_default_screen_blocks_framing(self, client, screen_id):
        resp = client.get(f"/screen/{screen_id}")
        assert resp.status_code == 200
        assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
        assert resp.headers.get("x-frame-options") == "SAMEORIGIN"


class TestEmbeddableScreen:
    """A configured demo screen is framable from the allowlist; no XFO."""

    def test_configured_screen_allows_allowlisted_origins(self, client, screen_id, embed_env):
        embed_env(screen_ids=screen_id, origins=ORIGINS)
        resp = client.get(f"/screen/{screen_id}")
        assert resp.status_code == 200
        csp = resp.headers["content-security-policy"]
        assert (
            "frame-ancestors https://bigbeautifulscreens.com https://www.bigbeautifulscreens.com"
            in csp
        )
        assert "frame-ancestors 'none'" not in csp
        # XFO must be absent so it doesn't conflict with the frame-ancestors allowlist.
        assert "x-frame-options" not in {k.lower() for k in resp.headers}

    def test_other_screen_stays_locked_while_allowlist_set(self, client, embed_env):
        """Only screens in EMBED_SCREEN_IDS are embeddable; others stay 'none'."""
        embeddable = client.post("/api/v1/screens").json()["screen_id"]
        other = client.post("/api/v1/screens").json()["screen_id"]
        embed_env(screen_ids=embeddable, origins=ORIGINS)

        resp = client.get(f"/screen/{other}")
        assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
        assert resp.headers.get("x-frame-options") == "SAMEORIGIN"

    def test_screen_id_listed_but_no_origins_stays_locked(self, client, screen_id, embed_env):
        """An allowlisted screen ID with empty origins is still locked (feature off)."""
        embed_env(screen_ids=screen_id, origins="")
        resp = client.get(f"/screen/{screen_id}")
        assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
        assert resp.headers.get("x-frame-options") == "SAMEORIGIN"
