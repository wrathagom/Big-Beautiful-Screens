# Testing

Big Beautiful Screens includes a comprehensive test suite using pytest, organized into two buckets: **core** (self-hosted) and **saas**.

## Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (includes pytest-playwright)
pip install -r requirements.txt

# Install Playwright browsers (required for E2E tests)
playwright install chromium
```

## Running Tests

```bash
# Run all core unit tests
pytest tests/core/unit -v

# Run all core tests (unit + e2e)
pytest tests/core -v

# Run core e2e tests only
pytest tests/core/e2e -v

# Run a specific test file
pytest tests/core/unit/test_screens.py -v

# Run a specific test class
pytest tests/core/unit/test_screens.py::TestWidgets -v

# Run with coverage
pytest tests/core --cov=app --cov-report=html

# Run everything (core + saas)
pytest tests/ -v
```

## Test Structure

```
tests/
├── conftest.py                  # Root config (TESTING=1)
├── core/                        # Self-hosted tests
│   ├── unit/                    # Unit tests (fast, no browser needed)
│   │   ├── test_screens.py
│   │   ├── test_templates.py
│   │   ├── test_media.py
│   │   ├── test_proxy.py
│   │   ├── test_rate_limit.py
│   │   └── test_onboarding.py
│   └── e2e/                     # Playwright E2E tests
│       ├── conftest.py
│       ├── test_admin_local.py
│       ├── test_demo_screen.py
│       ├── test_screen_features.py
│       ├── test_screen_layouts.py
│       ├── test_templates.py
│       └── screenshots/
└── saas/                        # SaaS-specific tests
    ├── saas_utils.py
    ├── fixtures/
    ├── unit/                    # SaaS unit tests (mocked)
    │   ├── test_webhooks.py
    │   └── test_multitenancy.py
    └── e2e/                     # SaaS E2E tests (deployed env)
        ├── test_admin_dashboard.py
        ├── test_auth_flows.py
        └── test_billing.py
```

## Test Categories

### Core Unit Tests

Fast tests that don't need a browser or running server:

- **test_screens.py** — Screen CRUD, messages, widgets, themes, pages, rotation
- **test_templates.py** — Template CRUD, system templates, screen creation from templates
- **test_media.py** — Media upload and serving
- **test_proxy.py** — URL proxy functionality
- **test_rate_limit.py** — Rate limiting
- **test_onboarding.py** — Demo screen and onboarding

### Core E2E Tests

Playwright browser tests against a local server (started automatically via the `app_server` fixture):

- **test_admin_local.py** — Admin dashboard interactions
- **test_demo_screen.py** — Demo screen pages and transitions
- **test_screen_features.py** — Styling, widgets, visual regression
- **test_screen_layouts.py** — Layouts and themes visual regression
- **test_templates.py** — Template gallery and management

### SaaS Tests

SaaS unit tests run with mocked dependencies. SaaS E2E tests require a deployed environment and credentials — see `tests/saas/e2e/README.md`.

## Writing Tests

### Fixtures

The test suite provides these fixtures:

```python
@pytest.fixture
def client(setup_test_db):
    """Create a test client."""
    return TestClient(setup_test_db)

@pytest.fixture
def screen(client):
    """Create a test screen and return its data."""
    response = client.post("/api/v1/screens")
    return response.json()
```

### Example Test

```python
def test_send_widget_content(self, client, screen):
    """Test sending a widget."""
    response = client.post(
        f"/api/v1/screens/{screen['screen_id']}/message",
        headers={"X-API-Key": screen["api_key"]},
        json={
            "content": [
                {
                    "type": "widget",
                    "widget_type": "clock",
                    "widget_config": {"style": "digital"}
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
```

## Test Database

Tests use an isolated SQLite database that's created fresh for each test session:

```python
@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Set up a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = str(Path(tmpdir) / "test_screens.db")
        os.environ["SQLITE_PATH"] = test_db_path
        # ... setup
        yield app
        # ... cleanup
```

## Manual Testing

For interactive testing with a running server:

```bash
# Start the server
uvicorn app.main:app --reload

# In another terminal, run manual test scripts
python test_api.py
python test_colors.py
```

## Test Coverage

Current test coverage includes:

- Screen CRUD operations
- Message sending (all content types)
- Widget content (clock digital/analog)
- Page management and rotation
- Theme application
- Authentication and authorization
- Style inheritance
- Ephemeral pages with expiration
