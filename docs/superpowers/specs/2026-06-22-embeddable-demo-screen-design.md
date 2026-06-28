# Embeddable Demo Screen — Design Spec

**Date:** 2026-06-22
**Branch:** `feature/embeddable-demo-screen`
**Status:** Approved

## Problem

The marketing website needs to embed a live BBS demo screen via `<iframe>`. Today every screen is unframeable from other origins:

- `app/main.py:63` — global middleware sets `X-Frame-Options: SAMEORIGIN` on all responses.
- `app/routes/screens.py:55-66, 880` — the `/screen/{id}` viewer attaches `SCREEN_CSP` ending in `frame-ancestors 'none'`.

`X-Frame-Options` cannot express a multi-origin allowlist, and `SAMEORIGIN` keeps blocking cross-origin frames even if the CSP is relaxed. Modern browsers honor CSP `frame-ancestors` and ignore XFO when both are present — but the safe approach is to omit XFO entirely on the embeddable response so there is no conflict.

## Goal

Allow a specific, configured demo screen to be framed from an allowlist of marketing origins. Every other screen — and all self-hosted installs by default — stays locked to `frame-ancestors 'none'`. No database schema change.

## Non-goals

Per-screen `embeddable` flag, admin UI, customer-facing embedding, a dedicated `/embed/{id}` route. Demo-only, config-driven.

## Design

### 1. Config (`app/config.py` `Settings`)

Two new env-var settings, both raw strings (avoids pydantic JSON-list parsing), with parsed accessors:

- `EMBED_ALLOWED_ORIGINS: str = ""` — space/comma-separated parent origins allowed to frame.
- `EMBED_SCREEN_IDS: str = ""` — comma-separated screen IDs permitted to be framed.
- `embed_allowed_origins -> list[str]` and `embed_screen_ids -> set[str]` properties parse/normalize (split on whitespace+comma, strip, drop empties).

**Both empty/unset → feature off.** This is the default for self-hosted and for any environment that hasn't opted in — behavior identical to today.

### 2. CSP builder (`app/routes/screens.py`)

Replace the `SCREEN_CSP` constant with `build_screen_csp(frame_ancestors: str = "'none'") -> str` returning the same policy string with the given `frame-ancestors` value. Default call reproduces today's policy exactly.

### 3. `view_screen` logic

Add `request: Request` to the signature. After loading the screen:

```
settings = get_settings()
is_embeddable = screen_id in settings.embed_screen_ids and bool(settings.embed_allowed_origins)
if is_embeddable:
    frame_ancestors = " ".join(settings.embed_allowed_origins)
    request.state.allow_embed = True
else:
    frame_ancestors = "'none'"
response.headers["Content-Security-Policy"] = build_screen_csp(frame_ancestors)
```

`frame-ancestors` with multiple origins is space-separated.

### 4. Middleware drops XFO for embeddable responses (`app/main.py`)

The middleware runs *after* the route handler, so deleting XFO in the route would be re-added by `setdefault`. Instead, gate it:

```
if not getattr(request.state, "allow_embed", False):
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
```

Embeddable responses therefore carry no `X-Frame-Options` header. Modern browsers enforce `frame-ancestors`; legacy XFO-only browsers fail safe (block).

## Testing (`tests/core/unit`, hermetic)

1. **Default screen** → CSP contains `frame-ancestors 'none'` **and** header `X-Frame-Options: SAMEORIGIN`.
2. **Configured embeddable screen** (env set, screen ID in allowlist) → CSP contains the configured origins, contains no `'none'` for frame-ancestors, and response has **no** `X-Frame-Options` header.
3. **Non-configured screen while allowlist set** → still `frame-ancestors 'none'` + XFO present.
4. **Empty config** → everything locked (feature off).

Tests clear the `get_settings` lru_cache and set env vars (matching existing unit-test conventions).

## Rollout (Railway env vars, post-merge)

Set per environment via Railway MCP using each environment's real demo-screen ID:

- **dev**: `EMBED_ALLOWED_ORIGINS` = `https://bigbeautifulscreens.com https://www.bigbeautifulscreens.com https://dev.big-beautiful-screens-web.pages.dev`; `EMBED_SCREEN_IDS` = dev demo screen ID.
- **prod**: `EMBED_ALLOWED_ORIGINS` = `https://bigbeautifulscreens.com https://www.bigbeautifulscreens.com` (add the pages.dev preview only if the preview marketing site frames the prod backend); `EMBED_SCREEN_IDS` = prod demo screen ID.

## Tradeoff

Gating by screen ID means if the demo screen is recreated (new ID), `EMBED_SCREEN_IDS` must be updated. Acceptable for a stable public demo.
