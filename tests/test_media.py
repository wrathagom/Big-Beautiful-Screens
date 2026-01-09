"""Tests for Media Library API."""

import io
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Use a temporary database and storage for tests
@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    """Set up a temporary database and storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set the database path via environment variable before importing
        test_db_path = str(Path(tmpdir) / "test_media.db")
        test_media_path = str(Path(tmpdir) / "media")
        os.makedirs(test_media_path, exist_ok=True)

        os.environ["SQLITE_PATH"] = test_db_path
        os.environ["STORAGE_LOCAL_PATH"] = test_media_path
        os.environ["STORAGE_BACKEND"] = "local"

        # Clear the cached settings so it picks up the new env var
        from app.config import get_settings

        get_settings.cache_clear()

        # Reset the database singleton
        from app.db.factory import reset_database

        reset_database()

        # Clear storage cache
        from app.storage import clear_storage_cache

        clear_storage_cache()

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
        clear_storage_cache()
        get_settings.cache_clear()


@pytest.fixture
def client(setup_test_environment):
    """Create a test client."""
    return TestClient(setup_test_environment)


def create_test_image() -> tuple[bytes, str]:
    """Create a simple PNG image for testing."""
    # 1x1 pixel red PNG
    png_data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00"
        b"\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00"
        b"\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return png_data, "image/png"


class TestMediaUpload:
    """Tests for media upload."""

    def test_upload_image(self, client):
        """Test uploading a PNG image."""
        image_data, content_type = create_test_image()

        response = client.post(
            "/api/v1/media/upload",
            files={"file": ("test.png", io.BytesIO(image_data), content_type)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "media" in data
        assert data["media"]["filename"] == "test.png"
        assert data["media"]["original_filename"] == "test.png"
        assert data["media"]["content_type"] == "image/png"
        assert data["media"]["size_bytes"] == len(image_data)
        assert "url" in data["media"]
        assert "id" in data["media"]

    def test_upload_invalid_type(self, client):
        """Test uploading an unsupported file type."""
        response = client.post(
            "/api/v1/media/upload",
            files={"file": ("test.exe", io.BytesIO(b"binary data"), "application/x-executable")},
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_svg(self, client):
        """Test uploading an SVG image."""
        svg_data = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="10"/></svg>'

        response = client.post(
            "/api/v1/media/upload",
            files={"file": ("test.svg", io.BytesIO(svg_data), "image/svg+xml")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["media"]["content_type"] == "image/svg+xml"


class TestMediaList:
    """Tests for listing media."""

    def test_list_media(self, client):
        """Test listing all media."""
        # Upload a test image first
        image_data, content_type = create_test_image()
        client.post(
            "/api/v1/media/upload",
            files={"file": ("list_test.png", io.BytesIO(image_data), content_type)},
        )

        response = client.get("/api/v1/media")

        assert response.status_code == 200
        data = response.json()
        assert "media" in data
        assert "total_count" in data
        assert "storage_used_bytes" in data
        assert "storage_quota_bytes" in data
        assert data["total_count"] >= 1

    def test_list_media_pagination(self, client):
        """Test pagination of media list."""
        response = client.get("/api/v1/media?page=1&per_page=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["media"]) <= 5

    def test_list_media_filter_image(self, client):
        """Test filtering media by image type."""
        response = client.get("/api/v1/media?content_type=image")

        assert response.status_code == 200
        data = response.json()
        for item in data["media"]:
            assert item["content_type"].startswith("image/")


class TestMediaGet:
    """Tests for getting a single media item."""

    def test_get_media(self, client):
        """Test getting a specific media item."""
        # Upload first
        image_data, content_type = create_test_image()
        upload_response = client.post(
            "/api/v1/media/upload",
            files={"file": ("get_test.png", io.BytesIO(image_data), content_type)},
        )
        media_id = upload_response.json()["media"]["id"]

        # Get the media
        response = client.get(f"/api/v1/media/{media_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["media"]["id"] == media_id

    def test_get_nonexistent_media(self, client):
        """Test getting a media item that doesn't exist."""
        response = client.get("/api/v1/media/nonexistent-id")

        assert response.status_code == 404


class TestMediaDelete:
    """Tests for deleting media."""

    def test_delete_media(self, client):
        """Test deleting a media item."""
        # Upload first
        image_data, content_type = create_test_image()
        upload_response = client.post(
            "/api/v1/media/upload",
            files={"file": ("delete_test.png", io.BytesIO(image_data), content_type)},
        )
        media_id = upload_response.json()["media"]["id"]

        # Delete
        response = client.delete(f"/api/v1/media/{media_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's gone
        get_response = client.get(f"/api/v1/media/{media_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_media(self, client):
        """Test deleting a media item that doesn't exist."""
        response = client.delete("/api/v1/media/nonexistent-id")

        assert response.status_code == 404


class TestMediaServing:
    """Tests for serving media files."""

    def test_serve_uploaded_file(self, client):
        """Test that uploaded files can be served."""
        # Upload
        image_data, content_type = create_test_image()
        upload_response = client.post(
            "/api/v1/media/upload",
            files={"file": ("serve_test.png", io.BytesIO(image_data), content_type)},
        )

        media_url = upload_response.json()["media"]["url"]
        # Extract the file path from the URL
        # URL format: http://testserver/media/files/{storage_path}
        file_path = media_url.split("/media/files/")[-1]

        # Serve the file
        response = client.get(f"/media/files/{file_path}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content == image_data

    def test_serve_nonexistent_file(self, client):
        """Test serving a file that doesn't exist."""
        response = client.get("/media/files/nonexistent/path/file.png")

        assert response.status_code == 404
