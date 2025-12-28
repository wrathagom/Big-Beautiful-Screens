"""Media Library API endpoints."""

import os
import uuid
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, RedirectResponse

from ..auth import OptionalUser
from ..config import (
    ALLOWED_MEDIA_TYPES,
    PLAN_LIMITS,
    AppMode,
    get_settings,
)
from ..database import (
    create_media,
    delete_media,
    get_all_media,
    get_media_by_id,
    get_media_count,
    get_storage_used,
)
from ..db import get_database
from ..models_media import (
    MediaDeleteResponse,
    MediaDetailResponse,
    MediaErrorResponse,
    MediaItem,
    MediaListResponse,
    MediaUploadResponse,
)
from ..storage import get_storage
from ..storage.local import LocalStorage

router = APIRouter(prefix="/api/v1/media", tags=["Media"])


def _can_use_media_library(user: OptionalUser, settings) -> tuple[bool, str | None]:
    """Check if the user can use the media library.

    Returns (can_use, error_message).
    """
    # Self-hosted: always allowed (no auth required)
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True, None

    # SaaS mode: require authentication
    if not user:
        return False, "Authentication required"

    return True, None


async def _check_media_enabled(user: OptionalUser) -> tuple[bool, str | None]:
    """Check if media is enabled for this user's plan.

    Returns (enabled, error_message).
    """
    settings = get_settings()

    # Self-hosted: always enabled
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True, None

    # SaaS: check plan
    if not user:
        return False, "Authentication required"

    db = get_database()
    user_data = await db.get_user(user.user_id)
    plan = user_data.get("plan", "free") if user_data else "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    if not limits.get("media_enabled", False):
        return False, f"Media library is not available on the {plan} plan. Upgrade to Pro or Team."

    return True, None


async def _get_storage_quota(user: OptionalUser) -> int:
    """Get storage quota in bytes for the user. Returns -1 for unlimited."""
    settings = get_settings()

    # Self-hosted: unlimited
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return -1

    if not user:
        return 0

    db = get_database()
    user_data = await db.get_user(user.user_id)
    plan = user_data.get("plan", "free") if user_data else "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    return limits.get("storage_bytes", 0)


async def _check_storage_quota(user: OptionalUser, file_size: int) -> tuple[bool, str | None]:
    """Check if adding this file would exceed storage quota.

    Returns (within_quota, error_message).
    """
    settings = get_settings()

    # Self-hosted: unlimited
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True, None

    if not user:
        return False, "Authentication required"

    quota = await _get_storage_quota(user)
    if quota == -1:
        return True, None

    current_usage = await get_storage_used(owner_id=user.user_id)
    if current_usage + file_size > quota:
        quota_mb = quota / (1024 * 1024)
        usage_mb = current_usage / (1024 * 1024)
        return False, f"Storage quota exceeded. Used {usage_mb:.1f}MB of {quota_mb:.1f}MB."

    return True, None


def _can_access_media(user: OptionalUser, media: dict, settings) -> bool:
    """Check if user can access this media item."""
    # Self-hosted: all accessible
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True

    if not user:
        return False

    # Owner can access
    if media.get("owner_id") == user.user_id:
        return True

    # Org members can access org media
    return bool(media.get("org_id") and media.get("org_id") == user.org_id)


@router.post(
    "/upload",
    response_model=MediaUploadResponse,
    responses={
        400: {"model": MediaErrorResponse, "description": "Invalid file type"},
        402: {"model": MediaErrorResponse, "description": "Storage quota exceeded"},
        403: {"model": MediaErrorResponse, "description": "Media not available on plan"},
        413: {"model": MediaErrorResponse, "description": "File too large"},
    },
)
async def upload_media(
    file: UploadFile = File(...),
    user: OptionalUser = None,
):
    """Upload a media file (image or video).

    In SaaS mode, requires authentication and checks plan limits.
    In self-hosted mode, uploads are unlimited.
    """
    settings = get_settings()

    # Check if user can use media library
    can_use, error = _can_use_media_library(user, settings)
    if not can_use:
        raise HTTPException(status_code=401, detail=error)

    # Check if media is enabled for this plan
    enabled, error = await _check_media_enabled(user)
    if not enabled:
        raise HTTPException(status_code=403, detail=error)

    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {content_type}. Allowed types: images (PNG, JPG, GIF, WebP, SVG) and videos (MP4, WebM, MOV).",
        )

    # Check file size
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file_data = await file.read()
    file_size = len(file_data)

    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    # Check storage quota
    within_quota, error = await _check_storage_quota(user, file_size)
    if not within_quota:
        raise HTTPException(status_code=402, detail=error)

    # Upload to storage
    storage = get_storage()
    owner_id = user.user_id if user else None

    result = await storage.upload(
        file_data=file_data,
        filename=file.filename or "unnamed",
        content_type=content_type,
        owner_id=owner_id,
    )

    # Create database record
    media_id = str(uuid.uuid4())
    org_id = user.org_id if user else None

    media_data = await create_media(
        media_id=media_id,
        filename=os.path.basename(result.storage_path),
        original_filename=file.filename or "unnamed",
        content_type=content_type,
        size_bytes=result.size_bytes,
        storage_path=result.storage_path,
        storage_backend=settings.STORAGE_BACKEND,
        owner_id=owner_id,
        org_id=org_id,
    )

    return MediaUploadResponse(
        media=MediaItem(
            id=media_id,
            filename=media_data["filename"],
            original_filename=media_data["original_filename"],
            content_type=media_data["content_type"],
            size_bytes=media_data["size_bytes"],
            url=result.public_url,
            created_at=media_data["created_at"],
            updated_at=media_data["updated_at"],
        )
    )


