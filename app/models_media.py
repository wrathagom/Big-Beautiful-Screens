"""Pydantic models for media operations."""

from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    """Representation of a media item."""

    id: str
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    url: str
    created_at: str
    updated_at: str


class MediaUploadResponse(BaseModel):
    """Response from uploading a media file."""

    success: bool = True
    media: MediaItem


class MediaListResponse(BaseModel):
    """Response for listing media."""

    media: list[MediaItem]
    total_count: int
    storage_used_bytes: int
    storage_quota_bytes: int = Field(
        description="Storage quota in bytes. -1 means unlimited (self-hosted)."
    )


class MediaDetailResponse(BaseModel):
    """Response for getting a single media item."""

    success: bool = True
    media: MediaItem


class MediaDeleteResponse(BaseModel):
    """Response for deleting media."""

    success: bool = True
    message: str = "Media deleted successfully"


class MediaErrorResponse(BaseModel):
    """Error response for media operations."""

    success: bool = False
    error: str
    detail: str | None = None
