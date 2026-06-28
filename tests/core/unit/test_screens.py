"""Tests for Big Beautiful Screens API."""

import os
import tempfile
from datetime import UTC
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Use a temporary database for tests
@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Set up a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set the database path via environment variable before importing
        test_db_path = str(Path(tmpdir) / "test_screens.db")
        os.environ["SQLITE_PATH"] = test_db_path

        # Clear the cached settings so it picks up the new env var
        from app.config import get_settings

        get_settings.cache_clear()

        # Reset the database singleton
        from app.db.factory import reset_database

        reset_database()

        # Initialize the database
        import asyncio
        import concurrent.futures

        import app.database as db_module
        from app.main import app

        # Handle case where event loop may or may not be running
        try:
            asyncio.get_running_loop()
            # If we're in a running loop, run in a separate thread
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(asyncio.run, db_module.init_db()).result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            asyncio.run(db_module.init_db())

        yield app

        # Clean up
        reset_database()
        get_settings.cache_clear()


@pytest.fixture
def client(setup_test_db):
    """Create a test client."""
    return TestClient(setup_test_db)


@pytest.fixture
def screen(client):
    """Create a test screen and return its data."""
    response = client.post("/api/v1/screens")
    assert response.status_code == 200
    return response.json()


class TestScreenCreation:
    """Tests for screen creation."""

    def test_create_screen(self, client):
        """Test creating a new screen."""
        response = client.post("/api/v1/screens")
        assert response.status_code == 200

        data = response.json()
        assert "screen_id" in data
        assert "api_key" in data
        assert "screen_url" in data
        assert "api_url" in data
        assert data["api_key"].startswith("sk_")
        assert len(data["screen_id"]) == 12

    def test_create_multiple_screens(self, client):
        """Test that each screen gets a unique ID and API key."""
        response1 = client.post("/api/v1/screens")
        response2 = client.post("/api/v1/screens")

        screen1 = response1.json()
        screen2 = response2.json()

        assert screen1["screen_id"] != screen2["screen_id"]
        assert screen1["api_key"] != screen2["api_key"]


class TestMessages:
    """Tests for sending messages to screens."""

    def test_send_simple_message(self, client, screen):
        """Test sending a simple text message."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Hello, World!"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "viewers" in data

    def test_send_multiple_panels(self, client, screen):
        """Test sending multiple content panels."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Panel 1", "Panel 2", "Panel 3"]},
        )
        assert response.status_code == 200

    def test_send_with_colors(self, client, screen):
        """Test sending a message with custom colors."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["Colored panel"],
                "background_color": "#1a1a2e",
                "panel_color": "#16213e",
            },
        )
        assert response.status_code == 200

    def test_send_with_fonts(self, client, screen):
        """Test sending a message with custom fonts."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["Custom font"],
                "font_family": "Georgia, serif",
                "font_color": "#f1c40f",
            },
        )
        assert response.status_code == 200

    def test_send_structured_content(self, client, screen):
        """Test sending structured content items."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {"type": "text", "value": "Plain text"},
                    {"type": "markdown", "value": "# Heading"},
                    {"type": "text", "value": "Colored", "panel_color": "#c0392b"},
                ]
            },
        )
        assert response.status_code == 200

    def test_send_with_wrap_option(self, client, screen):
        """Test sending text with wrap option."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {"type": "text", "value": "Wrapped text", "wrap": True},
                    {"type": "text", "value": "No wrap", "wrap": False},
                ]
            },
        )
        assert response.status_code == 200

    def test_send_image_with_mode(self, client, screen):
        """Test sending an image with display mode."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {"type": "image", "url": "https://example.com/image.jpg", "image_mode": "cover"}
                ]
            },
        )
        assert response.status_code == 200

    def test_send_video(self, client, screen):
        """Test sending a video."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "video",
                        "url": "https://example.com/video.mp4",
                        "autoplay": True,
                        "loop": True,
                        "muted": False,
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_wrong_api_key(self, client, screen):
        """Test that wrong API key is rejected."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": "wrong_key"},
            json={"content": ["Should fail"]},
        )
        assert response.status_code == 401

    def test_missing_api_key(self, client, screen):
        """Test that missing API key is rejected."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message", json={"content": ["Should fail"]}
        )
        assert response.status_code == 422  # Validation error

    def test_nonexistent_screen(self, client, screen):
        """Test sending to a nonexistent screen."""
        response = client.post(
            "/api/v1/screens/nonexistent123/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Should fail"]},
        )
        assert response.status_code == 404


