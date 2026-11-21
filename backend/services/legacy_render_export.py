"""Persist legacy render-batch outputs into private cloud storage.

The legacy renderer remains unchanged. This adapter is called only through an
authenticated endpoint that verifies project ownership before storing files.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import ExportedVideo, Project, RenderJob


def persist_legacy_batch_exports(
    db: Session,
    storage,
    *,
    owner_id: str,
    project: Project,
    batch_id: str,
    batch: dict,
    exports_dir: Path,
    now: datetime | None = None,
) -> dict:
    if batch.get("overall_status") != "completed":
        raise ValueError("Only completed render batches can be saved to cloud storage")
    if project.owner_id != owner_id:
        raise PermissionError("Project does not belong to the authenticated user")

    # Make this operation idempotent for repeated clicks / network retries.
    existing_jobs = db.scalars(
        select(RenderJob).where(
            RenderJob.owner_id == owner_id,
            RenderJob.project_id == project.id,
            RenderJob.status == "completed",
        )
    ).all()
    existing = next(
        (job for job in existing_jobs if (job.settings_json or {}).get("legacy_batch_id") == batch_id),
        None,
    )
    if existing:
        exports = db.scalars(
            select(ExportedVideo).where(ExportedVideo.render_job_id == existing.id)
        ).all()
        return {
            "render_job_id": existing.id,
            "exports": [
                {
                    "id": item.id,
                    "filename": item.filename,
                    "size_bytes": item.size_bytes,
                    "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                    "download_url": storage.create_download_url(item.storage_key, expires_seconds=300)
                    if item.storage_deleted_at is None else None,
                }
                for item in exports
            ],
            "already_saved": True,
        }

    safe_batch_id = re.sub(r"[^A-Za-z0-9_-]", "", batch_id)
    if safe_batch_id != batch_id or not safe_batch_id:
        raise ValueError("Invalid render batch identifier")

    candidates: list[tuple[Path, str, str]] = []
    for clip in batch.get("clips", []):
        if clip.get("status") != "completed":
            continue
        raw_path = clip.get("output_path")
        if not raw_path:
            download_url = str(clip.get("download_url") or "")
            raw_name = download_url.split("?", 1)[0].rsplit("/", 1)[-1]
        else:
            raw_name = Path(str(raw_path)).name
        if not raw_name or Path(raw_name).suffix.lower() != ".mp4":
            continue
        local_path = (exports_dir / raw_name).resolve()
        if local_path.parent != exports_dir.resolve() or not local_path.is_file():
            continue
        candidates.append((local_path, raw_name, "video/mp4"))

    zip_path = exports_dir / f"cheat_clip_pro_{safe_batch_id}.zip"
    if zip_path.is_file():
        candidates.append((zip_path.resolve(), zip_path.name, "application/zip"))

    if not candidates:
        raise FileNotFoundError("No completed render files were found for this batch")

    current = now or datetime.now(timezone.utc)
    retention_days = max(1, int(os.environ.get("EXPORT_RETENTION_DAYS", "7")))
    expires_at = current + timedelta(days=retention_days)
    render_job = RenderJob(
        owner_id=owner_id,
        project_id=project.id,
        status="completed",
        progress_percent=100,
        settings_json={"legacy_batch_id": batch_id, "export_count": len(candidates)},
        finished_at=current,
    )
    db.add(render_job)
    db.flush()

    uploaded_keys: list[str] = []
    try:
        records: list[ExportedVideo] = []
        for local_path, filename, content_type in candidates:
            export_id = str(uuid.uuid4())
            key = f"users/{owner_id}/projects/{project.id}/exports/{export_id}/{filename}"
            with local_path.open("rb") as stream:
                stored = storage.put(key, stream, content_type)
            uploaded_keys.append(key)
            record = ExportedVideo(
                id=export_id,
                owner_id=owner_id,
                render_job_id=render_job.id,
                storage_key=key,
                filename=filename,
                content_type=content_type,
                size_bytes=int(stored.size_bytes),
                expires_at=expires_at,
            )
            db.add(record)
            records.append(record)
        db.commit()
        for record in records:
            db.refresh(record)
        return {
            "render_job_id": render_job.id,
            "exports": [
                {
                    "id": item.id,
                    "filename": item.filename,
                    "size_bytes": item.size_bytes,
                    "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                    "download_url": storage.create_download_url(item.storage_key, expires_seconds=300),
                }
                for item in records
            ],
            "already_saved": False,
        }
    except Exception:
        db.rollback()
        for key in uploaded_keys:
            try:
                storage.delete(key)
            except Exception:
                pass
        raise
