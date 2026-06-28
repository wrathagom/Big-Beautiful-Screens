# `show_now` Parameter — Design Spec

**Date:** 2026-06-27
**Branch:** `feature/show-now-param`
**Status:** Approved

## Problem

When a page is submitted to a screen, it only renders immediately if the screen
is already displaying that page (matched by name). A new or non-current page is
added to the rotation and won't appear until the carousel reaches it. There is no
way to make a submitted page jump to the front and display right away — useful for
alerts, "now serving" updates, or any time-sensitive content.

## Goal

Add an opt-in `show_now` request flag that makes the submitted page jump to the
front and render immediately on all connected viewers, interrupting rotation.

## Non-goals

Persisting `show_now` on the page; a dedicated "alert" page type; priority
ordering; honoring transitions for the jump (the jump is an instant swap).

## Design

`show_now` is a **transient request-time flag**. It is never written to the
database — it only changes what connected viewers do when they receive the
existing `page_update` broadcast.

### 1. Models (`app/models.py`)

Add `show_now: bool = False` to:

- `MessageRequest` (the `POST /api/v1/screens/{id}/message` body)
- `PageRequest` (the `POST /api/v1/screens/{id}/pages/{name}` body)
- `PageUpdateRequest` (the `PATCH /api/v1/screens/{id}/pages/{name}` body)

### 2. Endpoints (`app/routes/screens.py`)

In `send_message`, `create_or_update_page`, and `patch_page`: after upserting the
page, include the flag in the broadcast:

```python
{"type": "page_update", "page": page_data, "show_now": request.show_now}
```

The flag is NOT added to `message_payload` / the upsert call, so it never
persists. A `GET` of the page returns no `show_now` field.

### 3. Viewer (`static/screen.js`)

- `ws.onmessage` `page_update` case calls `handlePageUpdate(data.page, data.show_now)`.
- `handlePageUpdate(page, showNow = false)`: after upserting `page` into the
  `pages` array, if `showNow` is true, find the page's index in the active
  (non-expired) pages, set `currentPageIndex` to it, call `renderCurrentPage()`
  (instant — no transition), and restart the rotation timer so the jumped-to page
  gets its full duration before advancing.
- When `showNow` is false/absent, behavior is unchanged (re-render only if the
  updated page is the one currently on screen).

### Edge cases

- Target page not in active pages (e.g. already expired) → no-op jump; falls back
  to default behavior.
- Works for both brand-new pages and updates to existing pages.
- Rotation timer resets on jump so the page isn't cut short.

## Testing (e2e, `tests/core/e2e`)

1. **Jumps on show_now:** multi-page screen, rotation on with a long interval.
   Submit a non-current page with `show_now=true` → viewer displays it well before
   the rotation interval elapses.
2. **No jump without show_now:** same setup, `show_now` omitted → viewer stays on
   the current page (does not jump to the updated page).

## Tradeoff

Instant swap ignores configured transitions for the jump. Acceptable: `show_now`
is an interrupt, and immediacy is the point.
