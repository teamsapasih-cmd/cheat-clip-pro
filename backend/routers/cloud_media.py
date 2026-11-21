"""Authenticated cloud media upload endpoints.

Uploads go directly to a private S3-compatible bucket using short-lived signed
URLs. Existing local upload routes remain unchanged until deployment is tested.
"""
from __future__ import annotations

import os
import re
import uuid
from pathlib import PurePath

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.cloud.factory import build_object_storage
from backend.database.dependencies import get_db_session
from backend.database.models import MediaAsset, Project, User
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/media/cloud", tags=["Cloud Media"])

_ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/flac",
}
_MAX_UPLOAD_BYTES = int(os.environ.get("MAX_CLOUD_UPLOAD_BYTES", str(50 * 1024 * 1024)))


class UploadIntentRequest(BaseModel):
    project_id: str
    filename: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=160)
    size_bytes: int = Field(gt=0, le=_MAX_UPLOAD_BYTES)


@router.post("/upload-intent", status_code=status.HTTP_201_CREATED)
def create_upload_intent(
    body: UploadIntentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    project = db.scalar(
        select(Project).where(Project.id == body.project_id, Project.owner_id == user.id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    content_type = body.content_type.strip().lower()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported media content type")

    try:
        storage = build_object_storage()
    except (RuntimeError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="Cloud media storage is not configured on this deployment",
        )

    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", PurePath(body.filename).name).strip("._")
    if not safe_name:
        safe_name = "media-upload"
    asset_id = str(uuid.uuid4())
    storage_key = f"users/{user.id}/projects/{project.id}/{asset_id}/{safe_name}"

    try:
        upload_url = storage.create_upload_url(storage_key, content_type, expires_seconds=300)
    except Exception:
        raise HTTPException(status_code=503, detail="Unable to create a secure upload URL")

    asset = MediaAsset(
        id=asset_id,
        project_id=project.id,
        owner_id=user.id,
        original_filename=safe_name,
        storage_key=storage_key,
        source_type="upload",
        content_type=content_type,
        size_bytes=0,
        status="pending_upload",
        metadata_json={"expected_size_bytes": body.size_bytes},
    )
    db.add(asset)
    db.commit()

    return {
        "media_asset_id": asset_id,
        "upload_url": upload_url,
        "method": "PUT",
        "required_headers": {"Content-Type": content_type},
        "expires_in": 300,
        "max_size_bytes": body.size_bytes,
    }


@router.post("/{media_asset_id}/complete")
def complete_cloud_upload(
    media_asset_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    asset = db.scalar(
        select(MediaAsset).where(
            MediaAsset.id == media_asset_id,
            MediaAsset.owner_id == user.id,
        )
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Media asset not found")
    if asset.status != "pending_upload" or not asset.storage_key:
        raise HTTPException(status_code=409, detail="Media asset is not awaiting upload")

    try:
        storage = build_object_storage()
        metadata = storage.get_metadata(asset.storage_key)
    except Exception:
        raise HTTPException(status_code=404, detail="Uploaded object was not found in cloud storage")

    actual_size = int(metadata["size_bytes"])
    expected_size = int(asset.metadata_json.get("expected_size_bytes", 0))
    actual_type = str(metadata["content_type"]).lower()
    if actual_size <= 0 or actual_size != expected_size or actual_size > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded file size does not match the upload request")
    if actual_type != (asset.content_type or "").lower():
        raise HTTPException(status_code=400, detail="Uploaded file content type does not match the upload request")

    asset.size_bytes = actual_size
    asset.status = "uploaded"
    asset.metadata_json = {
        "verified": True,
        "verified_size_bytes": actual_size,
        "verified_content_type": actual_type,
    }
    db.commit()
    db.refresh(asset)

    return {
        "media_asset_id": asset.id,
        "status": asset.status,
        "size_bytes": asset.size_bytes,
        "content_type": asset.content_type,
    }
