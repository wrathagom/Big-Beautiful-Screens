# Contributing

Thank you for your interest in contributing to Big Beautiful Screens!

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Big-Beautiful-Screens.git
   cd Big-Beautiful-Screens
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers (required for E2E tests):
   ```bash
   playwright install chromium
   ```

5. Install pre-commit hooks:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

6. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Code Style

- Python code follows PEP 8
- Use type hints where possible
- Format code with `black`
- Sort imports with `isort`

Pre-commit hooks handle formatting automatically.

## Running Tests

```bash
# Unit tests (fast, no browser needed)
pytest tests/core/unit -v

# E2E tests (requires playwright install chromium)
pytest tests/core/e2e -v

# All core tests
pytest tests/core -v
```

All core tests must pass before merging.

## Pull Request Process

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "Add your feature"
   ```

3. Push and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Fill out the PR template with:
   - Summary of changes
   - Test plan
   - Screenshots (if UI changes)

## Merge Strategy

- Keep PR branches up to date by rebasing onto `main` before merge.
- Resolve conflicts locally and ensure required tests/CI pass after the rebase.
- Merge using **Rebase and merge** (linear history; no merge commits).

## Adding a New Widget

Widgets are modular and easy to add:

1. Create `static/widgets/yourwidget.js`:
   ```javascript
   import { registerWidget } from './registry.js';

   const YourWidget = {
       name: 'yourwidget',
       version: '1.0.0',
       configSchema: {
           option1: { default: 'value' },
       },
       create(container, config) {
           const el = document.createElement('div');
           el.className = 'widget-yourwidget';
           // ... widget logic
           return el;
       },
       destroy(element) {
           // Clean up timers, event listeners, etc.
       }
   };

   registerWidget('yourwidget', YourWidget);
   ```

2. Import in `static/screen.js`:
   ```javascript
   import './widgets/yourwidget.js';
   ```

3. Add tests in `tests/core/unit/test_screens.py`:
   ```python
   def test_send_yourwidget(self, client, screen):
       response = client.post(
           f"/api/v1/screens/{screen['screen_id']}/message",
           headers={"X-API-Key": screen["api_key"]},
           json={"content": [
               {"type": "widget", "widget_type": "yourwidget"}
           ]},
       )
       assert response.status_code == 200
   ```

4. Document in `docs/content/widgets.md`

## Project Structure

```
big-beautiful-screens/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── database.py          # Database operations
│   ├── config.py            # Configuration
│   ├── utils.py             # Utilities
│   └── routes/              # API routes
├── static/
│   ├── screen.js            # Client-side rendering
│   ├── screen.css           # Screen styling
│   ├── admin.css            # Admin styling
│   └── widgets/             # Widget modules
├── tests/
│   ├── core/                  # Self-hosted tests (unit + e2e)
│   └── saas/                  # SaaS-specific tests
├── docs/                    # Documentation
└── mkdocs.yml               # Docs configuration
```

## License

By contributing, you agree that your contributions will be licensed under the project's [PolyForm Noncommercial 1.0.0](../../LICENSE) license.
