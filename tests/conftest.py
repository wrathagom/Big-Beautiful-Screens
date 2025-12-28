"""Pytest configuration and fixtures."""

import os

# Disable rate limiting during tests - must be set before importing app
os.environ["TESTING"] = "1"
