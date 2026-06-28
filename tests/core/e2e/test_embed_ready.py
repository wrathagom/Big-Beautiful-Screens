"""E2E test for the `bbs-screen-ready` postMessage signal used by iframe embeds.

When the screen viewer finishes rendering its first content, it must notify an
embedding parent window via `postMessage({type: 'bbs-screen-ready'}, '*')` so the
host page (e.g. the marketing site) can reveal the iframe / hide a loader.

When the screen is not framed, `window.parent === window`, so the message is
delivered to the page's own window and can be observed there.
"""

import httpx
import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="module")
def demo_screen_id(app_server: str):
    """Find the auto-created demo screen ID."""
    with httpx.Client() as client:
        response = client.get(f"{app_server}/api/v1/screens", params={"per_page": 100})
        assert response.status_code == 200
        screens = response.json().get("screens", [])
        for screen in screens:
            if screen.get("name") == "Welcome Demo":
                return screen["screen_id"]
        pytest.skip("Demo screen not found - test requires fresh database")


def test_screen_posts_ready_message_once_rendered(page: Page, app_server: str, demo_screen_id: str):
    """The screen page posts `bbs-screen-ready` to its parent once content renders."""
    # Record any messages posted to this window (parent === self when not framed).
    page.add_init_script(
        """
        window.__bbsMessages = [];
        window.addEventListener('message', (event) => {
            window.__bbsMessages.push(event.data);
        });
        """
    )

    page.goto(f"{app_server}/screen/{demo_screen_id}")

    # The signal fires after WebSocket sync + first render, so wait for it.
    page.wait_for_function(
        "() => (window.__bbsMessages || []).some((m) => m && m.type === 'bbs-screen-ready')"
    )

    messages = page.evaluate("() => window.__bbsMessages")
    ready_messages = [m for m in messages if m and m.get("type") == "bbs-screen-ready"]
    assert (
        len(ready_messages) == 1
    ), f"expected exactly one bbs-screen-ready message, got {ready_messages!r}"
