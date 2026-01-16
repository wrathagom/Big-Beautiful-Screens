## Tests

Automated tests (unit, integration, and E2E).

### Key areas
- `tests/e2e/`: Playwright-based E2E tests.
- `tests/integration/`: API and integration coverage.
- `tests/saas_utils.py`: Clerk mocks and test helpers.

### Tips
- E2E uses Playwright; ensure the local server fixture is running.
- Keep new tests aligned with existing fixtures in `tests/conftest.py`.

