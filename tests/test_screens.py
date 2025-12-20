"""Tests for Big Beautiful Screens API."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import os

# Use a temporary database for tests
@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Set up a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override the database path before importing the app
        import app.database as db_module
        db_module.DB_PATH = Path(tmpdir) / "test_screens.db"

        from app.main import app

        # Initialize the database
        import asyncio
        asyncio.get_event_loop().run_until_complete(db_module.init_db())

        yield app


@pytest.fixture
def client(setup_test_db):
    """Create a test client."""
    return TestClient(setup_test_db)


@pytest.fixture
def screen(client):
    """Create a test screen and return its data."""
    response = client.post("/api/screens")
    assert response.status_code == 200
    return response.json()


class TestScreenCreation:
    """Tests for screen creation."""

    def test_create_screen(self, client):
        """Test creating a new screen."""
        response = client.post("/api/screens")
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
        response1 = client.post("/api/screens")
        response2 = client.post("/api/screens")

        screen1 = response1.json()
        screen2 = response2.json()

        assert screen1["screen_id"] != screen2["screen_id"]
        assert screen1["api_key"] != screen2["api_key"]


class TestMessages:
    """Tests for sending messages to screens."""

    def test_send_simple_message(self, client, screen):
        """Test sending a simple text message."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Hello, World!"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "viewers" in data

    def test_send_multiple_panels(self, client, screen):
        """Test sending multiple content panels."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Panel 1", "Panel 2", "Panel 3"]}
        )
        assert response.status_code == 200

    def test_send_with_colors(self, client, screen):
        """Test sending a message with custom colors."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["Colored panel"],
                "background_color": "#1a1a2e",
                "panel_color": "#16213e"
            }
        )
        assert response.status_code == 200

    def test_send_with_fonts(self, client, screen):
        """Test sending a message with custom fonts."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": ["Custom font"],
                "font_family": "Georgia, serif",
                "font_color": "#f1c40f"
            }
        )
        assert response.status_code == 200

    def test_send_structured_content(self, client, screen):
        """Test sending structured content items."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {"type": "text", "value": "Plain text"},
                    {"type": "markdown", "value": "# Heading"},
                    {"type": "text", "value": "Colored", "color": "#c0392b"}
                ]
            }
        )
        assert response.status_code == 200

    def test_send_with_wrap_option(self, client, screen):
        """Test sending text with wrap option."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {"type": "text", "value": "Wrapped text", "wrap": True},
                    {"type": "text", "value": "No wrap", "wrap": False}
                ]
            }
        )
        assert response.status_code == 200

    def test_send_image_with_mode(self, client, screen):
        """Test sending an image with display mode."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {"type": "image", "url": "https://example.com/image.jpg", "image_mode": "cover"}
                ]
            }
        )
        assert response.status_code == 200

    def test_send_video(self, client, screen):
        """Test sending a video."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={
                "content": [
                    {
                        "type": "video",
                        "url": "https://example.com/video.mp4",
                        "autoplay": True,
                        "loop": True,
                        "muted": False
                    }
                ]
            }
        )
        assert response.status_code == 200

    def test_wrong_api_key(self, client, screen):
        """Test that wrong API key is rejected."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": "wrong_key"},
            json={"content": ["Should fail"]}
        )
        assert response.status_code == 401

    def test_missing_api_key(self, client, screen):
        """Test that missing API key is rejected."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            json={"content": ["Should fail"]}
        )
        assert response.status_code == 422  # Validation error

    def test_nonexistent_screen(self, client, screen):
        """Test sending to a nonexistent screen."""
        response = client.post(
            "/api/screens/nonexistent123/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Should fail"]}
        )
        assert response.status_code == 404


class TestScreenManagement:
    """Tests for screen management endpoints."""

    def test_delete_screen(self, client):
        """Test deleting a screen."""
        # Create a screen
        create_response = client.post("/api/screens")
        screen = create_response.json()

        # Delete it
        delete_response = client.delete(f"/api/screens/{screen['screen_id']}")
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

        # Verify it's gone
        message_response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Should fail"]}
        )
        assert message_response.status_code == 404

    def test_delete_nonexistent_screen(self, client):
        """Test deleting a nonexistent screen."""
        response = client.delete("/api/screens/nonexistent123")
        assert response.status_code == 404

    def test_update_screen_name(self, client, screen):
        """Test updating a screen's name."""
        response = client.patch(
            f"/api/screens/{screen['screen_id']}?name=My%20Test%20Screen"
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["name"] == "My Test Screen"

    def test_update_screen_name_empty(self, client, screen):
        """Test clearing a screen's name."""
        # First set a name
        client.patch(f"/api/screens/{screen['screen_id']}?name=Test")

        # Then clear it
        response = client.patch(f"/api/screens/{screen['screen_id']}?name=")
        assert response.status_code == 200

    def test_update_nonexistent_screen_name(self, client):
        """Test updating name of nonexistent screen."""
        response = client.patch("/api/screens/nonexistent123?name=Test")
        assert response.status_code == 404

    def test_reload_screen(self, client, screen):
        """Test the reload endpoint."""
        response = client.post(f"/api/screens/{screen['screen_id']}/reload")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "viewers_reloaded" in response.json()

    def test_reload_nonexistent_screen(self, client):
        """Test reloading a nonexistent screen."""
        response = client.post("/api/screens/nonexistent123/reload")
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
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["Just plain text"]}
        )
        assert response.status_code == 200

    def test_detect_markdown(self, client, screen):
        """Test that markdown is detected correctly."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["# This is a heading\n\nWith **bold** text"]}
        )
        assert response.status_code == 200

    def test_detect_image_url(self, client, screen):
        """Test that image URLs are detected correctly."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["https://example.com/image.png"]}
        )
        assert response.status_code == 200

    def test_detect_video_url(self, client, screen):
        """Test that video URLs are detected correctly."""
        response = client.post(
            f"/api/screens/{screen['screen_id']}/message",
            headers={"X-API-Key": screen["api_key"]},
            json={"content": ["https://example.com/video.mp4"]}
        )
        assert response.status_code == 200
