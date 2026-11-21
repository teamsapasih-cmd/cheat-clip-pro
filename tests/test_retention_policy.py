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
