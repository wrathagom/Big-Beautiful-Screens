# Testing

Big Beautiful Screens includes a comprehensive test suite using pytest.

## Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_screens.py -v

# Run specific test class
pytest tests/test_screens.py::TestWidgets -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Test Structure

```
tests/
├── test_screens.py      # API and integration tests
└── test_onboarding.py   # Onboarding/demo screen tests
```

## Test Categories

### Screen Tests

```python
class TestScreenCreation:
    """Tests for screen creation."""

class TestMessages:
    """Tests for sending messages to screens."""

class TestScreenManagement:
    """Tests for screen management endpoints."""

class TestScreenViewer:
    """Tests for the screen viewer page."""
```

### Page Tests

```python
class TestPages:
    """Tests for multi-page functionality."""

class TestRotation:
    """Tests for rotation and display settings."""
```

### Widget Tests

```python
class TestWidgets:
    """Tests for widget content types."""

    def test_send_clock_widget_digital(self, client, screen):
        """Test sending a digital clock widget."""

    def test_send_clock_widget_analog(self, client, screen):
        """Test sending an analog clock widget."""

    def test_send_clock_widget_with_timezone(self, client, screen):
        """Test sending a clock widget with timezone."""
```

### Theme Tests

```python
class TestThemes:
    """Tests for theme functionality."""
```

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
