"""Tests for the RSS proxy endpoint."""

import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.routes.proxy import is_private_ip, is_safe_url, parse_feed


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Set up a temporary database for testing."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"

    yield

    # Clean up
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(setup_test_db):
    """Create a test client."""
    from app.main import app

    return TestClient(app)


class TestIsPrivateIp:
    """Tests for is_private_ip function."""

    def test_private_ip_ranges(self):
        """Test that private IP ranges are detected."""
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("192.168.1.1") is True

    def test_loopback(self):
        """Test that loopback addresses are detected."""
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("127.0.0.2") is True

    def test_link_local(self):
        """Test that link-local addresses are detected."""
        assert is_private_ip("169.254.1.1") is True

    def test_cloud_metadata(self):
        """Test that cloud metadata endpoint is blocked."""
        assert is_private_ip("169.254.169.254") is True

    def test_public_ips(self):
        """Test that public IPs are allowed."""
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("1.1.1.1") is False
        assert is_private_ip("93.184.216.34") is False

    def test_invalid_ip(self):
        """Test that invalid IPs return False."""
        assert is_private_ip("not-an-ip") is False
        assert is_private_ip("") is False


class TestIsSafeUrl:
    """Tests for is_safe_url function."""

    def test_invalid_scheme(self):
        """Test that non-http(s) schemes are rejected."""
        is_safe, error = is_safe_url("ftp://example.com/feed.xml")
        assert is_safe is False
        assert "http or https" in error

        is_safe, error = is_safe_url("file:///etc/passwd")
        assert is_safe is False

    def test_blocked_hostnames(self):
        """Test that blocked hostnames are rejected."""
        is_safe, error = is_safe_url("http://localhost/feed.xml")
        assert is_safe is False
        assert "not allowed" in error

        is_safe, error = is_safe_url("http://metadata.google.internal/")
        assert is_safe is False

    @patch("socket.getaddrinfo")
    def test_private_ip_resolution(self, mock_getaddrinfo):
        """Test that hostnames resolving to private IPs are rejected."""
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("192.168.1.1", 80))]
        is_safe, error = is_safe_url("http://internal.example.com/feed.xml")
        assert is_safe is False
        assert "private/internal" in error

    @patch("socket.getaddrinfo")
    def test_public_url(self, mock_getaddrinfo):
        """Test that public URLs are allowed."""
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 80))]
        is_safe, error = is_safe_url("https://example.com/feed.xml")
        assert is_safe is True
        assert error == ""

    @patch("socket.getaddrinfo")
    def test_dns_failure(self, mock_getaddrinfo):
        """Test that DNS resolution failures are handled."""
        import socket

        mock_getaddrinfo.side_effect = socket.gaierror("DNS failed")
        is_safe, error = is_safe_url("http://nonexistent.example.com/feed.xml")
        assert is_safe is False
        assert "resolve hostname" in error


class TestParseFeed:
    """Tests for feed parsing functions."""

    def test_parse_rss_basic(self):
        """Test parsing a basic RSS feed."""
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <description>A test feed</description>
                <link>https://example.com</link>
                <item>
                    <title>Test Item 1</title>
                    <description>Description 1</description>
                    <link>https://example.com/1</link>
                    <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""
        result = parse_feed(xml)
        assert result["title"] == "Test Feed"
        assert result["description"] == "A test feed"
        assert len(result["items"]) == 1
        assert result["items"][0]["title"] == "Test Item 1"

    def test_parse_atom_basic(self):
        """Test parsing a basic Atom feed."""
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Test Atom Feed</title>
            <subtitle>A test atom feed</subtitle>
            <link href="https://example.com" rel="alternate"/>
            <entry>
                <title>Atom Entry 1</title>
                <summary>Summary 1</summary>
                <link href="https://example.com/1" rel="alternate"/>
                <published>2024-01-01T00:00:00Z</published>
                <id>entry-1</id>
            </entry>
        </feed>"""
        result = parse_feed(xml)
        assert result["title"] == "Test Atom Feed"
        assert len(result["items"]) == 1
        assert result["items"][0]["title"] == "Atom Entry 1"

    def test_parse_rss_with_enclosure_image(self):
        """Test extracting image from RSS enclosure."""
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <item>
                    <title>Item with Image</title>
                    <enclosure url="https://example.com/image.jpg" type="image/jpeg"/>
                </item>
            </channel>
        </rss>"""
        result = parse_feed(xml)
        assert result["items"][0]["image"] == "https://example.com/image.jpg"

    def test_parse_rss_with_media_content(self):
        """Test extracting image from media:content."""
        xml = """<?xml version="1.0"?>
        <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
            <channel>
                <title>Test Feed</title>
                <item>
                    <title>Item with Media</title>
                    <media:content url="https://example.com/media.jpg" type="image/jpeg"/>
                </item>
            </channel>
        </rss>"""
        result = parse_feed(xml)
        assert result["items"][0]["image"] == "https://example.com/media.jpg"

    def test_parse_rss_image_from_description(self):
        """Test extracting image from description HTML."""
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <item>
                    <title>Item with HTML</title>
                    <description>&lt;p&gt;Text&lt;/p&gt;&lt;img src="https://example.com/desc.jpg"/&gt;</description>
                </item>
            </channel>
        </rss>"""
        result = parse_feed(xml)
        assert result["items"][0]["image"] == "https://example.com/desc.jpg"

    def test_unknown_feed_format(self):
        """Test that unknown formats raise an error."""
        xml = """<?xml version="1.0"?><unknown><data/></unknown>"""
        with pytest.raises(ValueError, match="Unknown feed format"):
            parse_feed(xml)


class TestProxyEndpoint:
    """Integration tests for the proxy endpoint."""

    def test_ssrf_localhost(self, client):
        """Test SSRF protection blocks localhost."""
        response = client.get("/api/v1/proxy/rss?url=http://localhost/feed.xml")
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    def test_ssrf_private_ip(self, client):
        """Test SSRF protection blocks private IPs."""
        response = client.get("/api/v1/proxy/rss?url=http://192.168.1.1/feed.xml")
        assert response.status_code == 400
        assert (
            "private" in response.json()["detail"].lower()
            or "resolve" in response.json()["detail"].lower()
        )

    def test_ssrf_127_ip(self, client):
        """Test SSRF protection blocks 127.x.x.x IPs."""
        response = client.get("/api/v1/proxy/rss?url=http://127.0.0.1/feed.xml")
        assert response.status_code == 400

    def test_ssrf_metadata_endpoint(self, client):
        """Test SSRF protection blocks cloud metadata endpoints."""
        response = client.get("/api/v1/proxy/rss?url=http://metadata.google.internal/")
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    def test_invalid_scheme(self, client):
        """Test that non-http(s) schemes are rejected."""
        response = client.get("/api/v1/proxy/rss?url=ftp://example.com/feed.xml")
        assert response.status_code == 400
        assert "http or https" in response.json()["detail"].lower()

    def test_missing_url_param(self, client):
        """Test that missing URL parameter returns error."""
        response = client.get("/api/v1/proxy/rss")
        assert response.status_code == 422  # Validation error
