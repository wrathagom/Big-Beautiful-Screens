"""E2E test configuration for Playwright tests."""

import asyncio
import os
import socket
import tempfile
import threading
import time
from contextlib import closing
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import Page


def mock_javascript_time(page: Page, fixed_time: str = "2025-01-15T14:30:45Z"):
    """Mock Date in JavaScript for deterministic clock/countdown screenshots.

    Call this BEFORE navigating to a page with time-dependent widgets.
    The time will show as 2:30:45 PM (or 14:30:45 in 24h format).
    """
    page.add_init_script(f"""
        const mockDate = new Date('{fixed_time}');
        const OriginalDate = Date;
        window.Date = class extends OriginalDate {{
            constructor(...args) {{
                if (args.length === 0) return new OriginalDate(mockDate);
                return new OriginalDate(...args);
            }}
            static now() {{ return mockDate.getTime(); }}
        }};
    """)


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--record-video",
        action="store_true",
        default=False,
        help="Record videos of test runs",
    )


def find_free_port():
    """Find an available port on localhost."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class ServerThread(threading.Thread):
    """Run uvicorn server in a separate thread."""

    def __init__(self, app, host: str, port: int):
        super().__init__(daemon=True)
        self.app = app
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


@pytest.fixture(scope="session")
def app_server():
    """Start the FastAPI server for E2E tests."""
    # Create a temporary database for tests
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = str(Path(tmpdir) / "e2e_test.db")
        os.environ["SQLITE_PATH"] = test_db_path
        os.environ["TESTING"] = "1"

        # Clear cached settings
        from app.config import get_settings

        get_settings.cache_clear()

        # Reset database singleton
        from app.db.factory import reset_database

        reset_database()

        # Initialize the database
        import app.database as db_module
        from app.main import app

        # Handle case where event loop may or may not be running
        try:
            asyncio.get_running_loop()
            # If we're in a running loop, run in a separate thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(asyncio.run, db_module.init_db()).result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            asyncio.run(db_module.init_db())

        # Find a free port and start server
        port = find_free_port()
        server_thread = ServerThread(app, "127.0.0.1", port)
        server_thread.start()

        # Wait for server to be ready and demo screen to be created
        base_url = f"http://127.0.0.1:{port}"
        for _ in range(50):  # Wait up to 5 seconds
            try:
                import httpx

                with httpx.Client() as client:
                    response = client.get(f"{base_url}/admin/screens")
                    if response.status_code == 200:
                        # Also check that startup event completed (demo screen exists)
                        api_response = client.get(f"{base_url}/api/v1/screens")
                        if api_response.status_code == 200:
                            screens = api_response.json().get("screens", [])
                            if any(s.get("name") == "Welcome Demo" for s in screens):
                                break
            except Exception:
                pass
            time.sleep(0.1)

        yield base_url

        # Cleanup
        server_thread.stop()
        reset_database()
        get_settings.cache_clear()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for tests (non-video settings)."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture
def page(browser, browser_context_args, app_server, request):
    """Provide a page with video recording support."""
    context_args = {**browser_context_args}

    if request.config.getoption("--record-video"):
        videos_dir = Path(__file__).parent / "videos"
        videos_dir.mkdir(exist_ok=True)
        context_args["record_video_dir"] = str(videos_dir)
        context_args["record_video_size"] = {"width": 1280, "height": 720}

    # Grant clipboard permissions for copy button tests
    context_args["permissions"] = ["clipboard-read", "clipboard-write"]

    context = browser.new_context(**context_args)
    page = context.new_page()
    page.set_default_timeout(10000)  # 10 second timeout

    yield page

    page.close()
    context.close()  # This triggers video save


@pytest.fixture
def assert_snapshot(request):
    """Fixture for visual snapshot comparison.

    Usage:
        def test_example(page, assert_snapshot):
            assert_snapshot(page.screenshot(), "test_name.png")
    """
    screenshots_dir = Path(__file__).parent / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    def _assert_snapshot(image_bytes: bytes, name: str):
        """Compare screenshot against baseline or create new baseline."""
        baseline_path = screenshots_dir / name

        if baseline_path.exists():
            # Compare against existing baseline
            baseline_bytes = baseline_path.read_bytes()
            if image_bytes != baseline_bytes:
                # Save the new screenshot for comparison
                new_path = screenshots_dir / f"new_{name}"
                new_path.write_bytes(image_bytes)
                pytest.fail(
                    f"Screenshot '{name}' differs from baseline. "
                    f"New screenshot saved to {new_path}. "
                    f"If the change is expected, replace {baseline_path} with {new_path}."
                )
        else:
            # Create new baseline
            baseline_path.write_bytes(image_bytes)
            print(f"Created new baseline screenshot: {baseline_path}")

    return _assert_snapshot
