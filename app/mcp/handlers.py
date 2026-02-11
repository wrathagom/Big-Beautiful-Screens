"""MCP Tool handlers for Big Beautiful Screens.

This module implements the actual logic for each MCP tool, calling the
underlying database and API functions to perform operations.
"""

import secrets
import uuid
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from ..config import AppMode, get_settings
from ..connection_manager import manager
from ..database import (
    create_screen,
    delete_screen,
    get_all_pages,
    get_all_screens,
    get_rotation_settings,
    get_screen_by_id,
    get_screens_count,
    get_template,
    update_rotation_settings,
    update_screen_name,
    upsert_page,
)
from ..db import get_database
from ..layouts import list_layout_presets
from ..utils import (
    deserialize_template_to_screen_config,
    normalize_content,
    resolve_theme_settings,
)
from .arg_models import (
    CreatePageArgs,
    CreateScreenArgs,
    DeleteScreenArgs,
    GetScreenArgs,
    ListLayoutsArgs,
    ListScreensArgs,
    SendMessageArgs,
    UpdateScreenArgs,
)


class MCPContext:
    """Context for MCP operations including authentication state."""

    def __init__(self, api_key: str | None = None, user_id: str | None = None):
        self.api_key = api_key
        self.user_id = user_id
        self.settings = get_settings()

    @property
    def is_saas(self) -> bool:
        return self.settings.APP_MODE == AppMode.SAAS

    @property
    def is_self_hosted(self) -> bool:
        return self.settings.APP_MODE == AppMode.SELF_HOSTED


_mcp_context_var: ContextVar[MCPContext | None] = ContextVar("_mcp_context_var", default=None)


def set_mcp_context(api_key: str | None = None, user_id: str | None = None) -> Token[MCPContext | None]:
    """Set the MCP context for the current async task.

    Returns a token that can be passed to reset_mcp_context() to restore
    the previous value.
    """
    return _mcp_context_var.set(MCPContext(api_key=api_key, user_id=user_id))


def reset_mcp_context(token: Token[MCPContext | None]) -> None:
    """Reset the MCP context to its previous value using the token from set_mcp_context."""
    _mcp_context_var.reset(token)


def get_mcp_context() -> MCPContext:
    """Get the MCP context for the current async task."""
    ctx = _mcp_context_var.get()
    if ctx is None:
        ctx = MCPContext()
        _mcp_context_var.set(ctx)
    return ctx


def _validation_error_to_response(e: ValidationError) -> dict[str, Any]:
    """Convert Pydantic validation errors into the MCP handler error shape.

    Some unit tests (and the pre-Pydantic behavior) expect missing required
    fields to return `{ "error": "<field> is required" }` instead of raising.
    """

    errors = e.errors()
    missing = [err for err in errors if err.get("type") == "missing"]
    if missing:
        loc = missing[0].get("loc") or ()
        field = loc[-1] if loc else "field"
        return {"error": f"{field} is required"}

    return {"error": "Invalid arguments", "details": errors}


async def handle_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Route tool calls to their handlers."""
    handlers = {
        "list_screens": handle_list_screens,
        "create_screen": handle_create_screen,
        "get_screen": handle_get_screen,
        "update_screen": handle_update_screen,
        "delete_screen": handle_delete_screen,
        "send_message": handle_send_message,
        "create_page": handle_create_page,
        "list_layouts": handle_list_layouts,
    }

    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}

    try:
        return await handler(arguments)
    except ValidationError as e:
        return _validation_error_to_response(e)
    except Exception as e:
        return {"error": str(e)}


async def handle_list_screens(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle list_screens tool call."""
    try:
        args = ListScreensArgs.model_validate(arguments)
    except ValidationError as e:
        return _validation_error_to_response(e)
    ctx = get_mcp_context()
    page = args.page
    per_page = args.per_page
    offset = (page - 1) * per_page

    owner_id = ctx.user_id if ctx.is_saas else None
    org_id = None

    total_count = await get_screens_count(owner_id=owner_id, org_id=org_id)
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    page = max(1, min(page, total_pages))

    screens = await get_all_screens(limit=per_page, offset=offset, owner_id=owner_id, org_id=org_id)

    return {
        "screens": [
            {
                "screen_id": s["id"],
                "name": s.get("name"),
                "created_at": s.get("created_at"),
                "last_updated": s.get("last_updated"),
                "screen_url": f"/screen/{s['id']}",
                "viewer_count": manager.get_viewer_count(s["id"]),
            }
            for s in screens
        ],
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
    }


