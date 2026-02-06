## Tests

Automated tests organized into two buckets: **core** (self-hosted) and **saas**.

### Key areas
- `tests/core/unit/`: Self-hosted unit tests.
- `tests/core/e2e/`: Self-hosted Playwright E2E tests.
- `tests/saas/unit/`: SaaS unit tests (webhooks, multitenancy).
- `tests/saas/e2e/`: SaaS Playwright E2E tests (against deployed env).
- `tests/saas/saas_utils.py`: Clerk mocks and test helpers.
- `tests/saas/fixtures/`: Webhook payload fixtures.

### Tips
- E2E uses Playwright; ensure the local server fixture is running.
- Keep new tests aligned with existing fixtures in `tests/conftest.py`.
- Run `pytest tests/core` for all self-hosted tests, `pytest tests/saas` for SaaS tests.

