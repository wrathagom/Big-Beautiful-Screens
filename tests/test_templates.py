"""Tests for Templates API endpoints."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Use a temporary database for tests
@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Set up a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set the database path via environment variable before importing
        test_db_path = str(Path(tmpdir) / "test_templates.db")
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


@pytest.fixture
def template(client, screen):
    """Create a test template from a screen."""
    response = client.post(
        "/api/v1/templates",
        json={
            "screen_id": screen["screen_id"],
            "name": "Test Template",
            "description": "A test template",
            "category": "custom",
        },
    )
    assert response.status_code == 200
    return response.json()


class TestListTemplates:
    """Tests for listing templates."""

    def test_list_templates_empty(self, client):
        """Test listing templates when initially empty (no user templates)."""
        response = client.get("/api/v1/templates")
        assert response.status_code == 200

        data = response.json()
        assert "templates" in data
        assert "page" in data
        assert "total_count" in data
        # System templates are seeded on startup, so we may have some
        assert isinstance(data["templates"], list)

    def test_list_templates_pagination(self, client):
        """Test pagination parameters."""
        response = client.get("/api/v1/templates?page=1&per_page=5")
        assert response.status_code == 200

        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 5

    def test_list_templates_filter_by_category(self, client, template):
        """Test filtering templates by category."""
        # Filter by the custom category
        response = client.get("/api/v1/templates?category=custom")
        assert response.status_code == 200

        data = response.json()
        assert all(t["category"] == "custom" for t in data["templates"])

    def test_list_templates_filter_by_type(self, client, template):
        """Test filtering templates by type."""
        # Filter by user type
        response = client.get("/api/v1/templates?type=user")
        assert response.status_code == 200

        data = response.json()
        assert all(t["type"] == "user" for t in data["templates"])

    def test_list_templates_invalid_category(self, client):
        """Test that invalid category returns error."""
        response = client.get("/api/v1/templates?category=invalid_category")
        assert response.status_code == 422


class TestCreateTemplate:
    """Tests for creating templates."""

    def test_create_template(self, client, screen):
        """Test creating a template from a screen."""
        response = client.post(
            "/api/v1/templates",
            json={
                "screen_id": screen["screen_id"],
                "name": "My Template",
                "description": "Template description",
                "category": "restaurant",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "My Template"
        assert data["description"] == "Template description"
        assert data["category"] == "restaurant"
        assert data["type"] == "user"
        assert "id" in data
        assert "configuration" in data
        assert "thumbnail_url" in data

    def test_create_template_screen_not_found(self, client):
        """Test creating template with non-existent screen."""
        response = client.post(
            "/api/v1/templates",
            json={
                "screen_id": "nonexistent123",
                "name": "Test",
                "description": None,
                "category": "custom",
            },
        )
        assert response.status_code == 404

    def test_create_template_invalid_category(self, client, screen):
        """Test creating template with invalid category."""
        response = client.post(
            "/api/v1/templates",
            json={
                "screen_id": screen["screen_id"],
                "name": "Test",
                "description": None,
                "category": "invalid",
            },
        )
        assert response.status_code == 422

    def test_create_template_missing_required_fields(self, client, screen):
        """Test creating template without required fields."""
        response = client.post(
            "/api/v1/templates",
            json={
                "screen_id": screen["screen_id"],
                # Missing name and category
            },
        )
        assert response.status_code == 422


class TestGetTemplate:
    """Tests for getting template details."""

    def test_get_template(self, client, template):
        """Test getting a template by ID."""
        response = client.get(f"/api/v1/templates/{template['id']}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == template["id"]
        assert data["name"] == template["name"]
        assert "configuration" in data

    def test_get_template_not_found(self, client):
        """Test getting non-existent template."""
        response = client.get("/api/v1/templates/tmpl_nonexistent")
        assert response.status_code == 404

    def test_get_template_includes_configuration(self, client, template):
        """Test that template detail includes full configuration."""
        response = client.get(f"/api/v1/templates/{template['id']}")
        assert response.status_code == 200

        data = response.json()
        assert "configuration" in data
        # Configuration should have pages from the source screen
        config = data["configuration"]
        assert "pages" in config


class TestUpdateTemplate:
    """Tests for updating templates."""

    def test_update_template(self, client, template):
        """Test updating template metadata."""
        response = client.patch(
            f"/api/v1/templates/{template['id']}",
            json={
                "name": "Updated Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    def test_update_template_category(self, client, template):
        """Test updating template category."""
        response = client.patch(
            f"/api/v1/templates/{template['id']}",
            json={"category": "education"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["category"] == "education"

    def test_update_template_not_found(self, client):
        """Test updating non-existent template."""
        response = client.patch(
            "/api/v1/templates/tmpl_nonexistent",
            json={"name": "Test"},
        )
        assert response.status_code == 404

    def test_update_template_invalid_category(self, client, template):
        """Test updating template with invalid category."""
        response = client.patch(
            f"/api/v1/templates/{template['id']}",
            json={"category": "invalid"},
        )
        assert response.status_code == 422


class TestDeleteTemplate:
    """Tests for deleting templates."""

    def test_delete_template(self, client, screen):
        """Test deleting a template."""
        # Create a template to delete
        create_response = client.post(
            "/api/v1/templates",
            json={
                "screen_id": screen["screen_id"],
                "name": "To Delete",
                "description": None,
                "category": "custom",
            },
        )
        template_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/v1/templates/{template_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = client.get(f"/api/v1/templates/{template_id}")
        assert get_response.status_code == 404

    def test_delete_template_not_found(self, client):
        """Test deleting non-existent template."""
        response = client.delete("/api/v1/templates/tmpl_nonexistent")
        assert response.status_code == 404


class TestScreenCreationFromTemplate:
    """Tests for creating screens from templates."""

    def test_create_screen_from_template(self, client, template):
        """Test creating a screen using a template."""
        response = client.post(f"/api/v1/screens?template_id={template['id']}")
        assert response.status_code == 200

        data = response.json()
        assert "screen_id" in data
        assert "api_key" in data

    def test_screen_from_template_has_pages(self, client, screen):
        """Test that a screen created from template has the expected pages."""
        # First, add content to the source screen
        response = client.post(
            f"/api/v1/screens/{screen['screen_id']}/message",
            json={
                "content": [
                    {"type": "text", "value": "Test Panel 1"},
                    {"type": "text", "value": "Test Panel 2"},
                ],
                "layout": "2",
            },
            headers={"X-API-Key": screen["api_key"]},
        )
        assert response.status_code == 200

        # Create a template from this screen
        template_response = client.post(
            "/api/v1/templates",
            json={
                "screen_id": screen["screen_id"],
                "name": "Test With Content",
                "description": None,
                "category": "custom",
            },
        )
        assert template_response.status_code == 200
        template = template_response.json()

        # Create a new screen from the template
        new_screen_response = client.post(f"/api/v1/screens?template_id={template['id']}")
        assert new_screen_response.status_code == 200
        new_screen = new_screen_response.json()

        # Fetch pages for the new screen
        pages_response = client.get(
            f"/api/v1/screens/{new_screen['screen_id']}/pages",
            headers={"X-API-Key": new_screen["api_key"]},
        )
        assert pages_response.status_code == 200
        pages_data = pages_response.json()

        # Verify pages exist and have content
        assert "pages" in pages_data
        assert len(pages_data["pages"]) > 0, "New screen should have pages from template"

        # Check the first page has content
        first_page = pages_data["pages"][0]
        assert "content" in first_page
        assert len(first_page["content"]) == 2, "Page should have 2 content items"
        assert first_page["content"][0]["value"] == "Test Panel 1"
        assert first_page["content"][1]["value"] == "Test Panel 2"
        assert first_page.get("layout") == "2"

    def test_create_screen_from_nonexistent_template(self, client):
        """Test creating screen from non-existent template."""
        response = client.post("/api/v1/screens?template_id=tmpl_nonexistent")
        assert response.status_code == 404

    def test_create_screen_with_name_from_template(self, client, template):
        """Test creating a named screen from a template."""
        response = client.post(
            f"/api/v1/screens?template_id={template['id']}&name=My%20New%20Screen"
        )
        assert response.status_code == 200

        data = response.json()
        assert data.get("name") == "My New Screen"


class TestSystemTemplates:
    """Tests for system template behavior."""

    def test_seed_templates_function(self):
        """Test that seed templates are generated correctly."""
        from app.seed_templates import get_system_templates

        templates = get_system_templates()

        # Should have templates for each category
        assert len(templates) > 0
        categories = {t["category"] for t in templates}
        assert "restaurant" in categories
        assert "it_tech" in categories
        assert "small_business" in categories
        assert "education" in categories
        assert "healthcare" in categories

    def test_seed_templates_have_required_fields(self):
        """Test that seed templates have all required fields."""
        from app.seed_templates import get_system_templates

        templates = get_system_templates()

        for template in templates:
            assert "name" in template
            assert "description" in template
            assert "category" in template
            assert "configuration" in template
            assert "thumbnail_url" in template
            assert template["thumbnail_url"].startswith("data:image/svg+xml,")

    def test_seed_templates_have_valid_configurations(self):
        """Test that seed templates have valid configurations."""
        from app.seed_templates import get_system_templates

        templates = get_system_templates()

        for template in templates:
            config = template["configuration"]
            assert "pages" in config
            assert len(config["pages"]) > 0
            for page in config["pages"]:
                assert "name" in page
                assert "content" in page
