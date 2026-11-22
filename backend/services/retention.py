"""Scheduled cleanup for expired source media and rendered exports.

Database records and compact analysis results are retained; large binary objects
are deleted from private object storage according to explicit expiry timestamps.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.database.models import Analysis, ExportedVideo, MediaAsset

logger = logging.getLogger("clipstudio.retention")


def run_retention_sweep(db: Session, storage, *, now: datetime | None = None, limit: int = 100) -> dict[str, int]:
    current = now or datetime.now(timezone.utc)
    deleted_media = 0
    deleted_exports = 0
    failed = 0
    pending_deleted = 0
    rejected_deleted = 0
    pending_ttl_minutes = max(5, int(os.environ.get("PENDING_UPLOAD_TTL_MINUTES", "15")))
    pending_cutoff = current - timedelta(minutes=pending_ttl_minutes)

    media_rows = db.scalars(
        select(MediaAsset)
        .where(
            MediaAsset.storage_key.is_not(None),
            or_(
                and_(
                    MediaAsset.status == "uploaded",
                    MediaAsset.retention_expires_at.is_not(None),
                    MediaAsset.retention_expires_at <= current,
                ),
                and_(
                    MediaAsset.status == "pending_upload",
                    MediaAsset.created_at <= pending_cutoff,
                ),
                MediaAsset.status == "upload_rejected",
            ),
        )
        .order_by(MediaAsset.created_at.asc())
        .limit(limit)
    ).all()
    for media in media_rows:
        try:
            # Never delete a source while an analysis is queued or running.
            active = db.scalar(
                select(Analysis.id).where(
                    Analysis.media_asset_id == media.id,
                    Analysis.status.in_(("queued", "processing")),
                ).limit(1)
            )
            if active:
                continue
            storage.delete(media.storage_key)
            previous_status = media.status
            media.storage_key = None
            media.status = "expired"
            metadata = dict(media.metadata_json or {})
            metadata["cloud_object_deleted_at"] = current.isoformat()
            if previous_status == "pending_upload":
                metadata["pending_upload_expired_at"] = current.isoformat()
                pending_deleted += 1
            elif previous_status == "upload_rejected":
                metadata["rejected_upload_deleted_at"] = current.isoformat()
                rejected_deleted += 1
            else:
                metadata["source_media_deleted_at"] = current.isoformat()
                deleted_media += 1
            media.metadata_json = metadata
        except Exception:
            failed += 1
            logger.exception("Could not delete expired source object for asset %s", media.id)

    export_rows = db.scalars(
        select(ExportedVideo)
        .where(
            ExportedVideo.expires_at.is_not(None),
            ExportedVideo.expires_at <= current,
            ExportedVideo.storage_deleted_at.is_(None),
        )
        .order_by(ExportedVideo.expires_at.asc())
        .limit(limit)
    ).all()
    for export in export_rows:
        try:
            storage.delete(export.storage_key)
            export.storage_deleted_at = current
            deleted_exports += 1
        except Exception:
            failed += 1
            logger.exception("Could not delete expired export object %s", export.id)

    db.commit()
    return {
        "source_media_deleted": deleted_media,
        "pending_uploads_deleted": pending_deleted,
        "rejected_uploads_deleted": rejected_deleted,
        "exports_deleted": deleted_exports,
        "failed": failed,
    }

