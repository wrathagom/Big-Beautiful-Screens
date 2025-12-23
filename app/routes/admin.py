"""Admin dashboard routes with Jinja2 template rendering."""

import base64
import contextlib
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_clerk_sign_in_url, get_current_user
from ..config import PLAN_LIMITS, AppMode, get_settings
from ..connection_manager import manager
from ..database import (
    get_all_screens,
    get_all_themes,
    get_screens_count,
    get_theme_usage_counts,
    get_themes_count,
)
from ..db import get_database

router = APIRouter(include_in_schema=False)


def _format_datetime(value: str | datetime | None) -> str:
    """Format a datetime value for display, handling both strings and datetime objects."""
    if value is None:
        return "Never"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    # String format from SQLite
    return value[:19].replace("T", " ")


# Set up Jinja2 templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=templates_path)


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root route - handles Clerk auth redirect and serves as landing page."""
    settings = get_settings()

    # In SaaS mode with Clerk auth params, render the callback page to process them
    if settings.APP_MODE == AppMode.SAAS:
        has_auth_params = request.query_params.get("__clerk_db_jwt") or request.query_params.get(
            "__clerk_handshake"
        )

        if has_auth_params:
            return templates.TemplateResponse(
                request=request,
                name="clerk_callback.html",
                context={
                    "clerk_publishable_key": settings.CLERK_PUBLISHABLE_KEY,
                    "redirect_url": "/admin/screens",
                    "sign_in_url": get_clerk_sign_in_url("/admin/screens"),
                },
            )

    # Default: redirect to admin screens
    return RedirectResponse(url="/admin/screens", status_code=302)


@router.get("/auth/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """Sign out - revoke Clerk session, clear cookies, show logged out page."""
    import httpx
    import jwt

    settings = get_settings()

    # Try to revoke the Clerk session
    session_cookie = request.cookies.get("__session")
    if session_cookie and settings.CLERK_SECRET_KEY:
        try:
            # Decode JWT to get session ID (without verification - just need the sid)
            claims = jwt.decode(session_cookie, options={"verify_signature": False})
            session_id = claims.get("sid")

            if session_id:
                # Call Clerk API to revoke the session
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.clerk.com/v1/sessions/{session_id}/revoke",
                        headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                    )
        except Exception as e:
            print(f"Failed to revoke Clerk session: {e}")

    # Create response with a simple logged-out page
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Signed Out</title>
        <style>
            body { font-family: sans-serif; background: #0f0f23; color: #ccc;
                   display: flex; align-items: center; justify-content: center;
                   min-height: 100vh; margin: 0; }
            .container { text-align: center; }
            a { color: #4a69bd; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Signed Out</h1>
            <p>You have been signed out successfully.</p>
            <p><a href="/admin/screens">Sign in again</a></p>
        </div>
    </body>
    </html>
    """
    response = HTMLResponse(content=html)

    # Clear all Clerk cookies with matching parameters
    response.delete_cookie("__session", path="/", secure=True, samesite="none")
    response.delete_cookie("__client_uat", path="/", secure=True, samesite="none")

    return response