@router.get("", response_model=MediaListResponse)
async def list_media(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    content_type: Literal["image", "video"] | None = Query(
        None, description="Filter by content type"
    ),
    user: OptionalUser = None,
):
    """List media files with pagination.

    In SaaS mode, returns only the user's media.
    In self-hosted mode, returns all media.
    """
    settings = get_settings()

    # Check access
    can_use, error = _can_use_media_library(user, settings)
    if not can_use:
        raise HTTPException(status_code=401, detail=error)

    # Check if media is enabled
    enabled, error = await _check_media_enabled(user)
    if not enabled:
        raise HTTPException(status_code=403, detail=error)

    # Get ownership filter
    owner_id = user.user_id if user and settings.APP_MODE == AppMode.SAAS else None
    org_id = user.org_id if user and settings.APP_MODE == AppMode.SAAS else None

    # Get media
    offset = (page - 1) * per_page
    media_items = await get_all_media(
        limit=per_page,
        offset=offset,
        owner_id=owner_id,
        org_id=org_id,
        content_type_filter=content_type,
    )

    total_count = await get_media_count(owner_id=owner_id, org_id=org_id)
    storage_used = await get_storage_used(owner_id=owner_id, org_id=org_id)
    storage_quota = await _get_storage_quota(user)

    # Build response
    storage = get_storage()
    items = []
    for item in media_items:
        items.append(
            MediaItem(
                id=item["id"],
                filename=item["filename"],
                original_filename=item["original_filename"],
                content_type=item["content_type"],
                size_bytes=item["size_bytes"],
                url=storage.get_public_url(item["storage_path"]),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
            )
        )

    return MediaListResponse(
        media=items,
        total_count=total_count,
        storage_used_bytes=storage_used,
        storage_quota_bytes=storage_quota,
    )


@router.get(
    "/{media_id}",
    response_model=MediaDetailResponse,
    responses={
        404: {"model": MediaErrorResponse, "description": "Media not found"},
    },
)
async def get_media(
    media_id: str,
    user: OptionalUser = None,
):
    """Get details of a specific media item."""
    settings = get_settings()

    # Check access
    can_use, error = _can_use_media_library(user, settings)
    if not can_use:
        raise HTTPException(status_code=401, detail=error)

    # Get media
    media = await get_media_by_id(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Check ownership in SaaS mode
    if settings.APP_MODE == AppMode.SAAS and not _can_access_media(user, media, settings):
        raise HTTPException(status_code=404, detail="Media not found")

    storage = get_storage()
    return MediaDetailResponse(
        media=MediaItem(
            id=media["id"],
            filename=media["filename"],
            original_filename=media["original_filename"],
            content_type=media["content_type"],
            size_bytes=media["size_bytes"],
            url=storage.get_public_url(media["storage_path"]),
            created_at=media["created_at"],
            updated_at=media["updated_at"],
        )
    )


@router.delete(
    "/{media_id}",
    response_model=MediaDeleteResponse,
    responses={
        404: {"model": MediaErrorResponse, "description": "Media not found"},
    },
)
async def delete_media_item(
    media_id: str,
    user: OptionalUser = None,
):
    """Delete a media file.

    Removes the file from storage and the database record.
    """
    settings = get_settings()

    # Check access
    can_use, error = _can_use_media_library(user, settings)
    if not can_use:
        raise HTTPException(status_code=401, detail=error)

    # Get media to check ownership and get storage path
    media = await get_media_by_id(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Check ownership in SaaS mode
    if settings.APP_MODE == AppMode.SAAS and not _can_access_media(user, media, settings):
        raise HTTPException(status_code=404, detail="Media not found")

    # Delete from storage
    storage = get_storage()
    await storage.delete(media["storage_path"])

    # Delete from database
    await delete_media(media_id)

    return MediaDeleteResponse()


# Public file serving endpoint (no auth required)
public_router = APIRouter(tags=["Media"])


@public_router.get("/media/files/{file_path:path}")
async def serve_media_file(file_path: str):
    """Serve a media file.

    For local storage, serves the file directly.
    For S3/R2 storage, redirects to the public URL.
    """
    storage = get_storage()

    # Check if file exists
    if not await storage.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # For local storage, serve the file
    if isinstance(storage, LocalStorage):
        full_path = storage.get_file_path(file_path)
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Determine media type from extension
        suffix = full_path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mov": "video/quicktime",
        }
        media_type = media_types.get(suffix, "application/octet-stream")

        return FileResponse(
            path=full_path,
            media_type=media_type,
            filename=full_path.name,
        )

    # For cloud storage, redirect to public URL
    public_url = storage.get_public_url(file_path)
    return RedirectResponse(url=public_url, status_code=302)
