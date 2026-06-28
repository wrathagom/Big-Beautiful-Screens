"""Unit tests for the Postgres timestamp coercion used by page expires_at.

Regression: the page-write endpoints pass `expires_at` as an ISO-8601 *string*
(`request.expires_at.isoformat()`). asyncpg requires a `datetime` for the
TIMESTAMPTZ column, so binding the raw string raised and produced a 500 on
POST/PATCH /pages/{name}. The backend must coerce the string to a tz-aware
datetime before binding.
"""

from datetime import UTC, datetime

from app.db.postgres import _to_timestamptz


def test_none_returns_none():
    assert _to_timestamptz(None) is None


def test_iso_utc_string_parsed_to_aware_datetime():
    # What the endpoint actually sends: request.expires_at.isoformat() for a UTC value.
    dt = _to_timestamptz("2026-06-28T02:16:42.987000+00:00")
    assert isinstance(dt, datetime)
    assert dt.tzinfo is not None
    assert dt == datetime(2026, 6, 28, 2, 16, 42, 987000, tzinfo=UTC)


def test_naive_iso_string_assumed_utc():
    dt = _to_timestamptz("2026-06-28T03:00:00")
    assert dt.tzinfo is not None
    assert dt == datetime(2026, 6, 28, 3, 0, 0, tzinfo=UTC)


def test_existing_datetime_made_aware():
    dt = _to_timestamptz(datetime(2026, 6, 28, 3, 0, 0))
    assert dt.tzinfo is not None
    assert dt == datetime(2026, 6, 28, 3, 0, 0, tzinfo=UTC)


def test_aware_datetime_passthrough():
    aware = datetime(2026, 6, 28, 3, 0, 0, tzinfo=UTC)
    assert _to_timestamptz(aware) == aware
