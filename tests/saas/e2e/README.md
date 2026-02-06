# SaaS E2E Tests

End-to-end tests for the SaaS deployment of Big Beautiful Screens, testing real Clerk authentication and Stripe billing flows.

## Prerequisites

1. **Deployed dev environment** on Railway (or similar)
2. **Test user** created in Clerk (test mode) with email/password authentication
3. **Stripe test mode** configured with webhook endpoint

## Setup

### 1. Create a Test User in Clerk

1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
2. Make sure you're in **Development** mode (not Production)
3. Go to **Users** → **Create user**
4. Create a user with:
   - Email: `e2e-test@yourdomain.com` (or any email you control)
   - Password: A secure password
5. Note these credentials for the environment variables

### 2. Environment Variables

Create a `.env.e2e` file (don't commit this!) or set these in your shell:

```bash
export E2E_BASE_URL="https://your-dev-app.up.railway.app"
export E2E_TEST_EMAIL="e2e-test@yourdomain.com"
export E2E_TEST_PASSWORD="your-test-password"
```

### 3. Install Playwright

```bash
pip install pytest-playwright
playwright install chromium
```

## Running Tests

### Run all SaaS E2E tests

```bash
# Load environment variables
source .env.e2e

# Run tests
pytest tests/saas/e2e -v
```

### Run specific test files

```bash
# Auth tests only
pytest tests/saas/e2e/test_auth_flows.py -v

# Admin dashboard tests
pytest tests/saas/e2e/test_admin_dashboard.py -v

# Billing/Stripe tests
pytest tests/saas/e2e/test_billing.py -v
```

### Run with visible browser (debugging)

```bash
pytest tests/saas/e2e -v --headed
```

### Run with slow motion (easier to watch)

```bash
pytest tests/saas/e2e -v --headed --slowmo=500
```

## Test Categories

### Authentication Tests (`test_auth_flows.py`)
- Sign-in flow with valid credentials
- Sign-in with invalid credentials (error handling)
- Sign-out clears session
- Protected routes redirect to sign-in

### Admin Dashboard Tests (`test_admin_dashboard.py`)
- Screens page loads and shows screen list
- Create new screen flow
- Navigation between admin pages
- Usage page shows plan info
- Pricing page loads

### Billing Tests (`test_billing.py`)
- Upgrade button redirects to Stripe Checkout
- Stripe Checkout displays correctly
- Complete checkout with test card (4242 4242 4242 4242)
- Cancel checkout returns to app
- Manage billing opens Stripe portal

## Stripe Test Cards

For billing tests, use these [Stripe test cards](https://stripe.com/docs/testing):

| Card Number | Description |
|-------------|-------------|
| `4242424242424242` | Succeeds |
| `4000000000000002` | Declined |
| `4000002500003155` | Requires 3D Secure |

Use any future expiry date and any 3-digit CVC.

## CI/CD Integration

These tests are designed to run in GitHub Actions against a deployed dev environment. See `.github/workflows/e2e-saas.yml` for the workflow configuration.

Required GitHub Secrets:
- `E2E_BASE_URL`
- `E2E_TEST_EMAIL`
- `E2E_TEST_PASSWORD`

## Troubleshooting

### Tests fail with "Environment variable not set"
Make sure you've exported all required environment variables.

### Clerk sign-in form not found
The Clerk UI selectors may have changed. Update the selectors in `conftest.py`.

### Stripe checkout not loading
- Check that your dev environment has valid Stripe test keys
- Verify the Stripe pricing table ID is correct

### Tests timeout
Increase timeouts in `conftest.py` or use `--timeout=60` flag.