@router.get("/auth/callback")
async def auth_callback(request: Request, redirect_url: str = "/admin/screens"):
    """Handle Clerk auth callback - parse handshake JWT and set cookies server-side."""
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        return RedirectResponse(url=redirect_url, status_code=302)

    # Handle __clerk_db_jwt - this is a database reference token that
    # needs to be processed by the Clerk SDK, not used directly as a cookie.
    # Render the callback page to let the SDK handle the token exchange.
    db_jwt = request.query_params.get("__clerk_db_jwt")
    if db_jwt:
        return templates.TemplateResponse(
            request=request,
            name="clerk_callback.html",
            context={
                "clerk_publishable_key": settings.CLERK_PUBLISHABLE_KEY,
                "redirect_url": redirect_url,
                "sign_in_url": get_clerk_sign_in_url(redirect_url),
            },
        )

    # Get the handshake JWT from query params
    handshake_jwt = request.query_params.get("__clerk_handshake")

    if handshake_jwt:
        try:
            # Decode JWT payload (we don't need to verify, just extract cookies)
            # JWT format: header.payload.signature
            parts = handshake_jwt.split(".")
            if len(parts) >= 2:
                # Add padding if needed for base64 decoding
                payload_b64 = parts[1]
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding

                payload_json = base64.urlsafe_b64decode(payload_b64)
                payload = json.loads(payload_json)

                # Extract cookie strings from handshake array
                cookie_strings = payload.get("handshake", [])

                # Create redirect response and set cookies
                response = RedirectResponse(url=redirect_url, status_code=302)

                for cookie_str in cookie_strings:
                    # Parse cookie string: "name=value; Path=/; ..."
                    parts = cookie_str.split(";")
                    if not parts:
                        continue

                    # First part is name=value
                    name_value = parts[0].strip()
                    if "=" not in name_value:
                        continue

                    name, value = name_value.split("=", 1)

                    # Parse attributes
                    path = "/"
                    max_age = None
                    secure = False
                    httponly = False
                    samesite = "lax"

                    for attr in parts[1:]:
                        attr = attr.strip().lower()
                        if attr.startswith("path="):
                            path = attr.split("=", 1)[1]
                        elif attr.startswith("max-age="):
                            with contextlib.suppress(ValueError):
                                max_age = int(attr.split("=", 1)[1])
                        elif attr == "secure":
                            secure = True
                        elif attr == "httponly":
                            httponly = True
                        elif attr.startswith("samesite="):
                            samesite = attr.split("=", 1)[1]

                    # Set the cookie on response
                    response.set_cookie(
                        key=name,
                        value=value,
                        path=path,
                        max_age=max_age,
                        secure=secure,
                        httponly=httponly,
                        samesite=samesite,
                    )

                return response

        except Exception as e:
            # Log error and fall through to redirect without cookies
            print(f"Failed to parse Clerk handshake: {e}")

    # Fallback: just redirect (user may need to sign in again)
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/admin/screens", response_class=HTMLResponse)
async def admin_screens(request: Request, page: int = 1):
    """Admin page listing all screens with pagination.

    In SaaS mode, requires authentication and shows only user's screens.
    In self-hosted mode, shows all screens without authentication.
    """
    settings = get_settings()
    user = None

    # In SaaS mode, require authentication
    if settings.APP_MODE == AppMode.SAAS:
        user = await get_current_user(request)
        if not user:
            return RedirectResponse(url=get_clerk_sign_in_url("/admin/screens"), status_code=302)

    per_page = 10
    offset = (page - 1) * per_page

    # Filter by ownership in SaaS mode
    if settings.APP_MODE == AppMode.SAAS and user:
        total_count = await get_screens_count(owner_id=user.user_id, org_id=user.org_id)
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        page = max(1, min(page, total_pages))
        screens = await get_all_screens(
            limit=per_page, offset=offset, owner_id=user.user_id, org_id=user.org_id
        )
    else:
        total_count = await get_screens_count()
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        page = max(1, min(page, total_pages))
        screens = await get_all_screens(limit=per_page, offset=offset)

    # Enrich screen data for template
    enriched_screens = []
    for screen in screens:
        enriched_screens.append(
            {
                **screen,
                "screen_url": f"/screen/{screen['id']}",
                "api_url": f"/api/v1/screens/{screen['id']}/message",
                "viewer_count": manager.get_viewer_count(screen["id"]),
                "created_display": _format_datetime(screen["created_at"]),
                "last_updated_display": _format_datetime(screen.get("last_updated")),
                "name_display": screen.get("name") or "Unnamed Screen",
                "is_unnamed": not screen.get("name"),
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_screens.html",
        context={
            "screens": enriched_screens,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "clerk_publishable_key": settings.CLERK_PUBLISHABLE_KEY
            if settings.APP_MODE == AppMode.SAAS
            else None,
            "help_url": settings.HELP_URL,
        },
    )


@router.get("/admin/themes", response_class=HTMLResponse)
async def admin_themes(request: Request, page: int = 1):
    """Admin page for managing themes with pagination.

    In SaaS mode, requires authentication and shows only accessible themes.
    In self-hosted mode, shows all themes without authentication.
    """
    settings = get_settings()
    user = None

    # In SaaS mode, require authentication
    if settings.APP_MODE == AppMode.SAAS:
        user = await get_current_user(request)
        if not user:
            return RedirectResponse(url=get_clerk_sign_in_url("/admin/themes"), status_code=302)

    per_page = 10
    offset = (page - 1) * per_page

    # Get themes
    if settings.APP_MODE == AppMode.SAAS and user:
        total_count = await get_themes_count(owner_id=user.user_id)
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        page = max(1, min(page, total_pages))
        themes = await get_all_themes(limit=per_page, offset=offset, owner_id=user.user_id)
    else:
        total_count = await get_themes_count()
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        page = max(1, min(page, total_pages))
        themes = await get_all_themes(limit=per_page, offset=offset)

    usage_counts = await get_theme_usage_counts()

    # Enrich theme data for template
    enriched_themes = []
    for theme in themes:
        enriched_themes.append(
            {
                **theme,
                "usage_count": usage_counts.get(theme["name"], 0),
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_themes.html",
        context={
            "themes": enriched_themes,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "clerk_publishable_key": settings.CLERK_PUBLISHABLE_KEY
            if settings.APP_MODE == AppMode.SAAS
            else None,
            "help_url": settings.HELP_URL,
        },
    )


@router.get("/admin/usage", response_class=HTMLResponse)
async def admin_usage(request: Request, checkout: str | None = None):
    """Admin page showing usage statistics and billing information.

    Only available in SaaS mode. Requires authentication.
    """
    settings = get_settings()

    # Only available in SaaS mode
    if settings.APP_MODE != AppMode.SAAS:
        return RedirectResponse(url="/admin/screens", status_code=302)

    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url=get_clerk_sign_in_url("/admin/usage"), status_code=302)

    db = get_database()
    user_data = await db.get_user(user.user_id)
    plan = user_data.get("plan", "free") if user_data else "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    # Count usage
    screen_count = await get_screens_count(owner_id=user.user_id)
    all_themes = await get_all_themes(owner_id=user.user_id)
    custom_theme_count = sum(1 for t in all_themes if not t.get("is_builtin"))

    # Get API quota usage for today
    from datetime import UTC, datetime

    today = datetime.now(UTC).date()
    api_calls_today = await db.get_daily_quota_usage(user.user_id, today)

    # Subscription info
    subscription_status = user_data.get("subscription_status") if user_data else None
    subscription_id = user_data.get("stripe_subscription_id") if user_data else None
    customer_id = user_data.get("stripe_customer_id") if user_data else None
    has_subscription = bool(customer_id)

    return templates.TemplateResponse(
        request=request,
        name="admin_usage.html",
        context={
            "plan": plan,
            "limits": limits,
            "usage": {
                "screens": screen_count,
                "themes": custom_theme_count,
                "api_calls_today": api_calls_today,
            },
            "subscription_status": subscription_status,
            "subscription_id": subscription_id,
            "customer_id": customer_id,
            "has_subscription": has_subscription,
            "checkout": checkout,
            "clerk_publishable_key": settings.CLERK_PUBLISHABLE_KEY,
            "help_url": settings.HELP_URL,
        },
    )


@router.get("/admin/pricing", response_class=HTMLResponse)
async def admin_pricing(request: Request):
    """Pricing page with Stripe pricing table.

    Only available in SaaS mode. Requires authentication.
    """
    settings = get_settings()

    # Only available in SaaS mode
    if settings.APP_MODE != AppMode.SAAS:
        return RedirectResponse(url="/admin/screens", status_code=302)

    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url=get_clerk_sign_in_url("/admin/pricing"), status_code=302)

    # Check if Stripe pricing table is configured
    if not settings.STRIPE_PUBLISHABLE_KEY or not settings.STRIPE_PRICING_TABLE_ID:
        return RedirectResponse(url="/admin/usage", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="admin_pricing.html",
        context={
            "clerk_publishable_key": settings.CLERK_PUBLISHABLE_KEY,
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "stripe_pricing_table_id": settings.STRIPE_PRICING_TABLE_ID,
            "user_email": user.email,
            "help_url": settings.HELP_URL,
        },
    )
