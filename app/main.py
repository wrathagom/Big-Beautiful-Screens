"""Big Beautiful Screens - Real-time display screens for dashboards and signage."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import AppMode, get_settings
from .database import init_db
from .routes.admin import router as admin_router
from .routes.screens import router as screens_router
from .routes.themes import router as themes_router
from .routes_me import router as me_router
from .webhooks import router as webhooks_router

# OpenAPI tags for documentation organization
openapi_tags = [
    {"name": "Screens", "description": "Create and manage display screens"},
    {"name": "Pages", "description": "Manage pages within a screen for rotation"},
    {"name": "Themes", "description": "Color themes and styling presets"},
]

# Add SaaS-only tags if in SaaS mode
settings = get_settings()
if settings.APP_MODE == AppMode.SAAS:
    openapi_tags.extend(
        [
            {"name": "me", "description": "User-specific endpoints (SaaS mode)"},
            {"name": "webhooks", "description": "Clerk authentication webhooks"},
        ]
    )

app = FastAPI(
    title="Big Beautiful Screens",
    version="1.0.0",
    description="Real-time display screens for dashboards, status boards, and signage",
    openapi_tags=openapi_tags,
)

# Include API routers
app.include_router(themes_router)
app.include_router(screens_router)
app.include_router(admin_router)

# Include SaaS-only routers
if settings.APP_MODE == AppMode.SAAS:
    app.include_router(webhooks_router)
    app.include_router(me_router)

# Mount static files
static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.on_event("startup")
async def startup():
    """Initialize database on application startup."""
    await init_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
