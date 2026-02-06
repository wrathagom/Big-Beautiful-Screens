"""Tests for onboarding functionality."""

import asyncio
import concurrent.futures
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def run_async(coro):
    """Run an async coroutine, handling the case where an event loop is already running."""
    try:
        asyncio.get_running_loop()
        # If we're in a running loop, run in a separate thread
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return executor.submit(asyncio.run, coro).result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run()
        return asyncio.run(coro)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Set up a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = str(Path(tmpdir) / "test_onboarding.db")
        os.environ["SQLITE_PATH"] = test_db_path

        from app.config import get_settings

        get_settings.cache_clear()

        from app.db.factory import reset_database

        reset_database()

        import app.database as db_module
        from app.main import app

        run_async(db_module.init_db())

        yield app

        reset_database()
        get_settings.cache_clear()


@pytest.fixture
def client(setup_test_db):
    """Create a test client."""
    return TestClient(setup_test_db)


class TestOnboardingModule:
    """Tests for the onboarding module."""

    def test_demo_content_structure(self):
        """Test that demo content has valid structure."""
        from app.onboarding import _load_demo_config

        config = _load_demo_config()
        pages = config.get("pages", [])

        assert len(pages) >= 2  # At least 2 pages to demo rotation
        for page in pages:
            assert "name" in page
            assert "content" in page
            for item in page["content"]:
                assert "type" in item
                assert item["type"] in ["text", "markdown", "image", "video", "widget"]

    def test_demo_screen_config(self):
        """Test that demo screen config has required fields."""
        from app.onboarding import _load_demo_config

        config = _load_demo_config()

        assert "name" in config
        assert "background_color" in config
        assert "panel_color" in config
        assert "font_color" in config

    def test_demo_rotation_enabled(self):
        """Test that demo has rotation enabled to showcase multi-page."""
        from app.onboarding import _load_demo_config

        config = _load_demo_config()
        rotation = config.get("rotation", {})

        assert rotation.get("enabled") is True
        assert rotation.get("interval", 0) > 0

    def test_create_demo_screen(self, setup_test_db):
        """Test creating a demo screen."""
        from app.onboarding import create_demo_screen

        result = run_async(create_demo_screen())

        assert "screen_id" in result
        assert "api_key" in result
        assert "screen_url" in result
        assert result["api_key"].startswith("sk_")
        assert len(result["screen_id"]) == 12

    def test_demo_screen_has_content(self, client, setup_test_db):
        """Test that created demo screen has proper content."""
        from app.onboarding import create_demo_screen

        result = run_async(create_demo_screen())

        # Verify screen exists and is viewable
        response = client.get(f"/screen/{result['screen_id']}")
        assert response.status_code == 200

    def test_demo_screen_with_owner(self, setup_test_db):
        """Test creating a demo screen with an owner ID."""
        from app.onboarding import create_demo_screen

        result = run_async(create_demo_screen(owner_id="test_user_123"))

        assert "screen_id" in result
        assert "api_key" in result

    def test_demo_screen_appears_in_admin(self, client, setup_test_db):
        """Test that demo screen appears in admin page."""
        from app.onboarding import _load_demo_config, create_demo_screen

        config = _load_demo_config()
        result = run_async(create_demo_screen())

        response = client.get("/admin/screens")
        assert response.status_code == 200
        assert result["screen_id"] in response.text
        assert config["name"] in response.text


class TestHelpButton:
    """Tests for the help button functionality."""

    def test_help_url_config(self):
        """Test that HELP_URL config exists and has default."""
        from app.config import get_settings

        settings = get_settings()
        assert hasattr(settings, "HELP_URL")
        assert "github.com" in settings.HELP_URL

    def test_admin_screens_has_help_button(self, client):
        """Test that admin screens page has help button."""
        response = client.get("/admin/screens")
        assert response.status_code == 200
        assert 'class="help-button"' in response.text

    def test_admin_themes_has_help_button(self, client):
        """Test that admin themes page has help button."""
        response = client.get("/admin/themes")
        assert response.status_code == 200
        assert 'class="help-button"' in response.text