class TestScreenManagement:
    """Tests for screen management endpoints."""

    def test_delete_screen(self, client):
        """Test deleting a screen."""
        # Create a screen
        create_response = client.post("/api/v1/screens")
        screen = create_response.json()

        # Delete it (requires API key)
        delete_response = client.delete(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

        # Verify it's gone
        message_response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Should fail"]},
        )
        assert message_response.status_code == 404

    def test_delete_nonexistent_screen(self, client):
        """Test deleting a nonexistent screen."""
        response = client.delete(
            "/api/v1/screens/nonexistent123",
            headers={"X-API-Key": "sk_fake_key"},
        )
        assert response.status_code == 404

    def test_update_screen_name(self, client, screen):
        """Test updating a screen's name."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            json={"name": "My Test Screen"},
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["name"] == "My Test Screen"

    def test_update_screen_name_empty(self, client, screen):
        """Test clearing a screen's name."""
        # First set a name
        client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            json={"name": "Test"},
            headers={"X-API-Key": screen["api_key"]},
        )

        # Then clear it
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            json={"name": ""},
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200

    def test_update_nonexistent_screen_name(self, client, screen):
        """Test updating name of nonexistent screen."""
        response = client.patch(
            "/api/v1/screens/nonexistent123",
            json={"name": "Test"},
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 404

    def test_reload_screen(self, client, screen):
        """Test the reload endpoint."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/reload",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "viewers_reloaded" in response.json()

    def test_reload_nonexistent_screen(self, client):
        """Test reloading a nonexistent screen."""
        response = client.post(
            "/api/v1/screens/nonexistent123/reload",
            headers={"X-API-Key": "sk_fake_key"},
        )
        assert response.status_code == 404


class TestScreenViewer:
    """Tests for the screen viewer page."""

    def test_view_screen(self, client, screen):
        """Test that the screen viewer page loads."""
        response = client.get(f"/screen/{screen['screen_id']}")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_view_nonexistent_screen(self, client):
        """Test viewing a nonexistent screen."""
        response = client.get("/screen/nonexistent123")
        assert response.status_code == 404


class TestAdminPage:
    """Tests for the admin page."""

    def test_admin_page_loads(self, client):
        """Test that the admin page loads."""
        response = client.get("/admin/screens")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Big Beautiful Screens" in response.text

    def test_admin_page_shows_screens(self, client, screen):
        """Test that the admin page shows created screens."""
        response = client.get("/admin/screens")
        assert response.status_code == 200
        assert screen["screen_id"] in response.text


class TestContentAutoDetection:
    """Tests for content type auto-detection."""

    def test_detect_plain_text(self, client, screen):
        """Test that plain text is detected correctly."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Just plain text"]},
        )
        assert response.status_code == 200

    def test_detect_markdown(self, client, screen):
        """Test that markdown is detected correctly."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["# This is a heading\n\nWith **bold** text"]},
        )
        assert response.status_code == 200

    def test_detect_image_url(self, client, screen):
        """Test that image URLs are detected correctly."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["https://example.com/image.png"]},
        )
        assert response.status_code == 200

    def test_detect_video_url(self, client, screen):
        """Test that video URLs are detected correctly."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["https://example.com/video.mp4"]},
        )
        assert response.status_code == 200


class TestPages:
    """Tests for multi-page functionality."""

    def test_list_pages_empty(self, client, screen):
        """Test listing pages for a new screen."""
        response = client.get(f"/api/v1/screens/{screen['screen_id']}/pages")
        assert response.status_code == 200
        data = response.json()
        assert "pages" in data
        assert "rotation" in data

    def test_create_page(self, client, screen):
        """Test creating a new page."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/alerts",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Alert message!"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["page"]["name"] == "alerts"

    def test_update_existing_page(self, client, screen):
        """Test updating an existing page."""
        # Create page
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/weather",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Sunny"]},
        )

        # Update page
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/weather",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Rainy"]},
        )
        assert response.status_code == 200
        assert response.json()["page"]["content"][0]["value"] == "Rainy"

    def test_create_page_with_duration(self, client, screen):
        """Test creating a page with custom duration."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/promo",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Special offer!"], "duration": 10},
        )
        assert response.status_code == 200
        assert response.json()["page"]["duration"] == 10

    def test_create_ephemeral_page(self, client, screen):
        """Test creating an ephemeral page with expiry."""
        from datetime import datetime, timedelta

        expires = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/flash",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Flash sale!"], "expires_at": expires},
        )
        assert response.status_code == 200
        assert response.json()["page"]["expires_at"] is not None

    def test_delete_page(self, client, screen):
        """Test deleting a page."""
        # Create page
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/temp",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Temporary"]},
        )

        # Delete page
        response = client.delete(
            f"/api/v1/screens/{screen['screen_id']}/pages/temp",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_cannot_delete_default_page(self, client, screen):
        """Test that the default page cannot be deleted."""
        response = client.delete(
            f"/api/v1/screens/{screen['screen_id']}/pages/default",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 400

    def test_delete_nonexistent_page(self, client, screen):
        """Test deleting a page that doesn't exist."""
        response = client.delete(
            f"/api/v1/screens/{screen['screen_id']}/pages/nonexistent",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 404

    def test_page_wrong_api_key(self, client, screen):
        """Test that wrong API key is rejected for page operations."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/test",
            headers={"X-API-Key": "wrong_key"},
            json={"content": ["Should fail"]},
        )
        assert response.status_code == 401


class TestRotation:
    """Tests for rotation and display settings."""

    def test_update_rotation_settings(self, client, screen):
        """Test updating rotation settings."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"rotation_enabled": True, "rotation_interval": 15},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["enabled"] is True
        assert data["settings"]["interval"] == 15

    def test_disable_rotation(self, client, screen):
        """Test disabling rotation."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"rotation_enabled": False},
        )
        assert response.status_code == 200
        assert response.json()["settings"]["enabled"] is False

    def test_rotation_wrong_api_key(self, client, screen):
        """Test that wrong API key is rejected for rotation settings."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": "wrong_key"},
            json={"rotation_enabled": True},
        )
        assert response.status_code == 401

    def test_update_gap_setting(self, client, screen):
        """Test updating gap setting."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"gap": "0.5rem"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["gap"] == "0.5rem"

    def test_update_gap_zero(self, client, screen):
        """Test setting gap to zero for edge-to-edge panels."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"gap": "0"},
        )
        assert response.status_code == 200
        assert response.json()["settings"]["gap"] == "0"

    def test_update_border_radius(self, client, screen):
        """Test updating border radius setting."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"border_radius": "0.5rem"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["border_radius"] == "0.5rem"

    def test_update_border_radius_zero(self, client, screen):
        """Test setting border radius to zero for sharp corners."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"border_radius": "0"},
        )
        assert response.status_code == 200
        assert response.json()["settings"]["border_radius"] == "0"

    def test_update_panel_shadow(self, client, screen):
        """Test updating panel shadow setting."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"panel_shadow": "0 4px 12px rgba(0,0,0,0.3)"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["panel_shadow"] == "0 4px 12px rgba(0,0,0,0.3)"

    def test_panel_shadow_has_default_theme_value(self, client, screen):
        """Test that panel shadow has default theme value for new screens."""
        # Get settings without modifying shadow
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"gap": "1rem"},
        )
        assert response.status_code == 200
        # New screens get the default theme applied
        assert response.json()["settings"]["panel_shadow"] is not None

    def test_reorder_pages(self, client, screen):
        """Test reordering pages."""
        # Create some pages
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/default",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Default"]},
        )
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/page1",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Page 1"]},
        )
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/page2",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Page 2"]},
        )

        # Reorder
        response = client.put(
            f"/api/v1/screens/{screen['screen_id']}/pages/order",
            headers={"X-API-Key": screen["api_key"]},
            json={"page_names": ["page2", "page1", "default"]},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_update_background_color(self, client, screen):
        """Test updating screen-level background color."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"background_color": "#1a1a2e"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["background_color"] == "#1a1a2e"

    def test_update_background_color_gradient(self, client, screen):
        """Test updating screen-level background color with a gradient."""
        gradient = "linear-gradient(90deg, rgba(42,123,155,1) 0%, rgba(87,199,133,1) 100%)"
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"background_color": gradient},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["background_color"] == gradient

    def test_update_panel_color(self, client, screen):
        """Test updating screen-level panel color."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"panel_color": "#16213e"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["panel_color"] == "#16213e"

    def test_update_font_family(self, client, screen):
        """Test updating screen-level font family."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"font_family": "Georgia, serif"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["font_family"] == "Georgia, serif"

    def test_update_font_color(self, client, screen):
        """Test updating screen-level font color."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"font_color": "#f1c40f"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["font_color"] == "#f1c40f"

    def test_color_settings_have_default_theme_values(self, client, screen):
        """Test that color/font settings have default theme values for new screens."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"gap": "1rem"},
        )
        assert response.status_code == 200
        settings = response.json()["settings"]
        # New screens get the default theme applied
        assert settings["background_color"] is not None
        assert settings["panel_color"] is not None
        assert settings["font_family"] is not None
        assert settings["font_color"] is not None
        assert settings["theme"] == "default"

    def test_update_transition_setting(self, client, screen):
        """Test updating transition setting."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"transition": "fade"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["transition"] == "fade"

    def test_update_transition_duration(self, client, screen):
        """Test updating transition duration setting."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"transition_duration": 800},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["transition_duration"] == 800

    def test_update_transition_slide_left(self, client, screen):
        """Test updating transition to slide-left."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"transition": "slide-left", "transition_duration": 500},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["transition"] == "slide-left"
        assert data["settings"]["transition_duration"] == 500

    def test_transition_default_value(self, client, screen):
        """Test that transition defaults to 'none'."""
        response = client.get(f"/api/v1/screens/{screen['screen_id']}")
        assert response.status_code == 200
        settings = response.json()["settings"]
        assert settings["transition"] == "none"
        assert settings["transition_duration"] == 500

    def test_page_with_transition_override(self, client, screen):
        """Test creating a page with transition override."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/test_page",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["Test content"],
                "transition": "slide-left",
                "transition_duration": 300,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["page"]["transition"] == "slide-left"
        assert data["page"]["transition_duration"] == 300

    def test_page_transition_override_persists(self, client, screen):
        """Test that page transition override persists in pages list."""
        # Create page with transition
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/persist_test",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["Test"],
                "transition": "fade",
                "transition_duration": 600,
            },
        )

        # Get pages list
        response = client.get(f"/api/v1/screens/{screen['screen_id']}/pages")
        assert response.status_code == 200
        pages = response.json()["pages"]

        # Find the page we created
        test_page = next((p for p in pages if p["name"] == "persist_test"), None)
        assert test_page is not None
        assert test_page["transition"] == "fade"
        assert test_page["transition_duration"] == 600


