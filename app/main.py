"""Big Beautiful Screens - Real-time display screens for dashboards and signage."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import AppMode, get_settings
from .database import init_db
from .logging_middleware import UsageLoggingMiddleware, configure_usage_logging
from .mcp.routes import router as mcp_router
from .mcp.streamable_http_asgi import streamable_http_app
from .rate_limit import limiter
from .routes.account_keys import router as account_keys_router
from .routes.admin import router as admin_router
from .routes.billing import router as billing_router
from .routes.clerk_proxy import router as clerk_proxy_router
from .routes.media import public_router as media_public_router
from .routes.media import router as media_router
from .routes.proxy import router as proxy_router
from .routes.screens import router as screens_router
from .routes.templates import router as templates_router
from .routes.themes import router as themes_router
from .routes_me import router as me_router
from .webhooks import router as webhooks_router

# OpenAPI tags for documentation organization
openapi_tags = [
    {"name": "Screens", "description": "Create and manage display screens"},
    {"name": "Pages", "description": "Manage pages within a screen for rotation"},
    {"name": "Themes", "description": "Color themes and styling presets"},
    {"name": "Templates", "description": "Screen templates for quick setup"},
    {"name": "Media", "description": "Upload and manage media files (images, videos)"},
]

# Add SaaS-only tags if in SaaS mode
settings = get_settings()
if settings.APP_MODE == AppMode.SAAS:
    openapi_tags.extend(
        [
            {"name": "me", "description": "User-specific endpoints (SaaS mode)"},
            {"name": "billing", "description": "Subscription and billing management"},
            {"name": "webhooks", "description": "Clerk authentication webhooks"},
        ]
    )

app = FastAPI(
    title="Big Beautiful Screens",
    version="1.0.0",
    description="Real-time display screens for dashboards, status boards, and signage",
    openapi_tags=openapi_tags,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")

    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    if proto == "https":
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )
    return response


# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def custom_openapi():
    """Generate custom OpenAPI schema with security schemes."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=openapi_tags,
    )

    # Add security schemes
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Screen API key (sk_xxx) for screen-specific operations",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Clerk JWT token from __session cookie (SaaS mode)",
        },
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Include API routers
app.include_router(themes_router)
app.include_router(templates_router)
app.include_router(screens_router)
app.include_router(admin_router)
app.include_router(media_router)
app.include_router(media_public_router)
app.include_router(proxy_router)
app.include_router(mcp_router)
app.mount("/mcp/http", streamable_http_app)

# Include SaaS-only routers
if settings.APP_MODE == AppMode.SAAS:
    app.include_router(webhooks_router)
    app.include_router(me_router)
    app.include_router(billing_router)
    app.include_router(clerk_proxy_router)
    app.include_router(account_keys_router)

# Add usage logging middleware in SaaS mode
if settings.APP_MODE == AppMode.SAAS:
    configure_usage_logging(
        destination=settings.USAGE_LOG_DESTINATION,
        file_path=settings.USAGE_LOG_FILE_PATH,
    )
    app.add_middleware(UsageLoggingMiddleware)

# Mount static files
static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.on_event("startup")
async def startup():
    """Initialize database on application startup."""
    await init_db()

    # Seed system templates if none exist
    await seed_system_templates()

    # In self-hosted mode, create demo screen on first run
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        from .database import get_screens_count
        from .onboarding import create_demo_screen

        count = await get_screens_count()
        if count == 0:
            try:
                result = await create_demo_screen()
                print(f"Created demo screen: /screen/{result['screen_id']}")
            except Exception as e:
                print(f"Failed to create demo screen: {e}")


async def seed_system_templates():
    """Seed system templates on first startup if none exist."""
    import secrets

    from .database import (
        create_template,
        delete_template,
        get_all_templates,
        get_template,
        get_templates_count,
    )
    from .seed_templates import get_system_templates

    try:
        # Check if any system templates exist
        count = await get_templates_count(template_type="system")
        if count > 0:
            # Spot-check that existing templates have pages in their configuration.
            # NOTE: get_all_templates omits the configuration column for efficiency,
            # so we must fetch a full template via get_template to inspect it.
            existing = await get_all_templates(template_type="system")
            needs_reseed = False
            for tmpl in existing:
                full = await get_template(tmpl["id"])
                config = full.get("configuration", {}) if full else {}
                pages = config.get("pages", []) if isinstance(config, dict) else []
                if not pages:
                    needs_reseed = True
                    break

            if not needs_reseed:
                return  # System templates already exist with valid pages

            # Delete existing system templates and reseed
            print("Reseeding system templates (existing templates had empty pages)")
            for tmpl in existing:
                await delete_template(tmpl["id"])

        # Get seed templates and insert them
        templates = get_system_templates()
        for template in templates:
            template_id = f"tmpl_{secrets.token_hex(8)}"
            await create_template(
                template_id=template_id,
                name=template["name"],
                description=template["description"],
                category=template["category"],
                template_type="system",
                configuration=template["configuration"],
                user_id=None,  # System templates have no owner
                thumbnail_url=template.get("thumbnail_url"),
            )

        print(f"Seeded {len(templates)} system templates")
    except Exception as e:
        print(f"Failed to seed system templates: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