async def handle_create_screen(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle create_screen tool call."""
    try:
        args = CreateScreenArgs.model_validate(arguments)
    except ValidationError as e:
        return _validation_error_to_response(e)
    ctx = get_mcp_context()
    name = args.name
    template_id = args.template_id

    template = None
    if template_id:
        template = await get_template(template_id)
        if not template:
            return {"error": "Template not found"}

        if (
            ctx.is_saas
            and template.get("type") == "user"
            and template.get("user_id")
            and (not ctx.user_id or template["user_id"] != ctx.user_id)
        ):
            return {"error": "Template not found"}

    owner_id = None
    org_id = None
    if ctx.is_saas and ctx.user_id:
        owner_id = ctx.user_id

        db = get_database()
        user_data = await db.get_user(ctx.user_id)

        from ..config import PLAN_LIMITS

        plan = user_data.get("plan", "free") if user_data else "free"
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
        screen_limit = limits.get("screens", 3)

        current_count = await get_screens_count(owner_id=ctx.user_id)
        if current_count >= screen_limit:
            return {
                "error": f"Screen limit reached ({screen_limit} screens on {plan} plan). Upgrade to create more."
            }

    screen_id = uuid.uuid4().hex[:12]
    api_key = f"sk_{secrets.token_urlsafe(24)}"
    created_at = datetime.now(UTC).isoformat()

    await create_screen(screen_id, api_key, created_at, name=name, owner_id=owner_id, org_id=org_id)

    if template and template.get("configuration"):
        screen_settings, pages = deserialize_template_to_screen_config(template["configuration"])

        if screen_settings:
            await update_rotation_settings(
                screen_id,
                enabled=screen_settings.get("enabled"),
                interval=screen_settings.get("interval"),
                gap=screen_settings.get("gap"),
                border_radius=screen_settings.get("border_radius"),
                panel_shadow=screen_settings.get("panel_shadow"),
                background_color=screen_settings.get("background_color"),
                panel_color=screen_settings.get("panel_color"),
                font_family=screen_settings.get("font_family"),
                font_color=screen_settings.get("font_color"),
                theme=screen_settings.get("theme"),
                head_html=screen_settings.get("head_html"),
                default_layout=screen_settings.get("default_layout"),
                transition=screen_settings.get("transition"),
                transition_duration=screen_settings.get("transition_duration"),
                debug_enabled=screen_settings.get("debug_enabled"),
            )

        for page in pages:
            await upsert_page(
                screen_id,
                page["name"],
                page["payload"],
                duration=page.get("duration"),
                expires_at=None,
            )

    return {
        "screen_id": screen_id,
        "api_key": api_key,
        "screen_url": f"/screen/{screen_id}",
        "api_url": f"/api/v1/screens/{screen_id}/message",
        "name": name,
    }


async def handle_get_screen(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle get_screen tool call."""
    try:
        args = GetScreenArgs.model_validate(arguments)
    except ValidationError as e:
        return _validation_error_to_response(e)
    screen_id = args.screen_id

    screen = await get_screen_by_id(screen_id)
    if not screen:
        return {"error": "Screen not found"}

    settings = await get_rotation_settings(screen_id)

    return {
        "screen_id": screen["id"],
        "name": screen.get("name"),
        "created_at": screen.get("created_at"),
        "last_updated": screen.get("last_updated"),
        "settings": settings,
    }


async def handle_update_screen(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle update_screen tool call."""
    try:
        args = UpdateScreenArgs.model_validate(arguments)
    except ValidationError as e:
        return _validation_error_to_response(e)
    screen_id = args.screen_id
    api_key = args.api_key

    screen = await get_screen_by_id(screen_id)
    if not screen:
        return {"error": "Screen not found"}

    if screen["api_key"] != api_key:
        return {"error": "Invalid API key"}

    name = args.name
    if name is not None:
        await update_screen_name(screen_id, name)

    theme = args.theme
    rotation_enabled = args.rotation_enabled
    rotation_interval = args.rotation_interval
    gap = args.gap
    border_radius = args.border_radius
    panel_shadow = args.panel_shadow
    background_color = args.background_color
    panel_color = args.panel_color
    font_family = args.font_family
    font_color = args.font_color
    default_layout = args.default_layout
    if hasattr(default_layout, "model_dump"):
        default_layout = default_layout.model_dump(exclude_none=True)
    transition = args.transition
    transition_duration = args.transition_duration

    await update_rotation_settings(
        screen_id,
        enabled=rotation_enabled,
        interval=rotation_interval,
        gap=gap,
        border_radius=border_radius,
        panel_shadow=panel_shadow,
        background_color=background_color,
        panel_color=panel_color,
        font_family=font_family,
        font_color=font_color,
        theme=theme,
        default_layout=default_layout,
        transition=transition,
        transition_duration=transition_duration,
    )

    pages = await get_all_pages(screen_id)
    rotation = await get_rotation_settings(screen_id)
    resolved_rotation = await resolve_theme_settings(rotation)

    await manager.broadcast(
        screen_id, {"type": "pages_sync", "pages": pages, "rotation": resolved_rotation}
    )

    return {
        "success": True,
        "screen_id": screen_id,
        "settings": resolved_rotation,
    }


async def handle_delete_screen(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle delete_screen tool call."""
    try:
        args = DeleteScreenArgs.model_validate(arguments)
    except ValidationError as e:
        return _validation_error_to_response(e)
    screen_id = args.screen_id
    api_key = args.api_key

    screen = await get_screen_by_id(screen_id)
    if not screen:
        return {"error": "Screen not found"}

    if screen["api_key"] != api_key:
        return {"error": "Invalid API key"}

    await delete_screen(screen_id)
    return {"success": True, "message": "Screen deleted"}


async def handle_send_message(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle send_message tool call."""
    try:
        args = SendMessageArgs.model_validate(arguments)
    except ValidationError as e:
        return _validation_error_to_response(e)
    screen_id = args.screen_id
    api_key = args.api_key
    content = args.content

    screen = await get_screen_by_id(screen_id)
    if not screen:
        return {"error": "Screen not found"}

    if screen["api_key"] != api_key:
        return {"error": "Invalid API key"}

    normalized_content = normalize_content(content)

    layout_value = args.layout
    if hasattr(layout_value, "model_dump"):
        layout_value = layout_value.model_dump(exclude_none=True)

    message_payload = {
        "content": normalized_content,
        "background_color": args.background_color,
        "panel_color": args.panel_color,
        "font_family": args.font_family,
        "font_color": args.font_color,
        "gap": args.gap,
        "border_radius": args.border_radius,
        "panel_shadow": args.panel_shadow,
        "layout": layout_value,
    }

    page_data = await upsert_page(screen_id, "default", message_payload)

    viewers = await manager.broadcast(screen_id, {"type": "page_update", "page": page_data})

    return {"success": True, "viewers": viewers}


async def handle_create_page(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle create_page tool call."""
    try:
        args = CreatePageArgs.model_validate(arguments)
    except ValidationError as e:
        return _validation_error_to_response(e)
    screen_id = args.screen_id
    page_name = args.page_name
    api_key = args.api_key
    content = args.content

    screen = await get_screen_by_id(screen_id)
    if not screen:
        return {"error": "Screen not found"}

    if screen["api_key"] != api_key:
        return {"error": "Invalid API key"}

    normalized_content = normalize_content(content)

    layout_value = args.layout
    if hasattr(layout_value, "model_dump"):
        layout_value = layout_value.model_dump(exclude_none=True)

    message_payload = {
        "content": normalized_content,
        "background_color": args.background_color,
        "panel_color": args.panel_color,
        "font_family": args.font_family,
        "font_color": args.font_color,
        "gap": args.gap,
        "border_radius": args.border_radius,
        "panel_shadow": args.panel_shadow,
        "layout": layout_value,
        "transition": args.transition,
        "transition_duration": args.transition_duration,
    }

    duration = args.duration

    page_data = await upsert_page(screen_id, page_name, message_payload, duration=duration)

    viewers = await manager.broadcast(screen_id, {"type": "page_update", "page": page_data})

    return {"success": True, "page": page_data, "viewers": viewers}


async def handle_list_layouts(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle list_layouts tool call."""
    try:
        ListLayoutsArgs.model_validate(arguments)
    except ValidationError as e:
        return _validation_error_to_response(e)
    return {"layouts": list_layout_presets()}
