from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.database.models import Base, User, Project, MediaAsset, Analysis, ExportedVideo
from backend.services.retention import run_retention_sweep


class FakeStorage:
    def __init__(self):
        self.deleted = []
    def delete(self, key):
        self.deleted.append(key)


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_expired_media_deleted_but_analysis_records_retained():
    db = make_db()
    now = datetime.now(timezone.utc)
    user = User(email="retention@example.com")
    db.add(user); db.flush()
    project = Project(owner_id=user.id, name="Test")
    db.add(project); db.flush()
    media = MediaAsset(owner_id=user.id, project_id=project.id, original_filename="source.mp4",
        storage_key="users/u/source.mp4", status="uploaded", retention_expires_at=now-timedelta(days=1))
    db.add(media); db.flush()
    analysis = Analysis(owner_id=user.id, media_asset_id=media.id, status="completed")
    db.add(analysis); db.commit()
    storage = FakeStorage()
    result = run_retention_sweep(db, storage, now=now)
    assert result["source_media_deleted"] == 1
    assert storage.deleted == ["users/u/source.mp4"]
    db.refresh(media); db.refresh(analysis)
    assert media.storage_key is None and media.status == "expired"
    assert db.get(Analysis, analysis.id) is not None
    db.close()


def test_active_analysis_prevents_source_media_deletion():
    db = make_db()
    now = datetime.now(timezone.utc)
    user = User(email="active@example.com")
    db.add(user); db.flush()
    project = Project(owner_id=user.id, name="Test")
    db.add(project); db.flush()
    media = MediaAsset(owner_id=user.id, project_id=project.id, original_filename="source.mp4",
        storage_key="users/u/active.mp4", status="uploaded", retention_expires_at=now-timedelta(days=1))
    db.add(media); db.flush()
    db.add(Analysis(owner_id=user.id, media_asset_id=media.id, status="processing")); db.commit()
    storage = FakeStorage()
    result = run_retention_sweep(db, storage, now=now)
    assert result["source_media_deleted"] == 0
    assert storage.deleted == []
    db.close()


def test_expired_export_object_is_deleted_and_record_is_preserved():
    db = make_db()
    now = datetime.now(timezone.utc)
    user = User(email="export-retention@example.com")
    db.add(user); db.flush()
    project = Project(owner_id=user.id, name="Exports")
    db.add(project); db.flush()
    render_job = __import__("backend.database.models", fromlist=["RenderJob"]).RenderJob(
        owner_id=user.id, project_id=project.id, status="completed"
    )
    db.add(render_job); db.flush()
    export = ExportedVideo(
        owner_id=user.id, render_job_id=render_job.id,
        storage_key="users/u/exports/final.mp4", filename="final.mp4",
        expires_at=now - timedelta(hours=1),
    )
    db.add(export); db.commit()
    storage = FakeStorage()

    result = run_retention_sweep(db, storage, now=now)

    assert result["exports_deleted"] == 1
    assert storage.deleted == ["users/u/exports/final.mp4"]
    db.refresh(export)
    deleted_at = export.storage_deleted_at
    if deleted_at.tzinfo is None:  # SQLite drops timezone metadata for DateTime(timezone=True).
        deleted_at = deleted_at.replace(tzinfo=timezone.utc)
    assert deleted_at == now
    assert db.get(ExportedVideo, export.id) is not None
    db.close()


def test_export_without_expiry_is_not_deleted():
    db = make_db()
    user = User(email="keep-export@example.com")
    db.add(user); db.flush()
    project = Project(owner_id=user.id, name="Keep")
    db.add(project); db.flush()
    from backend.database.models import RenderJob
    job = RenderJob(owner_id=user.id, project_id=project.id, status="completed")
    db.add(job); db.flush()
    export = ExportedVideo(
        owner_id=user.id, render_job_id=job.id,
        storage_key="users/u/exports/keep.mp4", filename="keep.mp4",
    )
    db.add(export); db.commit()
    storage = FakeStorage()

    result = run_retention_sweep(db, storage)

    assert result["exports_deleted"] == 0
    assert storage.deleted == []
    assert export.storage_deleted_at is None
    db.close()


def test_abandoned_and_rejected_cloud_upload_objects_are_cleaned():
    db = make_db()
    now = datetime.now(timezone.utc)
    user = User(email="pending-upload-retention@example.com")
    db.add(user); db.flush()
    project = Project(owner_id=user.id, name="Pending uploads")
    db.add(project); db.flush()
    abandoned = MediaAsset(
        owner_id=user.id, project_id=project.id, original_filename="abandoned.mp4",
        storage_key="users/u/abandoned.mp4", status="pending_upload",
        created_at=now - timedelta(hours=1),
    )
    rejected = MediaAsset(
        owner_id=user.id, project_id=project.id, original_filename="rejected.mp4",
        storage_key="users/u/rejected.mp4", status="upload_rejected",
        created_at=now,
    )
    recent = MediaAsset(
        owner_id=user.id, project_id=project.id, original_filename="recent.mp4",
        storage_key="users/u/recent.mp4", status="pending_upload",
        created_at=now - timedelta(minutes=1),
    )
    db.add_all([abandoned, rejected, recent]); db.commit()
    storage = FakeStorage()

    result = run_retention_sweep(db, storage, now=now)

    assert result["pending_uploads_deleted"] == 1
    assert result["rejected_uploads_deleted"] == 1
    assert set(storage.deleted) == {"users/u/abandoned.mp4", "users/u/rejected.mp4"}
    db.refresh(abandoned); db.refresh(rejected); db.refresh(recent)
    assert abandoned.status == "expired" and abandoned.storage_key is None
    assert rejected.status == "expired" and rejected.storage_key is None
    assert recent.status == "pending_upload" and recent.storage_key is not None
    db.close()


def test_failed_pending_upload_object_deletion_is_retried():
    class FailOnceStorage(FakeStorage):
        def __init__(self):
            super().__init__()
            self.calls = 0
        def delete(self, key):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary storage error")
            super().delete(key)

    db = make_db()
    now = datetime.now(timezone.utc)
    user = User(email="pending-upload-retry@example.com")
    db.add(user); db.flush()
    project = Project(owner_id=user.id, name="Retry")
    db.add(project); db.flush()
    asset = MediaAsset(
        owner_id=user.id, project_id=project.id, original_filename="abandoned.mp4",
        storage_key="users/u/retry.mp4", status="pending_upload",
        created_at=now - timedelta(hours=1),
    )
    db.add(asset); db.commit()
    storage = FailOnceStorage()

    first = run_retention_sweep(db, storage, now=now)
    db.refresh(asset)
    assert first["failed"] == 1
    assert asset.status == "pending_upload" and asset.storage_key is not None

    second = run_retention_sweep(db, storage, now=now)
    db.refresh(asset)
    assert second["pending_uploads_deleted"] == 1
    assert asset.status == "expired" and asset.storage_key is None
    db.close()
