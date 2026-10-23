"""Tests for operator notifications sent through Resend."""

import json
from unittest.mock import patch

import httpx
import pytest

from app.config import get_settings
from app.notifications import RESEND_API_URL, send_signup_notification


@pytest.fixture
def resend_env(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("SIGNUP_NOTIFY_EMAIL", "owner@example.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def captured_requests():
    """Route the notifier's httpx client through a mock transport."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "email_123"})

    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    with patch("app.notifications.httpx.AsyncClient", side_effect=client_factory):
        yield requests


async def test_signup_notification_posts_to_resend(resend_env, captured_requests):
    await send_signup_notification(email="new@example.com", name="New User", user_id="user_1")

    assert len(captured_requests) == 1
    request = captured_requests[0]
    assert str(request.url) == RESEND_API_URL
    assert request.headers["Authorization"] == "Bearer re_test_key"
    body = json.loads(request.content)
    assert body["to"] == ["owner@example.com"]
    assert "new@example.com" in body["subject"]
    assert "user_1" in body["text"]


async def test_signup_notification_skipped_without_api_key(
    monkeypatch, resend_env, captured_requests
):
    monkeypatch.delenv("RESEND_API_KEY")
    get_settings.cache_clear()

    await send_signup_notification(email="new@example.com", name=None, user_id="user_1")

    assert captured_requests == []


async def test_signup_notification_raises_on_resend_error(resend_env):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "invalid from"})

    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    with (
        patch("app.notifications.httpx.AsyncClient", side_effect=client_factory),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await send_signup_notification(email="new@example.com", name=None, user_id="user_1")
