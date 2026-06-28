"""E2E tests for the show_now parameter and the responsive connection toast."""

import httpx
import pytest
from playwright.sync_api import Page, expect


def _create_screen(app_server: str) -> dict:
    with httpx.Client() as client:
        response = client.post(f"{app_server}/api/v1/screens")
        assert response.status_code == 200
        return response.json()


def _set_rotation(app_server: str, screen_id: str, api_key: str, enabled: bool, interval: int):
    with httpx.Client() as client:
        response = client.patch(
            f"{app_server}/api/v1/screens/{screen_id}",
            headers={"X-API-Key": api_key},
            json={"rotation_enabled": enabled, "rotation_interval": interval},
        )
        assert response.status_code == 200


def _put_page(
    app_server: str,
    screen_id: str,
    api_key: str,
    name: str,
    content: list,
    show_now: bool | None = None,
):
    body: dict = {"content": content}
    if show_now is not None:
        body["show_now"] = show_now
    with httpx.Client() as client:
        response = client.post(
            f"{app_server}/api/v1/screens/{screen_id}/pages/{name}",
            headers={"X-API-Key": api_key},
            json=body,
        )
        assert response.status_code == 200


class TestShowNow:
    """The show_now flag makes a submitted page display immediately."""

    @pytest.fixture
    def screen(self, app_server: str) -> dict:
        return _create_screen(app_server)

    def test_show_now_jumps_to_page_immediately(self, page: Page, app_server: str, screen: dict):
        sid, key = screen["screen_id"], screen["api_key"]
        _set_rotation(app_server, sid, key, True, 3600)
        _put_page(app_server, sid, key, "alpha", ["ALPHA PAGE"])

        page.goto(f"{app_server}/screen/{sid}")
        expect(page.locator("text=ALPHA PAGE")).to_be_visible()
        # Let the WebSocket settle so the next broadcast arrives live.
        page.wait_for_timeout(500)

        # A new, non-current page should only surface via show_now.
        _put_page(app_server, sid, key, "beta", ["BETA PAGE"], show_now=True)

        expect(page.locator("text=BETA PAGE")).to_be_visible()

    def test_without_show_now_does_not_jump(self, page: Page, app_server: str, screen: dict):
        sid, key = screen["screen_id"], screen["api_key"]
        _set_rotation(app_server, sid, key, True, 3600)
        _put_page(app_server, sid, key, "alpha", ["ALPHA PAGE"])

        page.goto(f"{app_server}/screen/{sid}")
        expect(page.locator("text=ALPHA PAGE")).to_be_visible()
        page.wait_for_timeout(500)

        # Submit a new page without show_now — the view must not jump to it.
        _put_page(app_server, sid, key, "gamma", ["GAMMA PAGE"])

        page.wait_for_timeout(1000)
        expect(page.locator("text=ALPHA PAGE")).to_be_visible()
        expect(page.locator("text=GAMMA PAGE")).to_have_count(0)


class TestResponsiveToast:
    """The connection toast scales down on small viewports."""

    @pytest.fixture
    def screen(self, app_server: str) -> dict:
        return _create_screen(app_server)

    def test_toast_scales_down_on_small_viewport(self, page: Page, app_server: str, screen: dict):
        sid = screen["screen_id"]

        def toast_font_px() -> float:
            return page.evaluate(
                "() => parseFloat(getComputedStyle("
                "document.getElementById('connection-status')).fontSize)"
            )

        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(f"{app_server}/screen/{sid}")
        expect(page.locator("#connection-status")).to_be_attached()
        large = toast_font_px()

        page.set_viewport_size({"width": 360, "height": 640})
        small = toast_font_px()

        assert large == pytest.approx(24, abs=1)  # clamp max == 1.5rem
        assert small < large
        assert small <= 14