class TestWidgets:
    """Tests for widget content types."""

    def test_send_clock_widget_digital(self, client, screen):
        """Test sending a digital clock widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "clock",
                        "widget_config": {"style": "digital", "format": "12h"},
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_clock_widget_analog(self, client, screen):
        """Test sending an analog clock widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "clock",
                        "widget_config": {"style": "analog", "show_numbers": True},
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_send_clock_widget_with_timezone(self, client, screen):
        """Test sending a clock widget with timezone."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "clock",
                        "widget_config": {
                            "style": "digital",
                            "timezone": "America/New_York",
                            "format": "24h",
                            "show_seconds": True,
                            "show_date": True,
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_send_widget_with_empty_config(self, client, screen):
        """Test sending a widget with empty config (uses defaults)."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": [{"type": "widget", "widget_type": "clock", "widget_config": {}}]},
        )
        assert response.status_code == 200

    def test_send_widget_without_config(self, client, screen):
        """Test sending a widget without config field."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": [{"type": "widget", "widget_type": "clock"}]},
        )
        assert response.status_code == 200

    def test_send_multiple_widgets(self, client, screen):
        """Test sending multiple widgets in one message."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "clock",
                        "widget_config": {"style": "digital"},
                    },
                    {
                        "type": "widget",
                        "widget_type": "clock",
                        "widget_config": {"style": "analog"},
                    },
                ]
            },
        )
        assert response.status_code == 200

    def test_send_widget_with_panel_styling(self, client, screen):
        """Test sending a widget with per-panel styling."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "clock",
                        "widget_config": {"style": "digital"},
                        "panel_color": "#1a1a2e",
                        "font_color": "#ffffff",
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_send_widget_mixed_content(self, client, screen):
        """Test sending widgets mixed with other content types."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {"type": "markdown", "value": "# Dashboard"},
                    {
                        "type": "widget",
                        "widget_type": "clock",
                        "widget_config": {"style": "digital"},
                    },
                    {"type": "text", "value": "Status: Online"},
                ]
            },
        )
        assert response.status_code == 200

    def test_create_page_with_widget(self, client, screen):
        """Test creating a page with widget content."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/clock-page",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "clock",
                        "widget_config": {"style": "analog", "timezone": "UTC"},
                    }
                ]
            },
        )
        assert response.status_code == 200
        page = response.json()["page"]
        assert page["name"] == "clock-page"
        assert page["content"][0]["type"] == "widget"
        assert page["content"][0]["widget_type"] == "clock"

    def test_send_countdown_widget(self, client, screen):
        """Test sending a countdown widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "countdown",
                        "widget_config": {"target": "2099-12-31T00:00:00Z"},
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_countdown_with_expired_text(self, client, screen):
        """Test sending a countdown with custom expired text."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "countdown",
                        "widget_config": {
                            "target": "2099-12-31T00:00:00Z",
                            "expired_text": "Happy New Year!",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_send_countdown_display_options(self, client, screen):
        """Test sending a countdown with display options."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "countdown",
                        "widget_config": {
                            "target": "2099-12-31T00:00:00Z",
                            "show_days": True,
                            "show_hours": True,
                            "show_minutes": True,
                            "show_seconds": False,
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_send_countdown_simple_style(self, client, screen):
        """Test sending a countdown with simple style."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "countdown",
                        "widget_config": {
                            "target": "2099-12-31T00:00:00Z",
                            "style": "simple",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_send_countup_widget(self, client, screen):
        """Test sending a count-up widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "countup",
                        "widget_config": {"start": "2025-01-01T00:00:00Z"},
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_countup_with_label(self, client, screen):
        """Test sending a count-up with label text."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "countup",
                        "widget_config": {
                            "start": "2025-01-01T00:00:00Z",
                            "label": "Since last update",
                            "label_position": "below",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_send_countup_display_options(self, client, screen):
        """Test sending a count-up with display options."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "countup",
                        "widget_config": {
                            "start": "2025-01-01T00:00:00Z",
                            "show_days": True,
                            "show_hours": True,
                            "show_minutes": True,
                            "show_seconds": False,
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_send_countup_simple_style(self, client, screen):
        """Test sending a count-up with simple style."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "countup",
                        "widget_config": {
                            "start": "2025-01-01T00:00:00Z",
                            "style": "simple",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200

    def test_send_chart_widget_line(self, client, screen):
        """Test sending a line chart widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "chart",
                        "widget_config": {
                            "chart_type": "line",
                            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                            "values": [10, 25, 15, 30, 22],
                            "label": "Sales",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_chart_widget_bar(self, client, screen):
        """Test sending a bar chart widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "chart",
                        "widget_config": {
                            "chart_type": "bar",
                            "labels": ["Q1", "Q2", "Q3", "Q4"],
                            "values": [120, 190, 300, 250],
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_chart_widget_multi_series(self, client, screen):
        """Test sending a chart with multiple datasets."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "chart",
                        "widget_config": {
                            "chart_type": "bar",
                            "labels": ["Q1", "Q2", "Q3", "Q4"],
                            "datasets": [
                                {
                                    "label": "2023",
                                    "values": [120, 190, 300, 250],
                                    "color": "#3498db",
                                },
                                {
                                    "label": "2024",
                                    "values": [150, 220, 280, 310],
                                    "color": "#2ecc71",
                                },
                            ],
                            "x_axis_label": "Quarter",
                            "y_axis_label": "Revenue ($K)",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_chart_widget_pie(self, client, screen):
        """Test sending a pie chart widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "chart",
                        "widget_config": {
                            "chart_type": "pie",
                            "labels": ["Desktop", "Mobile", "Tablet"],
                            "values": [60, 30, 10],
                            "label": "Traffic Sources",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_chart_widget_doughnut(self, client, screen):
        """Test sending a doughnut chart widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "chart",
                        "widget_config": {
                            "chart_type": "doughnut",
                            "labels": ["Completed", "In Progress", "Pending"],
                            "values": [45, 35, 20],
                            "label": "Task Status",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_chart_widget_radar(self, client, screen):
        """Test sending a radar chart widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "chart",
                        "widget_config": {
                            "chart_type": "radar",
                            "labels": ["Speed", "Reliability", "Comfort", "Safety", "Efficiency"],
                            "values": [85, 90, 70, 95, 80],
                            "label": "Performance",
                            "fill": True,
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_chart_widget_polar_area(self, client, screen):
        """Test sending a polarArea chart widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "chart",
                        "widget_config": {
                            "chart_type": "polarArea",
                            "labels": ["Red", "Blue", "Yellow", "Green"],
                            "values": [11, 16, 7, 14],
                            "label": "Dataset",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_chart_widget_scatter(self, client, screen):
        """Test sending a scatter chart widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "chart",
                        "widget_config": {
                            "chart_type": "scatter",
                            "datasets": [
                                {
                                    "label": "Group A",
                                    "data": [
                                        {"x": 10, "y": 20},
                                        {"x": 15, "y": 10},
                                        {"x": 25, "y": 30},
                                    ],
                                    "color": "#e74c3c",
                                }
                            ],
                            "x_axis_label": "X Values",
                            "y_axis_label": "Y Values",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_chart_widget_bubble(self, client, screen):
        """Test sending a bubble chart widget."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "widget",
                        "widget_type": "chart",
                        "widget_config": {
                            "chart_type": "bubble",
                            "datasets": [
                                {
                                    "label": "Sales",
                                    "data": [
                                        {"x": 20, "y": 30, "r": 10},
                                        {"x": 40, "y": 10, "r": 15},
                                        {"x": 30, "y": 20, "r": 8},
                                    ],
                                    "color": "#9b59b6",
                                }
                            ],
                            "x_axis_label": "Revenue",
                            "y_axis_label": "Profit",
                        },
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestThemes:
    """Tests for theme functionality."""

    def test_list_themes(self, client):
        """Test listing available themes."""
        response = client.get("/api/v1/themes")
        assert response.status_code == 200
        data = response.json()
        assert "themes" in data
        assert len(data["themes"]) >= 13  # At least 13 themes defined
        # Check a theme has expected properties
        theme = data["themes"][0]
        assert "name" in theme
        assert "background_color" in theme
        assert "panel_color" in theme
        assert "font_family" in theme
        assert "font_color" in theme
        assert "gap" in theme
        assert "border_radius" in theme

    def test_apply_theme(self, client, screen):
        """Test applying a theme sets all values."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"theme": "catppuccin-mocha"},
        )
        assert response.status_code == 200
        settings = response.json()["settings"]
        assert settings["theme"] == "catppuccin-mocha"
        assert "1e1e2e" in settings["background_color"]  # Now uses gradient
        assert "49, 50, 68" in settings["panel_color"]  # Now uses gradient
        assert settings["font_color"] == "#cdd6f4"

    def test_apply_theme_with_override(self, client, screen):
        """Test applying a theme with overrides."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"theme": "catppuccin-mocha", "gap": "0", "border_radius": "0"},
        )
        assert response.status_code == 200
        settings = response.json()["settings"]
        assert settings["theme"] == "catppuccin-mocha"
        # Theme values applied
        assert "1e1e2e" in settings["background_color"]  # Now uses gradient
        # Override values used
        assert settings["gap"] == "0"
        assert settings["border_radius"] == "0"

    def test_invalid_theme(self, client, screen):
        """Test applying an unknown theme returns 400."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"theme": "nonexistent-theme"},
        )
        assert response.status_code == 400
        assert "Unknown theme" in response.json()["detail"]

    def test_theme_requires_api_key(self, client, screen):
        """Test that applying a theme requires API key."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}", json={"theme": "catppuccin-mocha"}
        )
        # 422 because X-API-Key header is required by FastAPI validation
        assert response.status_code == 422


class TestLayouts:
    """Tests for layout presets and custom layouts."""

    def test_list_layouts(self, client):
        """Test listing all available layout presets."""
        response = client.get("/api/v1/layouts")
        assert response.status_code == 200
        data = response.json()
        assert "layouts" in data
        assert len(data["layouts"]) > 0

        # Check some expected presets exist
        layout_names = [layout["name"] for layout in data["layouts"]]
        assert "auto" in layout_names
        assert "vertical" in layout_names
        assert "grid-2x2" in layout_names
        assert "dashboard-header" in layout_names

    def test_layout_preset_structure(self, client):
        """Test that layout presets have required fields."""
        response = client.get("/api/v1/layouts")
        data = response.json()

        for layout in data["layouts"]:
            assert "name" in layout
            assert "description" in layout

    def test_message_with_layout_preset(self, client, screen):
        """Test sending a message with a layout preset name."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["Item 1", "Item 2", "Item 3", "Item 4"],
                "layout": "vertical",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_message_with_custom_layout(self, client, screen):
        """Test sending a message with a custom layout configuration."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["Header", "Panel 1", "Panel 2", "Panel 3"],
                "layout": {
                    "columns": 3,
                    "rows": "auto 1fr",
                    "header_rows": 1,
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_message_with_grid_positioning(self, client, screen):
        """Test sending a message with per-panel grid positioning."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {"type": "text", "value": "Title", "grid_column": "1 / -1"},
                    {
                        "type": "text",
                        "value": "Main",
                        "grid_column": "span 2",
                        "grid_row": "span 2",
                    },
                    {"type": "text", "value": "Side 1"},
                    {"type": "text", "value": "Side 2"},
                ],
                "layout": {"columns": 3, "rows": "auto 1fr 1fr"},
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_screen_default_layout(self, client, screen):
        """Test setting default layout for a screen."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"default_layout": "vertical-12"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["default_layout"] == "vertical-12"

    def test_screen_default_layout_custom(self, client, screen):
        """Test setting a custom default layout for a screen."""
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}",
            headers={"X-API-Key": screen["api_key"]},
            json={"default_layout": {"columns": 2, "rows": 6}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings"]["default_layout"]["columns"] == 2
        assert data["settings"]["default_layout"]["rows"] == 6

    def test_page_with_layout(self, client, screen):
        """Test creating a page with a specific layout."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/menu",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["# Menu", "Item 1", "Item 2", "Item 3"],
                "layout": "menu-board",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["page"]["layout"] == "menu-board"

    def test_page_layout_in_list(self, client, screen):
        """Test that page layout is included in pages list."""
        # Create page with layout
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/test-layout",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["Test"],
                "layout": "grid-3x3",
            },
        )

        # Get pages list
        response = client.get(f"/api/v1/screens/{screen['screen_id']}/pages")
        assert response.status_code == 200
        pages = response.json()["pages"]

        # Find our page
        test_page = next((p for p in pages if p["name"] == "test-layout"), None)
        assert test_page is not None
        assert test_page["layout"] == "grid-3x3"

    def test_patch_page_layout(self, client, screen):
        """Test updating a page's layout via PATCH."""
        # Create page
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/pages/patch-layout-test",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Test"]},
        )

        # Update layout
        response = client.patch(
            f"/api/v1/screens/{screen['screen_id']}/pages/patch-layout-test",
            headers={"X-API-Key": screen["api_key"]},
            json={"layout": "horizontal"},
        )
        assert response.status_code == 200
        assert response.json()["page"]["layout"] == "horizontal"


class TestDebugMode:
    """Tests for debug mode functionality."""

    def test_enable_debug(self, client, screen):
        """Test enabling debug mode."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/debug?enabled=true",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["debug_enabled"] is True
        assert "viewers" in data

    def test_disable_debug(self, client, screen):
        """Test disabling debug mode."""
        # Enable first
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/debug?enabled=true",
            headers={"X-API-Key": screen["api_key"]},
        )

        # Disable
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/debug?enabled=false",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["debug_enabled"] is False

    def test_toggle_debug(self, client, screen):
        """Test toggling debug mode."""
        # First toggle (should enable)
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/debug?enabled=toggle",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200
        first_state = response.json()["debug_enabled"]

        # Second toggle (should flip)
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/debug?enabled=toggle",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200
        second_state = response.json()["debug_enabled"]
        assert second_state != first_state

    def test_debug_state_persists(self, client, screen):
        """Test that debug state is persisted in database."""
        # Enable debug
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/debug?enabled=true",
            headers={"X-API-Key": screen["api_key"]},
        )

        # Get screen data - debug_enabled should be in rotation settings
        response = client.get(
            f"/api/v1/screens/{screen['screen_id']}/pages",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200
        assert response.json()["rotation"]["debug_enabled"] is True

        # Disable and verify
        client.post(
            f"/api/v1/screens/{screen['screen_id']}/debug?enabled=false",
            headers={"X-API-Key": screen["api_key"]},
        )

        response = client.get(
            f"/api/v1/screens/{screen['screen_id']}/pages",
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200
        assert response.json()["rotation"]["debug_enabled"] is False

    def test_debug_wrong_api_key(self, client, screen):
        """Test that wrong API key is rejected for debug toggle."""
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/debug?enabled=true",
            headers={"X-API-Key": "wrong_key"},
        )
        assert response.status_code == 401

    def test_debug_nonexistent_screen(self, client):
        """Test toggling debug on nonexistent screen."""
        response = client.post(
            "/api/v1/screens/nonexistent123/debug?enabled=true",
            headers={"X-API-Key": "sk_fake_key"},
        )
        assert response.status_code == 404
