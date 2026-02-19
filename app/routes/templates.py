"""Template API endpoints."""

import secrets

from fastapi import APIRouter, HTTPException, Query

from ..auth import AuthOrAccountKey
from ..config import AppMode, get_settings
from ..database import (
    create_template,
    delete_template,
    get_all_pages,
    get_all_templates,
    get_screen_by_id,
    get_template,
    get_templates_count,
    update_template,
)
from ..models import (
    TemplateCategory,
    TemplateCreate,
    TemplateDetail,
    TemplateType,
    TemplateUpdate,
)
from ..utils import generate_template_thumbnail, serialize_screen_to_template

router = APIRouter(prefix="/api/v1/templates", tags=["Templates"])


def generate_template_id() -> str:
    """Generate a unique template ID."""
    return f"tmpl_{secrets.token_hex(8)}"


@router.get("", response_model=dict)
async def list_templates(
    user: AuthOrAccountKey,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    type: TemplateType | None = Query(None, description="Filter by template type"),
    category: TemplateCategory | None = Query(None, description="Filter by category"),
):
    """List available templates with pagination and filtering.

    Returns system templates plus user's own templates (in SaaS mode).
    Templates are sorted by type (system first) then by creation date.

    In SaaS mode, requires authentication (Clerk session or account API key with ak_ prefix).
    """
    settings = get_settings()

    # Determine user_id for filtering
    user_id = None
    if settings.APP_MODE == AppMode.SAAS:
        user_id = user.user_id

    # Convert enums to string values for database query
    type_filter = type.value if type else None
    category_filter = category.value if category else None

    # Get pagination values
    offset = (page - 1) * per_page

    # Get total count for pagination
    total_count = await get_templates_count(
        template_type=type_filter,
        category=category_filter,
        user_id=user_id,
    )
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    page = max(1, min(page, total_pages))

    # Get templates (without configuration for list efficiency)
    templates = await get_all_templates(
        template_type=type_filter,
        category=category_filter,
        user_id=user_id,
        limit=per_page,
        offset=offset,
    )

    return {
        "templates": templates,
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
    }


@router.post("", response_model=TemplateDetail)
async def create_template_from_screen(
    request: TemplateCreate,
    user: AuthOrAccountKey,
):
    """Create a new template from an existing screen.

    Captures the screen's configuration (settings, layout, pages, content)
    and stores it as a reusable template.

    In SaaS mode, requires authentication (Clerk session or account API key with ak_ prefix)
    and the user must own the source screen.
    """
    settings = get_settings()

    # Get the source screen
    screen = await get_screen_by_id(request.screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # In SaaS mode, verify user owns the screen
    if (
        settings.APP_MODE == AppMode.SAAS
        and user
        and screen.get("owner_id")
        and screen["owner_id"] != user.user_id
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to create template from this screen"
        )

    # Get all pages for the screen
    pages = await get_all_pages(request.screen_id)

    # Serialize screen configuration
    configuration = serialize_screen_to_template(screen, pages)

    # Generate thumbnail from configuration
    thumbnail_url = generate_template_thumbnail(configuration)

    # Generate template ID and determine ownership
    template_id = generate_template_id()
    user_id = user.user_id if settings.APP_MODE == AppMode.SAAS and user else None

    # Create the template
    template = await create_template(
        template_id=template_id,
        name=request.name,
        description=request.description,
        category=request.category.value,
        template_type="user",
        configuration=configuration,
        user_id=user_id,
        thumbnail_url=thumbnail_url,
    )

    return template


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template_detail(template_id: str, user: AuthOrAccountKey):
    """Get a specific template by ID, including full configuration.

    In SaaS mode, user templates are only accessible by their owner.
    System templates are accessible by everyone.

    Requires authentication (Clerk session or account API key with ak_ prefix) in SaaS mode.
    """
    template = await get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check access permissions for user templates in SaaS mode
    settings = get_settings()
    if (
        settings.APP_MODE == AppMode.SAAS
        and template.get("type") == "user"
        and template.get("user_id")
        and (not user or template["user_id"] != user.user_id)
    ):
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.patch("/{template_id}", response_model=TemplateDetail)
async def update_template_metadata(
    template_id: str,
    request: TemplateUpdate,
    user: AuthOrAccountKey,
):
    """Update template metadata (name, description, category).

    In SaaS mode, only the template owner can update user templates.
    System templates cannot be modified.

    Requires authentication (Clerk session or account API key with ak_ prefix) in SaaS mode.
    """
    # Check if template exists
    existing = await get_template(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")

    # Cannot modify system templates
    if existing.get("type") == "system":
        raise HTTPException(status_code=403, detail="Cannot modify system templates")

    # In SaaS mode, verify ownership
    settings = get_settings()
    if (
        settings.APP_MODE == AppMode.SAAS
        and existing.get("user_id")
        and existing["user_id"] != user.user_id
    ):
        raise HTTPException(status_code=403, detail="Not authorized to modify this template")

    # Update template
    updated = await update_template(
        template_id=template_id,
        name=request.name,
        description=request.description,
        category=request.category.value if request.category else None,
    )

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update template")

    return updated


@router.delete("/{template_id}")
async def delete_template_endpoint(template_id: str, user: AuthOrAccountKey):
    """Delete a template.

    In SaaS mode, only the template owner can delete user templates.
    System templates cannot be deleted.

    Requires authentication (Clerk session or account API key with ak_ prefix) in SaaS mode.
    """
    # Check if template exists
    existing = await get_template(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")

    # Cannot delete system templates
    if existing.get("type") == "system":
        raise HTTPException(status_code=403, detail="Cannot delete system templates")

    # In SaaS mode, verify ownership
    settings = get_settings()
    if (
        settings.APP_MODE == AppMode.SAAS
        and existing.get("user_id")
        and existing["user_id"] != user.user_id
    ):
        raise HTTPException(status_code=403, detail="Not authorized to delete this template")

    success = await delete_template(template_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete template")

    return {"success": True}
