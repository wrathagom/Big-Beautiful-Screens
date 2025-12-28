"""Rate limiting configuration using slowapi."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Disable rate limiting during tests
_testing = os.environ.get("TESTING", "").lower() in ("1", "true", "yes")

# Create limiter instance - uses client IP by default
limiter = Limiter(key_func=get_remote_address, enabled=not _testing)

# Rate limit constants
RATE_LIMIT_UPLOADS = "10/minute"  # File uploads are expensive
RATE_LIMIT_CREATE = "20/minute"  # Creating resources
RATE_LIMIT_MUTATE = "60/minute"  # Updates/deletes
RATE_LIMIT_READ = "200/minute"  # Reading data
RATE_LIMIT_AUTH = "10/minute"  # Auth-related endpoints (prevent brute force)
